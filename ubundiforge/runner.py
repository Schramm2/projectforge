"""Executes the AI CLI subprocess with the assembled prompt."""

import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console

console = Console()


def _build_cmd(backend: str, prompt: str, model: str | None = None) -> list[str]:
    """Build the subprocess command for the given backend."""
    if backend == "claude":
        cmd = ["claude", "-p", "--dangerously-skip-permissions"]
        if model:
            cmd.extend(["--model", model])
        cmd.append(prompt)
    elif backend == "gemini":
        cmd = ["gemini", "-p", prompt, "-y"]
        if model:
            cmd.extend(["--model", model])
    elif backend == "codex":
        cmd = ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox"]
        if model:
            cmd.extend(["--model", model])
        cmd.append(prompt)
    else:
        return []

    return cmd


def run_ai(
    backend: str,
    prompt: str,
    project_dir: Path,
    model: str | None = None,
    verbose: bool = False,
) -> int:
    """Execute the AI CLI with the assembled prompt.

    Creates the project directory if it doesn't exist, then runs the chosen
    AI CLI inside it with a progress spinner.

    Args:
        backend: Which CLI to use (claude, gemini, codex).
        prompt: The assembled prompt string.
        project_dir: Path to the project directory to scaffold into.
        model: Optional model to pass to the AI CLI.
        verbose: If True, print the full command and timing info.

    Returns:
        The subprocess return code.
    """
    project_dir.mkdir(parents=True, exist_ok=True)

    cmd = _build_cmd(backend, prompt, model)
    if not cmd:
        print(f"Unknown backend: {backend}", file=sys.stderr)
        return 1

    if verbose:
        display_cmd = [c if c != prompt else "<prompt>" for c in cmd]
        console.print(f"[dim]Command: {' '.join(display_cmd)}[/dim]")
        console.print(f"[dim]Working directory: {project_dir}[/dim]")

    start = time.monotonic()

    with console.status(
        f"[cyan]{backend} is scaffolding your project...[/cyan]",
        spinner="dots",
    ):
        result = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)

    elapsed = time.monotonic() - start

    if result.stdout:
        console.print(result.stdout)
    if result.stderr:
        console.print(result.stderr, style="dim")

    if verbose:
        console.print(f"[dim]Completed in {elapsed:.1f}s (exit code {result.returncode})[/dim]")

    return result.returncode


def reset_project_dir(project_dir: Path) -> None:
    """Remove an existing scaffold target so generation starts from a clean slate."""
    if project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)


def ensure_git_init(project_dir: Path) -> bool:
    """Verify git was initialized with at least one commit; if not, init and commit.

    Returns:
        True if the project has a git repo with at least one commit, False otherwise.
    """
    git_dir = project_dir / ".git"

    if not git_dir.exists():
        console.print("[dim]Git not initialized by AI — setting up...[/dim]")
        result = subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[yellow]git init failed: {result.stderr.strip()}[/yellow]")
            return False

    # Check whether there is at least one commit
    has_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_dir,
        capture_output=True,
    )
    if has_commit.returncode == 0:
        return True

    console.print("[dim]No commits found — creating initial commit...[/dim]")
    result = subprocess.run(["git", "add", "-A"], cwd=project_dir, capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[yellow]git add failed: {result.stderr.strip()}[/yellow]")
        return False

    result = subprocess.run(
        ["git", "commit", "-m", "Initial commit (via UbundiForge)"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[yellow]git commit failed: {result.stderr.strip()}[/yellow]")
        return False

    console.print("[dim]Git initialized with initial commit[/dim]")
    return True


# Maps CLI command to macOS .app bundle name for fallback via `open -a`
_EDITOR_APP_BUNDLES = {
    "cursor": "Cursor",
    "code": "Visual Studio Code",
    "antigravity": "Antigravity",
    "windsurf": "Windsurf",
    "zed": "Zed",
}


def _try_open_via_app(editor: str, project_dir: Path) -> bool:
    """Try opening a project using macOS `open -a` with the .app bundle."""
    if platform.system() != "Darwin":
        return False
    app_name = _EDITOR_APP_BUNDLES.get(editor)
    if not app_name:
        return False
    app_path = Path(f"/Applications/{app_name}.app")
    if not app_path.exists():
        return False
    subprocess.Popen(["open", "-a", app_name, str(project_dir)])
    return True


def open_in_editor(project_dir: Path, preferred_editor: str = "") -> None:
    """Open the project directory in the user's editor.

    Tries the CLI command first, then falls back to macOS `open -a`.

    Args:
        project_dir: Path to the project directory.
        preferred_editor: Editor command from config. Tried first before fallbacks.
    """
    candidates = ["cursor", "antigravity", "code"]
    if preferred_editor:
        candidates = [preferred_editor] + [c for c in candidates if c != preferred_editor]

    for editor in candidates:
        if shutil.which(editor):
            subprocess.Popen([editor, str(project_dir)])
            console.print(f"[dim]Opened {project_dir} in {editor}[/dim]")
            return
        if _try_open_via_app(editor, project_dir):
            console.print(f"[dim]Opened {project_dir} in {editor}[/dim]")
            return

    console.print("[yellow]No editor found. Open the project manually.[/yellow]")
