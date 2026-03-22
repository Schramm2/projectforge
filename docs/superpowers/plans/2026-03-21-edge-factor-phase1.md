# Edge Factor Phase 1: Visual Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Forge's scaffold experience with a phase timeline, activity feed, file tree visualization, and post-scaffold dashboard — creating immediate wow factor with zero new dependencies.

**Architecture:** All four features build on the existing Rich/UI infrastructure in `ui.py` and integrate into the scaffold execution flow in `runner.py` and `cli.py`. The post-scaffold dashboard replaces the current `_render_completion` + `_render_next_steps` pair. The activity feed and phase timeline upgrade the existing `make_loader_panel` system. The file tree is a standalone renderable shown between phases.

**Tech Stack:** Python 3.12+, Rich (existing), pathlib (existing)

**Spec:** `docs/superpowers/specs/2026-03-21-edge-factor-design.md`

**Dev commands:**
```bash
uv run pytest tests/ -v                    # Run all tests
uv run pytest tests/test_file.py -v        # Run specific test file
uv run ruff check src/ubundiforge tests    # Lint
uv run ruff format src/ubundiforge tests   # Format
```

---

## File Structure

**New files:**
- `src/ubundiforge/dashboard.py` — Post-scaffold dashboard rendering (report card)
- `tests/test_dashboard.py` — Tests for dashboard

**Modified files:**
- `src/ubundiforge/ui.py` — New renderables: `make_phase_timeline`, `make_file_tree`, updated `make_loader_panel`
- `src/ubundiforge/runner.py` — Activity feed tracking, shared Live context support, file tree display
- `src/ubundiforge/cli.py` — Dashboard call replacing `_render_completion` + `_render_next_steps`, pass `VerifyReport` through
- `tests/test_runner.py` — Tests for activity feed and summarizer changes
- `tests/test_cli.py` — Updated tests for dashboard integration

---

## Task 1: Post-Scaffold Dashboard — Data Collection

The dashboard needs file counts, line counts, and dependency counts from the scaffolded project. Build the data layer first.

**Files:**
- Create: `src/ubundiforge/dashboard.py`
- Create: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing tests for project stats collection**

```python
# tests/test_dashboard.py
"""Tests for the post-scaffold dashboard."""

from pathlib import Path

from ubundiforge.dashboard import collect_project_stats


def test_collect_stats_empty_dir(tmp_path: Path):
    stats = collect_project_stats(tmp_path)
    assert stats["file_count"] == 0
    assert stats["line_count"] == 0
    assert stats["dep_count"] == 0


def test_collect_stats_with_files(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\nprint('world')\n")
    (tmp_path / "lib.py").write_text("x = 1\n")
    stats = collect_project_stats(tmp_path)
    assert stats["file_count"] == 2
    assert stats["line_count"] == 3


def test_collect_stats_ignores_hidden_dirs(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("stuff\n")
    (tmp_path / "main.py").write_text("x = 1\n")
    stats = collect_project_stats(tmp_path)
    assert stats["file_count"] == 1


def test_collect_stats_counts_python_deps(tmp_path: Path):
    toml = '[project]\nname = "test"\ndependencies = ["fastapi", "pydantic", "httpx"]\n'
    (tmp_path / "pyproject.toml").write_text(toml)
    stats = collect_project_stats(tmp_path)
    assert stats["dep_count"] == 3


def test_collect_stats_counts_node_deps(tmp_path: Path):
    pkg = '{"dependencies": {"react": "^18", "next": "^14"}, "devDependencies": {"vitest": "^1"}}'
    (tmp_path / "package.json").write_text(pkg)
    stats = collect_project_stats(tmp_path)
    assert stats["dep_count"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ubundiforge.dashboard'`

- [ ] **Step 3: Implement `collect_project_stats`**

