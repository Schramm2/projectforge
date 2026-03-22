"""Executes the AI CLI subprocess with the assembled prompt."""

import io
import os
import platform
import re
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from rich.live import Live
from rich.text import Text

from ubundiforge.ui import (
    BACKEND_ACCENTS,
    badge,
    create_console,
    grouped_lines,
    make_loader_panel,
    make_panel,
    make_phase_timeline,
    make_table,
    muted,
    status_line,
    subtle,
)

console = create_console()

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
_PULSE_STYLES = {
    "aqua": ("#4D6A84", "#75DCE6", "#C6CEE6", "#75DCE6"),
    "amber": ("#77603A", "#F3BB58", "#F7D99C", "#F3BB58"),
    "violet": ("#5F4A87", "#A16EFA", "#D3BCFF", "#A16EFA"),
    "plum": ("#7B4A79", "#D768D2", "#F0B6ED", "#D768D2"),
}


class ActivityTracker:
    """Accumulates scaffold activity summaries for the activity feed."""

    def __init__(self, max_visible: int = 6):
        self.steps: list[dict] = []
        self.current: str = ""
        self._max_visible = max_visible

    def update(self, summary: str) -> None:
        """Record a new activity summary. Deduplicates consecutive identical summaries."""
        if self.current == summary:
            return
        # Mark previous step as completed
        if self.steps:
            self.steps[-1]["completed"] = True
        self.steps.append(
            {
                "summary": summary,
                "completed": False,
                "timestamp": time.monotonic(),
            }
        )
        self.current = summary

    def visible_steps(self) -> list[dict]:
        """Return the most recent steps up to max_visible."""
        return self.steps[-self._max_visible :]


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


def _phase_accent(backend: str) -> str:
    """Return the accent color that best matches a backend."""
    return BACKEND_ACCENTS.get(backend, "violet")


def _initial_phase_summary(label: str, backend: str) -> str:
    """Return the first human-friendly summary shown before output arrives."""
    lowered = label.lower()
    if "architecture" in lowered:
        return "Designing the project foundation"
    if "frontend" in lowered:
        return "Shaping the interface and app structure"
    if "tests" in lowered:
        return "Setting up tests and developer workflows"
    if "verify" in lowered:
        return "Checking the scaffold and smoothing rough edges"
    return f"Working through the scaffold with {backend}"


def _sanitize_progress_line(line: str) -> str:
    """Normalize backend output into compact text suitable for a loader."""
    clean = _ANSI_RE.sub("", line).strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean[:120]


def _is_noisy_progress_line(line: str) -> bool:
    """Filter out raw lines that are too noisy to show directly in the loader."""
    if not line:
        return True
    noisy_prefixes = (
        "$",
        ">",
        "```",
        "diff --git",
        "@@",
        "+++",
        "---",
        "{",
        "[{",
    )
    if line.startswith(noisy_prefixes):
        return True
    if line.count("/") > 6:
        return True
    return False


def _summarize_output_line(line: str) -> str | None:
    """Translate backend output into a clean user-facing progress summary."""
    lowered = line.lower()

    keyword_groups = (
        (
            ("inspect", "review", "analy", "read ", "scan", "explor", "understand"),
            "Reviewing the scaffold brief",
        ),
        (("plan", "approach", "strategy", "outline"), "Planning the next set of changes"),
        (("lint", "eslint", "ruff", "prettier"), "Running lint checks"),
        (("typecheck", "tsc", "mypy", "pyright"), "Running type checks"),
        (("test", "pytest", "vitest", "jest", "playwright", "cypress"), "Running tests and checks"),
        (
            (
                "install",
                "dependencies",
                "dependency",
                "npm ",
                "pnpm ",
                "bun ",
                "pip ",
                "uv sync",
                "poetry ",
            ),
            "Installing project dependencies",
        ),
        (
            (
                "create",
                "created",
                "patch",
                "write",
                "writing",
                "update",
                "updating",
                "edited",
                "edit ",
                "apply_patch",
                "scaffold",
            ),
            "Writing and refining project files",
        ),
        (("schema", "migration", "database", "sql"), "Preparing the data layer"),
        (("build", "compile", "bundle", "transpil"), "Building the project"),
        (
            (
                "localhost",
                "listening",
                "dev server",
                "starting server",
                "ready on",
                "running dev",
                "vite",
            ),
            "Starting the app locally",
        ),
        (("git init", "git add", "git commit", ".git"), "Finalizing the repository"),
        (
            ("error", "failed", "traceback", "exception", "cannot", "unable to", "fixing"),
            "Working through an issue in the scaffold",
        ),
        (("done", "complete", "completed", "finished", "success"), "Wrapping up this phase"),
    )

    for tokens, summary in keyword_groups:
        if any(token in lowered for token in tokens):
            return summary
    return None


def _progress_summary_for_line(line: str, current: str) -> str:
    """Pick the best loader summary for a new backend output line."""
    summary = _summarize_output_line(line)
    if summary:
        return summary
    if not _is_noisy_progress_line(line):
        return line
    return current


