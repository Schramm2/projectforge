"""Executes the AI CLI subprocess with the assembled prompt."""

import io
import os
import platform
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from rich.live import Live
from rich.text import Text

from projectforge.conventions import FORGE_DIR
from projectforge.execution_policy import build_provider_command
from projectforge.failure_taxonomy import classify_provider_failure
from projectforge.subprocess_utils import (
    PHASE_TIMEOUT,
    format_activity,
    progress_summary_for_line,
    sanitize_progress_line,
    spinner_frame,
    spinner_style,
    summarize_output_line,
)
from projectforge.ui import (
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


class ProviderExit(int):
    """Integer-compatible provider exit code carrying a privacy-safe category."""

    failure_category: str | None

    def __new__(cls, code: int, failure_category: str | None = None):
        value = int.__new__(cls, code)
        value.failure_category = failure_category
        return value


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


def _build_cmd(
    backend: str,
    prompt: str,
    model: str | None = None,
    *,
    approval_mode: str = "safe",
    allow_unsafe: bool = False,
) -> list[str]:
    """Build the subprocess command for the given backend."""
    return build_provider_command(
        backend,
        prompt,
        model,
        approval_mode=approval_mode,
        allow_unsafe=allow_unsafe,
    )


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


class _ProviderOutput:
    """Sanitized provider output shared by the reader thread and live display."""

    def __init__(self, display_label: str, backend: str) -> None:
        self.tracker = ActivityTracker()
        self.tracker.update(_initial_phase_summary(display_label, backend))
        self.tail: list[str] = []
        self.lock = threading.Lock()

    def stream(self, pipe: io.BufferedReader, live: Live, *, verbose: bool) -> None:
        try:
            for raw_line in iter(pipe.readline, b""):
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                if not line:
                    continue
                clean = sanitize_progress_line(line)
                if not clean:
                    continue
                with self.lock:
                    self.tail.append(clean)
                    if len(self.tail) > 50:
                        del self.tail[0]
                    new_summary = summarize_output_line(clean)
                    if new_summary and new_summary != self.tracker.current:
                        self.tracker.update(new_summary)
                if verbose and new_summary:
                    live.console.print(new_summary)
        except ValueError:
            return

    def display_state(self) -> tuple[str, list[dict]]:
        with self.lock:
            return self.tracker.current, self.tracker.visible_steps()

    @property
    def failure_input(self) -> str:
        return "\n".join(self.tail)


def _render_provider_command(command: list[str], prompt: str, project_dir: Path) -> None:
    display_command = [part if part != prompt else "<prompt>" for part in command]
    console.print(
        make_panel(
            grouped_lines(
                [
                    subtle(f"Command: {' '.join(display_command)}"),
                    subtle(f"Working directory: {project_dir}"),
                ]
            ),
            title="Execution",
            accent="violet",
        )
    )


def _render_provider_timeout() -> ProviderExit:
    failure = classify_provider_failure("", returncode=None, timed_out=True)
    console.print(
        make_panel(
            grouped_lines(
                [
                    Text.assemble(
                        badge("timeout", "warning"),
                        Text("  "),
                        subtle("Project generation took longer than the allowed time."),
                    ),
                    muted(failure.summary),
                    muted(failure.remediation),
                ]
            ),
            title="Execution",
            accent="amber",
        )
    )
    return ProviderExit(124, failure.category)


def _monitor_provider(
    process: subprocess.Popen,
    output: _ProviderOutput,
    *,
    display_label: str,
    accent: str,
    phase_context: list[dict] | None,
    started_at: float,
    verbose: bool,
) -> ProviderExit | None:
    with Live(console=console, refresh_per_second=12) as live:
        reader = threading.Thread(
            target=output.stream,
            args=(process.stdout, live),
            kwargs={"verbose": verbose},
            daemon=True,
        )
        reader.start()

        while process.poll() is None:
            elapsed = time.monotonic() - started_at
            if elapsed > PHASE_TIMEOUT:
                process.kill()
                process.wait()
                reader.join(timeout=5)
                return _render_provider_timeout()
            summary, activities = output.display_state()
            loader = make_loader_panel(
                display_label,
                summary,
                elapsed=elapsed,
                spinner_frame=spinner_frame(elapsed),
                spinner_style=spinner_style(accent, elapsed),
                accent=accent,
                detail=None,
                activities=activities,
            )
            if phase_context:
                from rich.console import Group as RichGroup

                live.update(RichGroup(make_phase_timeline(phase_context), Text(), loader))
            else:
                live.update(loader)
            time.sleep(0.2)

        reader.join(timeout=5)
    return None


def _render_provider_completion(
    *,
    display_label: str,
    elapsed: float,
    returncode: int,
    accent: str,
    verbose: bool,
    failure_input: str,
) -> ProviderExit:
    failure = (
        classify_provider_failure(failure_input, returncode=returncode) if returncode != 0 else None
    )
    if failure is not None and not verbose:
        console.print(
            make_panel(
                grouped_lines(
                    [
                        Text.assemble(
                            badge("failed", "error"),
                            Text("  "),
                            subtle("Project generation stopped before this step finished."),
                        ),
                        muted(failure.summary),
                        muted(failure.remediation),
                    ]
                ),
                title="Execution",
                accent="plum",
            )
        )

    if verbose:
        console.print(
            status_line(f"{display_label} completed in {elapsed:.1f}s (exit {returncode})")
        )
    else:
        console.print(status_line(f"{display_label} finished in {elapsed:.0f}s", accent=accent))
    return ProviderExit(returncode, failure.category if failure is not None else None)


def run_ai(
    backend: str,
    prompt: str,
    project_dir: Path,
    model: str | None = None,
    verbose: bool = False,
    label: str = "",
    phase_context: list[dict] | None = None,
    approval_mode: str = "safe",
    allow_unsafe: bool = False,
) -> int:
    """Execute the AI CLI with the assembled prompt.

    Creates the project directory if it doesn't exist, then runs the chosen
    AI CLI inside it. Output streams to the terminal in real-time.

    Args:
        backend: Which CLI to use (claude, antigravity, codex).
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

    cmd = _build_cmd(
        backend,
        prompt,
        model,
        approval_mode=approval_mode,
        allow_unsafe=allow_unsafe,
    )
    if not cmd:
        console.print(
            status_line(
                "Forge could not start the selected AI tool. Run `forge doctor`, then choose "
                "a ready tool and retry.",
                accent="amber",
            )
        )
        return 1

    if verbose:
        _render_provider_command(cmd, prompt, project_dir)

    started_at = time.monotonic()
    accent = _phase_accent(backend)
    output = _ProviderOutput(display_label, backend)

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        failure = classify_provider_failure("command not found", returncode=None)
        console.print(status_line(failure.summary, accent="amber"))
        console.print(muted(failure.remediation))
        return ProviderExit(127, failure.category)

    timeout_exit = _monitor_provider(
        proc,
        output,
        display_label=display_label,
        accent=accent,
        phase_context=phase_context,
        started_at=started_at,
        verbose=verbose,
    )
    if timeout_exit is not None:
        return timeout_exit

    assert proc.returncode is not None
    return _render_provider_completion(
        display_label=display_label,
        elapsed=time.monotonic() - started_at,
        returncode=proc.returncode,
        accent=accent,
        verbose=verbose,
        failure_input=output.failure_input,
    )


@dataclass(frozen=True)
class _ParallelPhase:
    """Normalized input for one member of a parallel execution window."""

    label: str
    backend: str
    prompt: str
    model: str | None
    approval_mode: str
    allow_unsafe: bool

    @classmethod
    def from_mapping(cls, phase: dict) -> "_ParallelPhase":
        return cls(
            label=phase["label"],
            backend=phase["backend"],
            prompt=phase["prompt"],
            model=phase.get("model"),
            approval_mode=phase.get("approval_mode", "safe"),
            allow_unsafe=phase.get("allow_unsafe", False),
        )


@dataclass
class _PhaseProgress:
    """Live and terminal display state for one parallel phase."""

    label: str
    backend: str
    summary: str
    start: float = 0.0
    returncode: int | None = None
    lines: list[str] = field(default_factory=list)
    last_line: str = ""
    failure_category: str | None = None


class _ParallelExecution:
    """Own concurrent provider processes and their shared Rich display."""

    def __init__(self, phases: list[dict], project_dir: Path, *, verbose: bool) -> None:
        self.phases = [_ParallelPhase.from_mapping(phase) for phase in phases]
        self.project_dir = project_dir
        self.verbose = verbose
        self.lock = threading.Lock()
        self.trackers = {
            phase.label: _PhaseProgress(
                label=phase.label,
                backend=phase.backend,
                summary=_initial_phase_summary(phase.label, phase.backend),
            )
            for phase in self.phases
        }

    def execute(self) -> list[tuple[str, int]]:
        with ThreadPoolExecutor(max_workers=len(self.phases)) as pool:
            futures = [pool.submit(self._run_phase, phase) for phase in self.phases]
            with Live(self._status_table(), console=console, refresh_per_second=4) as live:
                while not all(future.done() for future in futures):
                    live.update(self._status_table())
                    time.sleep(0.25)
                live.update(self._status_table())
            results = [future.result() for future in futures]

        if self.verbose:
            self._render_verbose_output()
        return results

    def _status_table(self):
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
        for tracker in self.trackers.values():
            elapsed = time.monotonic() - tracker.start if tracker.start else 0
            if tracker.returncode == 0:
                icon = badge("done", "success")
                status = f"finished in {elapsed:.0f}s"
            elif tracker.returncode is not None:
                icon = badge("failed", "error")
                status = tracker.failure_category or f"exit {tracker.returncode}"
            else:
                icon = badge("live", "info")
                status = f"working... {elapsed:.0f}s"
            table.add_row(
                icon,
                tracker.label,
                tracker.backend,
                subtle(format_activity(tracker.summary)),
                subtle(status),
            )
        return table

    def _read_output(self, label: str, pipe: io.BufferedReader) -> None:
        try:
            for raw_line in iter(pipe.readline, b""):
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                if not line:
                    continue
                clean = sanitize_progress_line(line)
                if not clean:
                    continue
                with self.lock:
                    tracker = self.trackers[label]
                    tracker.last_line = clean
                    safe_summary = progress_summary_for_line(clean, tracker.summary)
                    if safe_summary != tracker.summary:
                        tracker.summary = safe_summary
                        tracker.lines.append(safe_summary)
                        if len(tracker.lines) > 200:
                            del tracker.lines[0]
        except ValueError:
            return

    def _run_phase(self, phase: _ParallelPhase) -> tuple[str, int]:
        command = _build_cmd(
            phase.backend,
            phase.prompt,
            phase.model,
            approval_mode=phase.approval_mode,
            allow_unsafe=phase.allow_unsafe,
        )
        if not command:
            with self.lock:
                self.trackers[phase.label].returncode = 1
            return phase.label, ProviderExit(1, "unknown")

        started_at = time.monotonic()
        with self.lock:
            self.trackers[phase.label].start = started_at
        try:
            process = subprocess.Popen(
                command,
                cwd=self.project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except FileNotFoundError:
            with self.lock:
                tracker = self.trackers[phase.label]
                tracker.returncode = 1
                tracker.summary = (
                    "The selected AI tool could not start. Run `forge doctor`, then retry."
                )
            return phase.label, ProviderExit(127, "missing_binary")

        reader = threading.Thread(
            target=self._read_output,
            args=(phase.label, process.stdout),
            daemon=True,
        )
        reader.start()
        while process.poll() is None:
            if time.monotonic() - started_at > PHASE_TIMEOUT:
                process.kill()
                process.wait()
                reader.join(timeout=5)
                with self.lock:
                    tracker = self.trackers[phase.label]
                    tracker.returncode = 1
                    tracker.failure_category = "timeout"
                return phase.label, ProviderExit(124, "timeout")
            time.sleep(0.5)

        reader.join(timeout=5)
        assert process.returncode is not None
        with self.lock:
            tracker = self.trackers[phase.label]
            tracker.returncode = process.returncode
            if process.returncode != 0:
                tracker.failure_category = classify_provider_failure(
                    tracker.last_line,
                    returncode=process.returncode,
                ).category
            failure_category = tracker.failure_category
        return phase.label, ProviderExit(process.returncode, failure_category)

    def _render_verbose_output(self) -> None:
        for phase in self.phases:
            tracker = self.trackers[phase.label]
            if not tracker.lines:
                continue
            console.print()
            console.print(
                make_panel(
                    Text(phase.label, style="bold #F7F9FF"),
                    title="Phase Output",
                    accent="plum",
                )
            )
            for line in tracker.lines:
                console.print(line)


def run_ai_parallel(
    phases: list[dict],
    project_dir: Path,
    verbose: bool = False,
) -> list[tuple[str, int]]:
    """Run provider phases concurrently with one shared status display."""
    project_dir.mkdir(parents=True, exist_ok=True)
    return _ParallelExecution(phases, project_dir, verbose=verbose).execute()


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
            status_line(
                "Git is not installed, so Forge could not create the first commit. Install "
                "Git, then initialize and commit the project manually.",
                accent="amber",
            )
        )
        return False

    if git_check.returncode != 0:
        console.print(
            status_line(
                "Forge could not use Git in the project folder. Run `git status` there, fix "
                "the reported issue, then create the first commit manually.",
                accent="amber",
            )
        )
        return False

    if not git_dir.exists():
        console.print(status_line("Git not initialized by AI — setting up...", accent="violet"))
        result = subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(
                status_line(
                    "Forge could not start version control. Run `git init` in the project "
                    "folder, then create the first commit manually.",
                    accent="amber",
                )
            )
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
        console.print(
            status_line(
                "Forge could not stage the generated files. Review the project, then run "
                "`git add -A` and commit manually.",
                accent="amber",
            )
        )
        return False

    result = subprocess.run(
        ["git", "commit", "-m", "Initial commit (via ProjectForge)"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(
            status_line(
                "Forge could not create the first commit. Check your Git identity, then commit "
                "the generated files manually.",
                accent="amber",
            )
        )
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

    console.print(
        status_line(
            "Forge could not open an editor. Open the project manually, or rerun "
            "`forge --setup` to choose an available editor.",
            accent="amber",
        )
    )


HOOKS_DIR = FORGE_DIR / "hooks"
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
        console.print(
            status_line(
                "The post-scaffold hook took too long and was stopped. Review it locally, then "
                "run it again from the project folder.",
                accent="amber",
            )
        )
        return False

    if result.returncode != 0:
        console.print(
            status_line(
                "The post-scaffold hook did not finish successfully. Review the hook locally, "
                "fix it, and run it again from the project folder.",
                accent="amber",
            )
        )
        return False

    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            console.print(f"  {line}")

    console.print(status_line("Post-scaffold hook completed.", accent="aqua"))
    return True