```python
# src/ubundiforge/dashboard.py
"""Post-scaffold dashboard — the project report card."""

import json
from pathlib import Path

_HIDDEN_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".forge", ".ruff_cache"}
_BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot"}


def collect_project_stats(project_dir: Path) -> dict:
    """Collect file count, line count, and dependency count from a scaffolded project."""
    file_count = 0
    line_count = 0

    for path in project_dir.rglob("*"):
        if any(part.startswith(".") or part in _HIDDEN_DIRS for part in path.relative_to(project_dir).parts):
            continue
        if path.is_file() and path.suffix not in _BINARY_SUFFIXES:
            file_count += 1
            try:
                line_count += len(path.read_text(errors="replace").splitlines())
            except OSError:
                pass

    dep_count = _count_python_deps(project_dir) + _count_node_deps(project_dir)

    return {
        "file_count": file_count,
        "line_count": line_count,
        "dep_count": dep_count,
    }


def _count_python_deps(project_dir: Path) -> int:
    """Count dependencies from pyproject.toml if present."""
    toml_path = project_dir / "pyproject.toml"
    if not toml_path.exists():
        return 0
    try:
        import tomllib
        data = tomllib.loads(toml_path.read_text())
        return len(data.get("project", {}).get("dependencies", []))
    except Exception:
        return 0


def _count_node_deps(project_dir: Path) -> int:
    """Count dependencies from package.json if present."""
    pkg_path = project_dir / "package.json"
    if not pkg_path.exists():
        return 0
    try:
        data = json.loads(pkg_path.read_text())
        deps = len(data.get("dependencies", {}))
        dev_deps = len(data.get("devDependencies", {}))
        return deps + dev_deps
    except Exception:
        return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Lint and format**

Run: `uv run ruff check src/ubundiforge/dashboard.py tests/test_dashboard.py && uv run ruff format src/ubundiforge/dashboard.py tests/test_dashboard.py`

- [ ] **Step 6: Commit**

```bash
git add src/ubundiforge/dashboard.py tests/test_dashboard.py
git commit -m "feat(dashboard): add project stats collection"
```

---

## Task 2: Post-Scaffold Dashboard — Rendering

Build the Rich-based dashboard renderable that presents the report card.

**Files:**
- Modify: `src/ubundiforge/dashboard.py`
- Modify: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing test for dashboard rendering**

```python
# Append to tests/test_dashboard.py
from io import StringIO
from pathlib import Path

from rich.console import Console

from ubundiforge.dashboard import render_dashboard
from ubundiforge.verify import CheckResult, VerifyReport


def test_render_dashboard_produces_output(tmp_path: Path):
    """Dashboard renders without error and produces output."""
    (tmp_path / "main.py").write_text("x = 1\n")
    answers = {"name": "pulse", "stack": "fastapi", "description": "health API"}
    phase_backends = [("architecture", "claude"), ("tests", "codex"), ("verify", "claude")]
    report = VerifyReport(checks=[
        CheckResult(name="lint", passed=True),
        CheckResult(name="test", passed=True),
    ])
    console = Console(file=StringIO(), width=80)
    # Should not raise
    render_dashboard(
        console=console,
        answers=answers,
        phase_backends=phase_backends,
        project_dir=tmp_path,
        verify_report=report,
        elapsed=158.0,
    )


