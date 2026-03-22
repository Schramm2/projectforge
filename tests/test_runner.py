"""Tests for the runner module."""

import stat
from pathlib import Path

from ubundiforge.runner import (
    ActivityTracker,
    _build_cmd,
    _initial_phase_summary,
    reset_project_dir,
    run_post_scaffold_hook,
)
from ubundiforge.subprocess_utils import progress_summary_for_line as _progress_summary_for_line


def test_claude_cmd_basic():
    cmd = _build_cmd("claude", "do stuff")
    assert cmd == ["claude", "-p", "--dangerously-skip-permissions", "do stuff"]


def test_claude_cmd_with_model():
    cmd = _build_cmd("claude", "do stuff", model="opus")
    assert cmd == [
        "claude",
        "-p",
        "--dangerously-skip-permissions",
        "--model",
        "opus",
        "do stuff",
    ]


def test_gemini_cmd_basic():
    cmd = _build_cmd("gemini", "do stuff")
    assert cmd == ["gemini", "-p", "do stuff", "-y"]


def test_gemini_cmd_with_model():
    cmd = _build_cmd("gemini", "do stuff", model="flash")
    assert cmd == ["gemini", "-p", "do stuff", "-y", "--model", "flash"]


def test_codex_cmd_basic():
    cmd = _build_cmd("codex", "do stuff")
    assert cmd == [
        "codex",
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "do stuff",
    ]


def test_codex_cmd_with_model():
    cmd = _build_cmd("codex", "do stuff", model="o3")
    assert cmd == [
        "codex",
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--model",
        "o3",
        "do stuff",
    ]


def test_unknown_backend_returns_empty():
    cmd = _build_cmd("unknown", "do stuff")
    assert cmd == []


def test_initial_phase_summary_matches_known_phase_labels():
    assert (
        _initial_phase_summary("Architecture & Core", "claude")
        == "Designing the project foundation"
    )
    assert (
        _initial_phase_summary("Frontend & UI", "gemini")
        == "Shaping the interface and app structure"
    )
    assert (
        _initial_phase_summary("Tests & Automation", "codex")
        == "Setting up tests and developer workflows"
    )
    assert (
        _initial_phase_summary("Verify & Fix", "claude")
        == "Checking the scaffold and smoothing rough edges"
    )


def test_progress_summary_for_line_maps_common_backend_output_to_clean_loader_copy():
    current = "Designing the project foundation"

    assert (
        _progress_summary_for_line("Inspecting the existing files first", current)
        == "Reviewing the scaffold brief"
    )
    assert (
        _progress_summary_for_line("Running pnpm install", current)
        == "Installing project dependencies"
    )
    assert (
        _progress_summary_for_line("Applying patch to app/page.tsx", current)
        == "Writing and refining project files"
    )
    assert _progress_summary_for_line("Running pytest -q", current) == "Running tests and checks"
    assert (
        _progress_summary_for_line("Starting dev server on localhost:3000", current)
        == "Starting the app locally"
    )


def test_progress_summary_for_line_uses_clean_fallback_for_non_noisy_updates():
    current = "Setting up tests and developer workflows"

    assert (
        _progress_summary_for_line("Refining the empty state for the dashboard shell", current)
        == "Refining the empty state for the dashboard shell"
    )
    assert _progress_summary_for_line("$ cat src/app/page.tsx", current) == current


def test_reset_project_dir_clears_existing_contents(tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("stale")
    nested_dir = project_dir / "src"
    nested_dir.mkdir()
    (nested_dir / "main.py").write_text("print('stale')")

    reset_project_dir(project_dir)

    assert project_dir.exists()
    assert list(project_dir.iterdir()) == []


def test_reset_project_dir_creates_missing_directory(tmp_path):
    project_dir = tmp_path / "new-project"

    reset_project_dir(project_dir)

    assert project_dir.exists()
    assert isinstance(project_dir, Path)


def test_post_scaffold_hook_returns_true_when_no_hook(tmp_path, monkeypatch):
    monkeypatch.setattr("ubundiforge.runner.POST_SCAFFOLD_HOOK", tmp_path / "nope.sh")
    assert run_post_scaffold_hook(tmp_path, {"name": "demo"}) is True


def test_post_scaffold_hook_runs_script(tmp_path, monkeypatch):
    hook_path = tmp_path / "hook.sh"
    marker = tmp_path / "marker.txt"
    hook_path.write_text(f'#!/bin/bash\necho "$FORGE_PROJECT_NAME" > {marker}\n')
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

    monkeypatch.setattr("ubundiforge.runner.POST_SCAFFOLD_HOOK", hook_path)

    project_dir = tmp_path / "my-project"
    project_dir.mkdir()

    result = run_post_scaffold_hook(project_dir, {"name": "my-project", "stack": "nextjs"})
    assert result is True
    assert marker.read_text().strip() == "my-project"


def test_post_scaffold_hook_returns_false_on_failure(tmp_path, monkeypatch):
    hook_path = tmp_path / "hook.sh"
    hook_path.write_text("#!/bin/bash\nexit 1\n")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

    monkeypatch.setattr("ubundiforge.runner.POST_SCAFFOLD_HOOK", hook_path)

    project_dir = tmp_path / "fail-project"
    project_dir.mkdir()

    result = run_post_scaffold_hook(project_dir, {"name": "fail-project"})
    assert result is False


def test_post_scaffold_hook_passes_env_vars(tmp_path, monkeypatch):
    hook_path = tmp_path / "hook.sh"
    env_dump = tmp_path / "env.txt"
    hook_path.write_text(f'#!/bin/bash\necho "$FORGE_STACK:$FORGE_DEMO_MODE" > {env_dump}\n')
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

    monkeypatch.setattr("ubundiforge.runner.POST_SCAFFOLD_HOOK", hook_path)

    project_dir = tmp_path / "env-project"
    project_dir.mkdir()

    run_post_scaffold_hook(
        project_dir, {"name": "env-project", "stack": "fastapi", "demo_mode": True}
    )
    assert env_dump.read_text().strip() == "fastapi:1"


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
