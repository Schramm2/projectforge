"""Executes the AI CLI subprocess with the assembled prompt."""

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


def ensure_git_init(project_dir: Path) -> None:
    """Verify git was initialized in the project dir; if not, init and commit."""
    git_dir = project_dir / ".git"
    if git_dir.exists():
        return

    console.print("[dim]Git not initialized by AI — setting up...[/dim]")
    subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=project_dir, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit (via UbundiForge)"],
        cwd=project_dir,
        capture_output=True,
    )
    console.print("[dim]Git initialized with initial commit[/dim]")


def open_in_editor(project_dir: Path) -> None:
    """Open the project directory in the user's editor."""
    for editor in ("cursor", "code"):
        if shutil.which(editor):
            subprocess.Popen([editor, str(project_dir)])
            console.print(f"[dim]Opened {project_dir} in {editor}[/dim]")
            return

    console.print("[yellow]No editor found (tried cursor, code). Open manually.[/yellow]")