def test_render_dashboard_without_verify(tmp_path: Path):
    """Dashboard renders when verify was skipped (no report)."""
    answers = {"name": "pulse", "stack": "fastapi", "description": "health API"}
    phase_backends = [("architecture", "claude")]
    console = Console(file=StringIO(), width=80)
    render_dashboard(
        console=console,
        answers=answers,
        phase_backends=phase_backends,
        project_dir=tmp_path,
        verify_report=None,
        elapsed=90.0,
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_dashboard.py::test_render_dashboard_produces_output -v`
Expected: FAIL with `ImportError: cannot import name 'render_dashboard'`

- [ ] **Step 3: Implement `render_dashboard`**

```python
# Append to src/ubundiforge/dashboard.py

from rich.console import Console
from rich.text import Text

from ubundiforge.ui import (
    ACCENTS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    badge,
    command_text,
    grouped_lines,
    make_panel,
    muted,
    subtle,
)
from ubundiforge.verify import VerifyReport


def render_dashboard(
    *,
    console: Console,
    answers: dict,
    phase_backends: list[tuple[str, str]],
    project_dir: Path,
    verify_report: VerifyReport | None,
    elapsed: float,
) -> None:
    """Render the post-scaffold project report card."""
    name = answers.get("name", "project")
    stack = answers.get("stack", "unknown")
    backends_used = sorted({b for _, b in phase_backends})

    stats = collect_project_stats(project_dir)

    # --- Header row ---
    header = Text()
    header.append("Project Ready", style=f"bold {ACCENTS['violet']}")
    console.print()
    console.print(header)
    console.print()

    # --- Metadata ---
    meta_lines: list[Text] = []
    meta_parts = [
        ("Project", name),
        ("Stack", stack),
        ("Backend", " + ".join(backends_used)),
        ("Time", f"{elapsed:.0f}s"),
    ]
    for label, value in meta_parts:
        line = Text()
        line.append(f"  {label:<10}", style=TEXT_MUTED)
        line.append(value, style=f"bold {TEXT_PRIMARY}")
        meta_lines.append(line)
    console.print(grouped_lines(meta_lines))
    console.print()

    # --- Health checks ---
    if verify_report is not None:
        check_line = Text("  ")
        for check in verify_report.checks:
            if check.skipped:
                check_line.append(f"- {check.name}  ", style=TEXT_MUTED)
            elif check.passed:
                check_line.append("✓ ", style=ACCENTS["aqua"])
                detail = check.detail or check.name
                check_line.append(f"{detail}  ", style=TEXT_SECONDARY)
            else:
                check_line.append("✗ ", style=ACCENTS["plum"])
                check_line.append(f"{check.name}  ", style=TEXT_SECONDARY)
        console.print(muted("  HEALTH CHECKS"))
        console.print(check_line)
    else:
        console.print(muted("  HEALTH CHECKS"))
        console.print(subtle("  skipped (use --verify to enable)"))
    console.print()

    # --- Scaffold summary ---
    console.print(muted("  SCAFFOLD SUMMARY"))
    summary = Text("  ")
    summary.append(str(stats["file_count"]), style=f"bold {ACCENTS['amber']}")
    summary.append(" files  ", style=TEXT_MUTED)
    summary.append(f"{stats['line_count']:,}", style=f"bold {ACCENTS['amber']}")
    summary.append(" lines  ", style=TEXT_MUTED)
    summary.append(str(len(phase_backends)), style=f"bold {ACCENTS['amber']}")
    summary.append(" phases  ", style=TEXT_MUTED)
    if stats["dep_count"]:
        summary.append(str(stats["dep_count"]), style=f"bold {ACCENTS['amber']}")
        summary.append(" deps", style=TEXT_MUTED)
    console.print(summary)
    console.print()

    # --- Next steps ---
    from ubundiforge.stacks import STACK_META

    console.print(muted("  NEXT STEPS"))
    console.print(command_text(f"  cd {project_dir.name}"))
    meta = STACK_META.get(stack)
    if meta and meta.env_hints:
        console.print(subtle("  cp .env.example .env"))
    if meta and meta.dev_commands:
        run_cmd = meta.dev_commands.get("run") or meta.dev_commands.get("dev")
        if run_cmd:
            console.print(command_text(f"  {run_cmd}"))
    console.print()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Lint and format**

Run: `uv run ruff check src/ubundiforge/dashboard.py tests/test_dashboard.py && uv run ruff format src/ubundiforge/dashboard.py tests/test_dashboard.py`

- [ ] **Step 6: Commit**

```bash
git add src/ubundiforge/dashboard.py tests/test_dashboard.py
git commit -m "feat(dashboard): add post-scaffold report card rendering"
```

---

## Task 3: Post-Scaffold Dashboard — CLI Integration

Replace the current `_render_completion` + `_render_next_steps` with the dashboard. Pass `VerifyReport` and elapsed time through.

**Files:**
- Modify: `src/ubundiforge/cli.py:1076-1104`

- [ ] **Step 1: Write failing test for dashboard integration**

```python
# Append to tests/test_cli.py (or add a focused integration test)
# This test verifies the dashboard import is available and the function signature matches
from ubundiforge.dashboard import render_dashboard
from ubundiforge.verify import VerifyReport


def test_dashboard_import_and_signature():
    """Verify render_dashboard has the expected parameters."""
    import inspect
    sig = inspect.signature(render_dashboard)
    params = set(sig.parameters.keys())
    assert "console" in params
    assert "answers" in params
    assert "phase_backends" in params
    assert "project_dir" in params
    assert "verify_report" in params
    assert "elapsed" in params
```

- [ ] **Step 2: Run test to verify it passes** (this is a smoke test that the module exists)

Run: `uv run pytest tests/test_cli.py::test_dashboard_import_and_signature -v`
Expected: PASS (since Task 2 created the function)

- [ ] **Step 3: Integrate dashboard into cli.py**

In `src/ubundiforge/cli.py`, make these changes:

**Add import** (near the other imports at the top):
```python
from ubundiforge.dashboard import render_dashboard
```

**Add timing** — capture `start_time` immediately before the phase execution loop begins (around line 970, the `# --- Execute phases ---` comment). Use `time` from stdlib:
```python
import time
scaffold_start = time.monotonic()
```

**Replace the post-scaffold rendering block** (lines ~1076-1104). Replace:
```python
    write_scaffold_manifest(...)
    git_ok = ensure_git_init(project_dir)

    if verify:
        report = verify_scaffold(answers["stack"], project_dir, verbose=verbose)
        print_report(report, console)
        if not report.all_passed:
            _render_verification_guidance(project_dir)

    run_post_scaffold_hook(project_dir, answers)
    append_scaffold_log(answers, phase_backends, project_dir)

    console.print()
    _render_completion(project_dir, git_ok=git_ok)
    console.print()
    _render_next_steps(answers, project_dir, open_editor=open_editor)
```

With:
```python
    write_scaffold_manifest(...)
    git_ok = ensure_git_init(project_dir)

    verify_report = None
    if verify:
        verify_report = verify_scaffold(answers["stack"], project_dir, verbose=verbose)

    run_post_scaffold_hook(project_dir, answers)
    append_scaffold_log(answers, phase_backends, project_dir)

    elapsed = time.monotonic() - scaffold_start
    render_dashboard(
        console=console,
        answers=answers,
        phase_backends=phase_backends,
        project_dir=project_dir,
        verify_report=verify_report,
        elapsed=elapsed,
    )

    if not git_ok:
        console.print(muted('  Run git init && git add -A && git commit -m "Initial commit" manually.'))

    # Preserve existing open_editor logic — this block is UNCHANGED from before
    if open_editor:
        _open_editor(project_dir, answers)
```

**Important:** The `open_editor` block (lines ~1102-1104 in the original) must be preserved after the dashboard call. Do not remove it. The replacement only covers the `_render_completion` + `_render_next_steps` calls.

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS. Some existing tests may reference `_render_completion` or `_render_next_steps` — update any that break.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/ubundiforge/cli.py`

- [ ] **Step 6: Smoke test**

Run: `./forge --dry-run --name smoke --stack fastapi --description "test" --no-docker`
Expected: Forge runs through the prompt assembly (dry-run exits before execution, so no dashboard shown, but no import errors)

- [ ] **Step 7: Commit**

```bash
git add src/ubundiforge/cli.py
git commit -m "feat(dashboard): integrate post-scaffold report card into CLI"
```

---

## Task 4: Activity Feed — Tracking Layer

Upgrade the runner's single-summary model to accumulate completed activity steps.

**Files:**
- Modify: `src/ubundiforge/runner.py`
- Modify: `tests/test_runner.py`

- [ ] **Step 1: Write failing tests for activity tracking**

```python
# Append to tests/test_runner.py
from ubundiforge.runner import ActivityTracker


def test_activity_tracker_add_new_summary():
    tracker = ActivityTracker()
    tracker.update("Reviewing the scaffold brief")
    assert len(tracker.steps) == 1
    assert tracker.steps[0]["summary"] == "Reviewing the scaffold brief"
    assert tracker.current == "Reviewing the scaffold brief"


def test_activity_tracker_deduplicates_consecutive():
    tracker = ActivityTracker()
    tracker.update("Writing and refining project files")
    tracker.update("Writing and refining project files")
    assert len(tracker.steps) == 1


def test_activity_tracker_adds_different_summary():
    tracker = ActivityTracker()
    tracker.update("Reviewing the scaffold brief")
    tracker.update("Writing and refining project files")
    assert len(tracker.steps) == 2
    assert tracker.steps[0]["summary"] == "Reviewing the scaffold brief"
    assert tracker.steps[1]["summary"] == "Writing and refining project files"
    assert tracker.current == "Writing and refining project files"


def test_activity_tracker_max_visible():
    tracker = ActivityTracker(max_visible=3)
    for i in range(5):
        tracker.update(f"Step {i}")
    visible = tracker.visible_steps()
    assert len(visible) == 3
    assert visible[0]["summary"] == "Step 2"
    assert visible[-1]["summary"] == "Step 4"


def test_activity_tracker_marks_completed():
    tracker = ActivityTracker()
    tracker.update("Step one")
    tracker.update("Step two")
    assert tracker.steps[0]["completed"] is True
    assert tracker.steps[1]["completed"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_runner.py::test_activity_tracker_add_new_summary -v`
Expected: FAIL with `ImportError: cannot import name 'ActivityTracker'`

- [ ] **Step 3: Implement `ActivityTracker`**

Add to `src/ubundiforge/runner.py` (after the existing imports):

```python
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
        self.steps.append({
            "summary": summary,
            "completed": False,
            "timestamp": time.monotonic(),
        })
        self.current = summary

    def visible_steps(self) -> list[dict]:
        """Return the most recent steps up to max_visible."""
        return self.steps[-self._max_visible:]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_runner.py -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 5: Lint and format**

Run: `uv run ruff check src/ubundiforge/runner.py tests/test_runner.py && uv run ruff format src/ubundiforge/runner.py tests/test_runner.py`

- [ ] **Step 6: Commit**

```bash
git add src/ubundiforge/runner.py tests/test_runner.py
git commit -m "feat(runner): add ActivityTracker for activity feed"
```

---

## Task 5: Activity Feed — Loader Panel Integration

Update `make_loader_panel` to render the activity feed and wire `ActivityTracker` into `run_ai`.

**Files:**
- Modify: `src/ubundiforge/ui.py:173-199` (`make_loader_panel`)
- Modify: `src/ubundiforge/runner.py` (`run_ai` function)

- [ ] **Step 1: Write failing test for updated loader panel**

```python
# Append to tests/test_dashboard.py (or a new tests/test_ui.py)
from io import StringIO

from rich.console import Console

from ubundiforge.ui import make_loader_panel


def test_loader_panel_with_activity_feed():
    """make_loader_panel accepts and renders an activity list."""
    activities = [
        {"summary": "Reviewing the scaffold brief", "completed": True},
        {"summary": "Writing and refining project files", "completed": False},
    ]
    panel = make_loader_panel(
        "Architecture & Core",
        "Writing and refining project files",
        elapsed=42.0,
        spinner_frame="⠹",
        spinner_style="#A16EFA",
        accent="violet",
        activities=activities,
    )
    # Should render without error
    console = Console(file=StringIO(), width=80)
    console.print(panel)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dashboard.py::test_loader_panel_with_activity_feed -v`
Expected: FAIL with `TypeError: make_loader_panel() got an unexpected keyword argument 'activities'`

- [ ] **Step 3: Update `make_loader_panel` in `ui.py`**

Modify the function signature and body in `src/ubundiforge/ui.py`:

```python
def make_loader_panel(
    title: str,
    summary: str,
    *,
    elapsed: float,
    spinner_frame: str,
    spinner_style: str,
    accent: str = "violet",
    detail: str | None = None,
    activities: list[dict] | None = None,
) -> Panel:
    """Create a polished live loader panel for long-running CLI work."""
    header = Text()
    header.append(f"{spinner_frame} ", style=f"bold {spinner_style}")
    header.append(title, style=f"bold {TEXT_PRIMARY}")
    header.append("  ", style="")
    header.append(f"{elapsed:.0f}s", style=TEXT_MUTED)

    lines: list[Text] = [header]

    if activities:
        for step in activities:
            line = Text("  ")
            if step["completed"]:
                line.append("✓ ", style=ACCENTS["aqua"])
                line.append(step["summary"], style=TEXT_MUTED)
            else:
                line.append(f"{spinner_frame} ", style=f"bold {spinner_style}")
                line.append(step["summary"], style=f"bold {TEXT_SECONDARY}")
            lines.append(line)
    else:
        lines.append(Text(summary, style=f"bold {TEXT_SECONDARY}"))
        if detail:
            lines.append(Text(detail, style=TEXT_MUTED))

    return make_panel(
        grouped_lines(lines),
        title="In Progress",
        accent=accent,
        padding=(0, 1),
    )
```

- [ ] **Step 4: Wire `ActivityTracker` into `run_ai`**

In `src/ubundiforge/runner.py`, modify the `run_ai` function:

Replace the `summary` and `last_line` tracking with an `ActivityTracker`. In `_stream_stdout`, call `tracker.update(new_summary)` when the summary changes. In the Live loop, pass `activities=tracker.visible_steps()` to `make_loader_panel`.

Key changes in `run_ai`:
```python
# Replace:
summary = _initial_phase_summary(display_label, backend)
last_line = ""

# With:
tracker = ActivityTracker()
tracker.update(_initial_phase_summary(display_label, backend))
last_line = ""
```

In `_stream_stdout`:
```python
# Replace:
summary = _progress_summary_for_line(clean, summary)

# With:
new_summary = _summarize_output_line(clean)
if new_summary and new_summary != tracker.current:
    tracker.update(new_summary)
```

In the Live update loop:
```python
live.update(
    make_loader_panel(
        display_label,
        tracker.current,
        elapsed=elapsed,
        spinner_frame=_spinner_frame(elapsed),
        spinner_style=_spinner_style(accent, elapsed),
        accent=accent,
        detail=current_detail,
        activities=tracker.visible_steps(),
    )
)
```

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Lint and format**

Run: `uv run ruff check src/ubundiforge/ui.py src/ubundiforge/runner.py && uv run ruff format src/ubundiforge/ui.py src/ubundiforge/runner.py`

- [ ] **Step 7: Commit**

```bash
git add src/ubundiforge/ui.py src/ubundiforge/runner.py
git commit -m "feat(runner): integrate activity feed into loader panel"
```

---

## Task 6: Phase Timeline — Renderable

Build the phase timeline Rich renderable shown above the loader during scaffold execution.

**Files:**
- Modify: `src/ubundiforge/ui.py`
- Create: `tests/test_ui.py`

- [ ] **Step 1: Write failing tests for phase timeline**

```python
# tests/test_ui.py
"""Tests for UI renderables."""

from io import StringIO

from rich.console import Console

from ubundiforge.ui import make_phase_timeline


def test_phase_timeline_renders():
    """Phase timeline renders without error."""
    phases = [
        {"label": "Architecture & Core", "status": "completed", "elapsed": 42.0, "accent": "violet"},
        {"label": "Frontend & UI", "status": "active", "elapsed": 18.0, "accent": "amber"},
        {"label": "Tests & Automation", "status": "pending", "elapsed": 0.0, "accent": "aqua"},
        {"label": "Verify & Fix", "status": "pending", "elapsed": 0.0, "accent": "violet"},
    ]
    renderable = make_phase_timeline(phases)
    console = Console(file=StringIO(), width=80)
    console.print(renderable)


def test_phase_timeline_single_phase():
    """Timeline works with a single phase."""
    phases = [
        {"label": "Architecture & Core", "status": "active", "elapsed": 10.0, "accent": "violet"},
    ]
    renderable = make_phase_timeline(phases)
    console = Console(file=StringIO(), width=80)
    console.print(renderable)


def test_phase_timeline_all_completed():
    """Timeline works when all phases are done."""
    phases = [
        {"label": "Architecture & Core", "status": "completed", "elapsed": 42.0, "accent": "violet"},
        {"label": "Tests & Automation", "status": "completed", "elapsed": 30.0, "accent": "aqua"},
    ]
    renderable = make_phase_timeline(phases)
    console = Console(file=StringIO(), width=80)
    console.print(renderable)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ui.py -v`
Expected: FAIL with `ImportError: cannot import name 'make_phase_timeline'`

- [ ] **Step 3: Implement `make_phase_timeline`**

Add to `src/ubundiforge/ui.py`:

```python
def make_phase_timeline(phases: list[dict]) -> Group:
    """Create a horizontal phase progress indicator.

    Each phase dict has: label, status (completed/active/pending), elapsed, accent.
    """
    # Phase labels row
    label_line = Text("  ")
    for phase in phases:
        if phase["status"] == "completed":
            label_line.append("● ", style=ACCENTS["aqua"])
            label_line.append(phase["label"], style=TEXT_MUTED)
            label_line.append(f" {phase['elapsed']:.0f}s", style=TEXT_MUTED)
        elif phase["status"] == "active":
            label_line.append("◉ ", style=ACCENTS[phase["accent"]])
            label_line.append(phase["label"], style=f"bold {TEXT_PRIMARY}")
            label_line.append(f" {phase['elapsed']:.0f}s", style=TEXT_MUTED)
        else:
            label_line.append("○ ", style=TEXT_MUTED)
            label_line.append(phase["label"], style=TEXT_MUTED)
        label_line.append("   ", style="")

    # Progress bar
    total = len(phases)
    completed = sum(1 for p in phases if p["status"] == "completed")
    active = sum(1 for p in phases if p["status"] == "active")
    bar_width = min(60, total * 15)

    completed_width = int(bar_width * completed / total)
    active_width = int(bar_width * active / total) if active else 0
    remaining_width = bar_width - completed_width - active_width

    bar = Text("  ")
    if completed_width:
        bar.append("━" * completed_width, style=ACCENTS["aqua"])
    if active_width:
        active_accent = next((p["accent"] for p in phases if p["status"] == "active"), "violet")
        bar.append("━" * active_width, style=ACCENTS[active_accent])
    if remaining_width:
        bar.append("━" * remaining_width, style=ACCENTS["indigo"])

    return Group(label_line, bar)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ui.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Lint and format**

Run: `uv run ruff check src/ubundiforge/ui.py tests/test_ui.py && uv run ruff format src/ubundiforge/ui.py tests/test_ui.py`

- [ ] **Step 6: Commit**

```bash
git add src/ubundiforge/ui.py tests/test_ui.py
git commit -m "feat(ui): add phase timeline renderable"
```

---

## Task 7: Phase Timeline — Runner Integration

Wire the phase timeline into `run_ai` so it appears above the loader panel. This requires `run_ai` to accept phase context.

**Note:** This task wires the timeline into serial `run_ai` calls only. Parallel execution (`run_ai_parallel`) integration is deferred — the parallel loader already shows multi-phase progress via `_PhaseProgress`. Adding the timeline to the parallel path is a follow-up improvement.

**Files:**
- Modify: `src/ubundiforge/runner.py`
- Modify: `src/ubundiforge/cli.py`

- [ ] **Step 1: Add `phase_context` parameter to `run_ai`**

In `src/ubundiforge/runner.py`, update `run_ai` signature to accept optional phase timeline data:

```python
def run_ai(
    backend: str,
    prompt: str,
    project_dir: Path,
    model: str | None = None,
    verbose: bool = False,
    label: str = "",
    phase_context: list[dict] | None = None,
) -> int:
```

When `phase_context` is provided, compose a `Group` with the timeline above the loader panel in the Live update:

```python
from ubundiforge.ui import make_phase_timeline

# In the Live update loop:
if phase_context:
    renderable = Group(
        make_phase_timeline(phase_context),
        Text(),  # spacer
        loader_panel,
    )
else:
    renderable = loader_panel
live.update(renderable)
```

- [ ] **Step 2: Pass phase context from `cli.py`**

In `src/ubundiforge/cli.py`, build a `phase_context` list before the execution loop. Update it as each phase completes.

**First**, move `_BACKEND_ACCENTS` from `runner.py` to `ui.py` so both modules can import it. In `ui.py`, add:
```python
BACKEND_ACCENTS: dict[str, str] = {
    "claude": "violet",
    "gemini": "amber",
    "codex": "aqua",
}
```
Update `runner.py` to import from `ui.py`: `from ubundiforge.ui import BACKEND_ACCENTS` and remove the old `_BACKEND_ACCENTS` dict. Update all references in `runner.py` from `_BACKEND_ACCENTS` to `BACKEND_ACCENTS`.

**Then** in `cli.py`:
```python
from ubundiforge.ui import BACKEND_ACCENTS

# Before phase execution
phase_context = []
for phase, backend in phase_backends:
    phase_context.append({
        "label": PHASE_LABELS.get(phase, phase),
        "status": "pending",
        "elapsed": 0.0,
        "accent": BACKEND_ACCENTS.get(backend, "violet"),
    })
```

Before each `run_ai` call, set the current phase to "active". After it returns, set to "completed" with elapsed time. Pass `phase_context=phase_context` to each `run_ai` call.

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS. Existing `run_ai` callers that don't pass `phase_context` get the default (None) and behave as before.

- [ ] **Step 4: Smoke test**

Run: `./forge --dry-run --name smoke --stack fastapi --description "test" --no-docker`
Expected: No errors (dry-run doesn't trigger `run_ai`, so no visual change, but imports work)

- [ ] **Step 5: Lint and format**

Run: `uv run ruff check src/ubundiforge/runner.py src/ubundiforge/cli.py && uv run ruff format src/ubundiforge/runner.py src/ubundiforge/cli.py`

- [ ] **Step 6: Commit**

```bash
git add src/ubundiforge/runner.py src/ubundiforge/cli.py
git commit -m "feat(runner): integrate phase timeline into scaffold execution"
```

---

## Task 8: File Tree Growth Visualization

Render a color-coded file tree after each phase showing what was created.

**Files:**
- Modify: `src/ubundiforge/ui.py`
- Modify: `tests/test_ui.py`
- Modify: `src/ubundiforge/cli.py`

- [ ] **Step 1: Write failing tests for file tree**

```python
# Append to tests/test_ui.py
from pathlib import Path

from ubundiforge.ui import make_file_tree


def _render_to_string(renderable) -> str:
    """Render a Rich renderable to a plain string."""
    console = Console(file=StringIO(), width=80, color_system=None)
    console.print(renderable)
    return console.file.getvalue()


def test_file_tree_renders_files(tmp_path: Path):
    """File tree renders a directory with files."""
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "routes.py").write_text("x = 1\n")
    (tmp_path / "pyproject.toml").write_text("[project]\n")

    tree = make_file_tree(tmp_path)
    console = Console(file=StringIO(), width=80)
    console.print(tree)


def test_file_tree_ignores_hidden(tmp_path: Path):
    """File tree skips .git and other hidden directories."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x\n")
    (tmp_path / "main.py").write_text("x = 1\n")

    tree = make_file_tree(tmp_path)
    output = _render_to_string(tree)
    assert ".git" not in output
    assert "main.py" in output


def test_file_tree_empty_dir(tmp_path: Path):
    """File tree handles an empty directory."""
    tree = make_file_tree(tmp_path)
    console = Console(file=StringIO(), width=80)
    console.print(tree)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ui.py::test_file_tree_renders_files -v`
Expected: FAIL with `ImportError: cannot import name 'make_file_tree'`

- [ ] **Step 3: Implement `make_file_tree`**

Add to `src/ubundiforge/ui.py`:

```python
from rich.tree import Tree


_HIDDEN_TREE_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".forge", ".ruff_cache"}
_CONFIG_FILES = {"pyproject.toml", "package.json", "Dockerfile", "docker-compose.yml",
                 "tsconfig.json", ".env.example", "CLAUDE.md", ".pre-commit-config.yaml",
                 ".gitignore", "next.config.ts", "tailwind.config.ts", "vitest.config.ts"}


def make_file_tree(project_dir: Path) -> Group:
    """Render a color-coded file tree of a scaffolded project."""
    tree = Tree(
        Text(f"{project_dir.name}/", style=f"bold {ACCENTS['aqua']}"),
        guide_style=TEXT_MUTED,
    )

    file_count = 0
    line_count = 0

    def _add_dir(parent_tree: Tree, directory: Path) -> None:
        nonlocal file_count, line_count
        entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name))
        for entry in entries:
            name = entry.name
            if name in _HIDDEN_TREE_DIRS or name.startswith("."):
                if name not in _CONFIG_FILES:
                    continue
            if entry.is_dir():
                branch = parent_tree.add(Text(f"{name}/", style=ACCENTS["violet"]))
                _add_dir(branch, entry)
            else:
                file_count += 1
                try:
                    line_count += len(entry.read_text(errors="replace").splitlines())
                except OSError:
                    pass
                if name in _CONFIG_FILES:
                    parent_tree.add(Text(name, style=ACCENTS["plum"]))
                else:
                    parent_tree.add(Text(name, style=ACCENTS["aqua"]))

    _add_dir(tree, project_dir)

    summary = Text("  ")
    summary.append(str(file_count), style=f"bold {ACCENTS['amber']}")
    summary.append(" files", style=TEXT_MUTED)
    summary.append(" · ", style=TEXT_MUTED)
    summary.append(f"{line_count:,}", style=f"bold {ACCENTS['amber']}")
    summary.append(" lines", style=TEXT_MUTED)

    return Group(tree, summary)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ui.py -v`
Expected: All tests PASS

- [ ] **Step 5: Wire into cli.py**

In `src/ubundiforge/cli.py`, after each phase's `run_ai` call returns successfully, add:

```python
from ubundiforge.ui import make_file_tree
# After successful run_ai call:
console.print()
console.print(make_file_tree(project_dir))
```

Also add the same file tree rendering after the `run_ai_parallel` results block (after the success check loop for parallel phases):
```python
# After parallel phase success checks:
console.print()
console.print(make_file_tree(project_dir))
```

- [ ] **Step 6: Run full test suite and lint**

Run: `uv run pytest tests/ -v && uv run ruff check src/ubundiforge/ui.py src/ubundiforge/cli.py`

- [ ] **Step 7: Commit**

```bash
git add src/ubundiforge/ui.py src/ubundiforge/cli.py tests/test_ui.py
git commit -m "feat(ui): add color-coded file tree visualization between phases"
```

---

## Task 9: Final Integration Test and Cleanup

Run the full test suite, lint, and do a dry-run smoke test to verify everything works together.

**Files:**
- All modified files from Tasks 1-8

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run linter**

Run: `uv run ruff check src/ubundiforge tests`
Expected: No errors

- [ ] **Step 3: Run formatter**

Run: `uv run ruff format src/ubundiforge tests`

- [ ] **Step 4: Dry-run smoke test**

Run: `./forge --dry-run --name smoke --stack fastapi --description "test" --no-docker`
Expected: Forge runs through the full prompt assembly without errors

- [ ] **Step 5: Remove unused imports/functions**

Check if `_render_completion` and `_render_next_steps` in `cli.py` are still referenced anywhere. If not, remove them. Similarly, check if the old `print_report` call site is still needed (it was replaced by the dashboard's health check section).

- [ ] **Step 6: Final commit**

```bash
git add -u
git commit -m "chore: cleanup unused functions after dashboard integration"
```

---

## Notes for Phases 2 and 3

This plan covers Phase 1 (Visual Polish) only. Phases 2 and 3 will get their own implementation plans when ready:

- **Phase 2 (Intelligence):** Quality memory, smart defaults, forge stats, forge evolve
- **Phase 3 (Signature):** forge check, scaffold replay, forge card, completion sound

Phase 2 depends on Phase 1 for the `VerifyReport` data flow (quality memory extracts signals from verify results, which Phase 1 plumbs through properly).