def _spinner_frame(elapsed: float) -> str:
    """Return the current spinner frame."""
    return _SPINNER_FRAMES[int(elapsed * 10) % len(_SPINNER_FRAMES)]


def _spinner_style(accent: str, elapsed: float) -> str:
    """Return a pulsing spinner color to mimic a subtle fade animation."""
    palette = _PULSE_STYLES.get(accent, _PULSE_STYLES["violet"])
    return palette[int(elapsed * 6) % len(palette)]


def _format_activity(text: str, limit: int = 54) -> str:
    """Clamp activity text so loader surfaces stay compact."""
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def run_ai(
    backend: str,
    prompt: str,
    project_dir: Path,
    model: str | None = None,
    verbose: bool = False,
    label: str = "",
    phase_context: list[dict] | None = None,
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
        console.print(status_line(f"Unknown backend: {backend}", accent="amber"))
        return 1

    if verbose:
        display_cmd = [c if c != prompt else "<prompt>" for c in cmd]
        console.print(
            make_panel(
                grouped_lines(
                    [
                        subtle(f"Command: {' '.join(display_cmd)}"),
                        subtle(f"Working directory: {project_dir}"),
                    ]
                ),
                title="Execution",
                accent="violet",
            )
        )

    start = time.monotonic()
    accent = _phase_accent(backend)
    tracker = ActivityTracker()
    tracker.update(_initial_phase_summary(display_label, backend))
    last_line = ""
    lock = threading.Lock()

    def _stream_stdout(pipe: io.BufferedReader, live: Live) -> None:
        """Read stdout line-by-line and update the polished loader state."""
        nonlocal last_line
        try:
            for raw_line in iter(pipe.readline, b""):
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                if line:
                    clean = _sanitize_progress_line(line)
                    if not clean:
                        continue
                    with lock:
                        last_line = clean
                        new_summary = _summarize_output_line(clean)
                        if new_summary and new_summary != tracker.current:
                            tracker.update(new_summary)
                    if verbose:
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

        with Live(console=console, refresh_per_second=12) as live:
            reader = threading.Thread(target=_stream_stdout, args=(proc.stdout, live), daemon=True)
            reader.start()

            while proc.poll() is None:
                elapsed = time.monotonic() - start
                if elapsed > _PHASE_TIMEOUT:
                    proc.kill()
                    proc.wait()
                    reader.join(timeout=5)
                    console.print(
                        make_panel(
                            grouped_lines(
                                [
                                    Text.assemble(
                                        badge("timeout", "warning"),
                                        Text("  "),
                                        subtle(f"{display_label} timed out after {elapsed:.0f}s."),
                                    ),
                                    muted("The phase may have stalled."),
                                ]
                            ),
                            title="Execution",
                            accent="amber",
                        )
                    )
                    return 1
                with lock:
                    current_activities = tracker.visible_steps()
                    current_detail = last_line if last_line != tracker.current else None
                loader = make_loader_panel(
                    display_label,
                    tracker.current,
                    elapsed=elapsed,
                    spinner_frame=_spinner_frame(elapsed),
                    spinner_style=_spinner_style(accent, elapsed),
                    accent=accent,
                    detail=current_detail,
                    activities=current_activities,
                )
                if phase_context:
                    from rich.console import Group as RichGroup

                    live.update(RichGroup(make_phase_timeline(phase_context), Text(), loader))
                else:
                    live.update(loader)
                time.sleep(0.2)

            reader.join(timeout=5)

    except FileNotFoundError:
        console.print(status_line(f"{backend} command not found.", accent="amber"))
        return 1

    elapsed = time.monotonic() - start

    if proc.returncode != 0 and not verbose:
        failure_lines: list[Text] = [
            Text.assemble(
                badge("failed", "error"),
                Text("  "),
                subtle(f"{display_label} exited with code {proc.returncode}."),
            )
        ]
        if last_line:
            failure_lines.append(muted(_format_activity(last_line, limit=110)))
        console.print(make_panel(grouped_lines(failure_lines), title="Execution", accent="plum"))

    if verbose:
        console.print(
            status_line(f"{display_label} completed in {elapsed:.1f}s (exit {proc.returncode})")
        )
    else:
        console.print(status_line(f"{display_label} finished in {elapsed:.0f}s", accent=accent))

    return proc.returncode


@dataclass
class _PhaseProgress:
    """Tracks live progress and final state for a running phase."""

    label: str
    backend: str
    summary: str
    start: float = 0.0
    returncode: int | None = None
    lines: list[str] = field(default_factory=list)
    last_line: str = ""


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

    trackers: dict[str, _PhaseProgress] = {}
    procs: dict[str, subprocess.Popen] = {}
    readers: dict[str, threading.Thread] = {}
    lock = threading.Lock()

    def _build_status_table():
        """Build a Rich table showing all parallel phase statuses."""
        table = make_table(
            title="Parallel Phases",
            accent="amber",
            show_edge=False,
            pad_edge=False,
            box_style=None,
        )
        table.add_column("Status", width=10)
        table.add_column("Phase")
        table.add_column("Backend")
        table.add_column("Activity")
        table.add_column("State")
        for t in trackers.values():
            elapsed = time.monotonic() - t.start if t.start else 0
            if t.returncode is not None:
                if t.returncode == 0:
                    icon = badge("done", "success")
                    status = f"finished in {elapsed:.0f}s"
                else:
                    icon = badge("failed", "error")
                    status = f"exit {t.returncode}"
            else:
                icon = badge("live", "info")
                status = f"working... {elapsed:.0f}s"
            table.add_row(
                icon,
                t.label,
                t.backend,
                subtle(_format_activity(t.summary)),
                subtle(status),
            )
        return table

    def _reader_fn(label: str, pipe: io.BufferedReader) -> None:
        try:
            for raw_line in iter(pipe.readline, b""):
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                if line:
                    clean = _sanitize_progress_line(line)
                    if not clean:
                        continue
                    with lock:
                        trackers[label].lines.append(clean)
                        trackers[label].last_line = clean
                        trackers[label].summary = _progress_summary_for_line(
                            clean, trackers[label].summary
                        )
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
                trackers[label].summary = f"{backend} command not found"
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
        trackers[phase["label"]] = _PhaseProgress(
            label=phase["label"],
            backend=phase["backend"],
            summary=_initial_phase_summary(phase["label"], phase["backend"]),
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

    if verbose:
        for phase in phases:
            label = phase["label"]
            t = trackers[label]
            if t.lines:
                console.print()
                console.print(
                    make_panel(
                        Text(label, style="bold #F7F9FF"),
                        title="Phase Output",
                        accent="plum",
                    )
                )
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

    try:
        git_check = subprocess.run(["git", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        console.print(
            status_line("git is not installed. Install git to enable repo setup.", accent="amber")
        )
        return False

    if git_check.returncode != 0:
        console.print(status_line("git is not working correctly.", accent="amber"))
        return False

    if not git_dir.exists():
        console.print(status_line("Git not initialized by AI — setting up...", accent="violet"))
        result = subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(status_line(f"git init failed: {result.stderr.strip()}", accent="amber"))
            return False

    # Check whether there is at least one commit
    has_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_dir,
        capture_output=True,
    )
    if has_commit.returncode == 0:
        return True

    console.print(status_line("No commits found — creating initial commit...", accent="violet"))
    result = subprocess.run(["git", "add", "-A"], cwd=project_dir, capture_output=True, text=True)
    if result.returncode != 0:
        console.print(status_line(f"git add failed: {result.stderr.strip()}", accent="amber"))
        return False

    result = subprocess.run(
        ["git", "commit", "-m", "Initial commit (via UbundiForge)"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(status_line(f"git commit failed: {result.stderr.strip()}", accent="amber"))
        return False

    console.print(status_line("Git initialized with initial commit", accent="aqua"))
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
            console.print(status_line(f"Opened {project_dir} in {editor}"))
            return
        if _try_open_via_app(editor, project_dir):
            console.print(status_line(f"Opened {project_dir} in {editor}"))
            return

    console.print(status_line("No editor found. Open the project manually.", accent="amber"))


HOOKS_DIR = Path.home() / ".forge" / "hooks"
POST_SCAFFOLD_HOOK = HOOKS_DIR / "post-scaffold.sh"


def run_post_scaffold_hook(
    project_dir: Path,
    answers: dict,
) -> bool:
    """Run ~/.forge/hooks/post-scaffold.sh if it exists.

    The hook receives the project directory as cwd and key scaffold
    metadata as environment variables.

    Returns:
        True if the hook ran successfully or no hook exists. False on failure.
    """
    if not POST_SCAFFOLD_HOOK.exists():
        return True

    env = {
        **os.environ,
        "FORGE_PROJECT_DIR": str(project_dir),
        "FORGE_PROJECT_NAME": answers.get("name", ""),
        "FORGE_STACK": answers.get("stack", ""),
        "FORGE_DEMO_MODE": "1" if answers.get("demo_mode") else "0",
    }

    console.print(status_line("Running post-scaffold hook...", accent="violet"))

    try:
        result = subprocess.run(
            ["bash", str(POST_SCAFFOLD_HOOK)],
            cwd=project_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        console.print(status_line("Post-scaffold hook timed out (60s limit).", accent="amber"))
        return False

    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            console.print(f"  {line}")

    if result.returncode != 0:
        console.print(
            status_line(
                f"Post-scaffold hook exited with code {result.returncode}.",
                accent="amber",
            )
        )
        if result.stderr.strip():
            console.print(f"  {result.stderr.strip()}")
        return False

    console.print(status_line("Post-scaffold hook completed.", accent="aqua"))
    return True
