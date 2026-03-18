"""Executes the AI CLI subprocess with the assembled prompt."""

import io
import platform
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

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


_PHASE_TIMEOUT = 1800  # 30 minutes per phase


def run_ai(
    backend: str,
    prompt: str,
    project_dir: Path,
    model: str | None = None,
    verbose: bool = False,
    label: str = "",
) -> int:
    """Execute the AI CLI with the assembled prompt.

    Creates the project directory if it doesn't exist, then runs the chosen
    AI CLI inside it. Output streams to the terminal in real-time.

    Args:
        backend: Which CLI to use (claude, gemini, codex).
        prompt: The assembled prompt string.
        project_dir: Path to the project directory to scaffold into.
        model: Optional model to pass to the AI CLI.
        verbose: If True, print the full command and timing info.
        label: Display label for this phase (used in spinner text).

    Returns:
        The subprocess return code.
    """
    project_dir.mkdir(parents=True, exist_ok=True)
    display_label = label or backend

    cmd = _build_cmd(backend, prompt, model)
    if not cmd:
        print(f"Unknown backend: {backend}", file=sys.stderr)
        return 1

    if verbose:
        display_cmd = [c if c != prompt else "<prompt>" for c in cmd]
        console.print(f"[dim]Command: {' '.join(display_cmd)}[/dim]")
        console.print(f"[dim]Working directory: {project_dir}[/dim]")

    start = time.monotonic()

    spinner = Spinner("dots", text=Text(f"Starting {display_label}...", style="dim"))

    def _stream_stdout(pipe: io.BufferedReader, live: Live) -> None:
        """Read stdout line-by-line, print above the spinner via Rich."""
        try:
            for raw_line in iter(pipe.readline, b""):
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                if line:
                    live.console.print(line)
        except ValueError:
            pass  # pipe closed

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        with Live(spinner, console=console, refresh_per_second=10) as live:
            reader = threading.Thread(
                target=_stream_stdout, args=(proc.stdout, live), daemon=True
            )
            reader.start()

            while proc.poll() is None:
                elapsed = time.monotonic() - start
                if elapsed > _PHASE_TIMEOUT:
                    proc.kill()
                    proc.wait()
                    reader.join(timeout=5)
                    console.print(
                        f"\n[yellow]{display_label} timed out after {elapsed:.0f}s. "
                        f"The phase may have stalled.[/yellow]"
                    )
                    return 1
                spinner.update(text=Text(
                    f"{display_label} working... ({elapsed:.0f}s)", style="dim"
                ))
                time.sleep(0.2)

            reader.join(timeout=5)

    except FileNotFoundError:
        console.print(f"[red]{backend} command not found.[/red]")
        return 1

    elapsed = time.monotonic() - start

    if verbose:
        console.print(
            f"[dim]{display_label} completed in {elapsed:.1f}s"
            f" (exit {proc.returncode})[/dim]"
        )
    else:
        console.print(f"[dim]{display_label} finished in {elapsed:.0f}s[/dim]")

    return proc.returncode


@dataclass
class _ParallelPhase:
    """Tracks a phase running in the background."""
    label: str
    backend: str
    start: float = 0.0
    returncode: int | None = None
    lines: list[str] = field(default_factory=list)


def run_ai_parallel(
    phases: list[dict],
    project_dir: Path,
    verbose: bool = False,
) -> list[tuple[str, int]]:
    """Run multiple AI phases concurrently with a shared status display.

    Args:
        phases: List of dicts with keys: label, backend, prompt, model.
        project_dir: Shared project directory.
        verbose: Show detailed output.

    Returns:
        List of (label, returncode) tuples.
    """
    project_dir.mkdir(parents=True, exist_ok=True)

    trackers: dict[str, _ParallelPhase] = {}
    procs: dict[str, subprocess.Popen] = {}
    readers: dict[str, threading.Thread] = {}
    lock = threading.Lock()

    def _build_status_table() -> Table:
        """Build a Rich table showing all parallel phase statuses."""
        table = Table(show_header=False, show_edge=False, pad_edge=False, box=None)
        table.add_column(width=3)
        table.add_column()
        for t in trackers.values():
            elapsed = time.monotonic() - t.start if t.start else 0
            if t.returncode is not None:
                if t.returncode == 0:
                    icon = "[green]ok[/green]"
                    status = f"{t.label} finished in {elapsed:.0f}s"
                else:
                    icon = "[red]!![/red]"
                    status = f"{t.label} failed (exit {t.returncode})"
            else:
                icon = "[cyan]...[/cyan]"
                status = f"{t.label} ({t.backend}) working... ({elapsed:.0f}s)"
            table.add_row(icon, f"[dim]{status}[/dim]")
        return table

    def _reader_fn(label: str, pipe: io.BufferedReader) -> None:
        try:
            for raw_line in iter(pipe.readline, b""):
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                if line:
                    with lock:
                        trackers[label].lines.append(line)
        except ValueError:
            pass

    def _run_one(phase: dict) -> tuple[str, int]:
        label = phase["label"]
        backend = phase["backend"]
        prompt = phase["prompt"]
        model = phase.get("model")

        cmd = _build_cmd(backend, prompt, model)
        if not cmd:
            with lock:
                trackers[label].returncode = 1
            return label, 1

        start = time.monotonic()
        with lock:
            trackers[label].start = start

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except FileNotFoundError:
            with lock:
                trackers[label].returncode = 1
            return label, 1

        with lock:
            procs[label] = proc

        reader = threading.Thread(target=_reader_fn, args=(label, proc.stdout), daemon=True)
        reader.start()
        with lock:
            readers[label] = reader

        while proc.poll() is None:
            elapsed = time.monotonic() - start
            if elapsed > _PHASE_TIMEOUT:
                proc.kill()
                proc.wait()
                reader.join(timeout=5)
                with lock:
                    trackers[label].returncode = 1
                return label, 1
            time.sleep(0.5)

        reader.join(timeout=5)
        with lock:
            trackers[label].returncode = proc.returncode

        return label, proc.returncode

    # Initialize trackers
    for phase in phases:
        trackers[phase["label"]] = _ParallelPhase(
            label=phase["label"], backend=phase["backend"]
        )

    results: list[tuple[str, int]] = []

    with ThreadPoolExecutor(max_workers=len(phases)) as pool:
        futures = {pool.submit(_run_one, p): p["label"] for p in phases}

        with Live(_build_status_table(), console=console, refresh_per_second=4) as live:
            while not all(f.done() for f in futures):
                live.update(_build_status_table())
                time.sleep(0.25)
            # Final update
            live.update(_build_status_table())

        for future in futures:
            label, rc = future.result()
            results.append((label, rc))

    # Print buffered output from each phase
    for phase in phases:
        label = phase["label"]
        t = trackers[label]
        if t.lines:
            console.print(f"\n[bold]--- {label} output ---[/bold]")
            for line in t.lines:
                console.print(line)

    return results


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
