"""Tests for the runner module."""

import stat
import subprocess
import sys
from pathlib import Path

from projectforge.runner import (
    ActivityTracker,
    ProviderExit,
    _build_cmd,
    _initial_phase_summary,
    ensure_git_init,
    initialize_git_repository,
    reset_project_dir,
    run_ai,
    run_ai_parallel,
    run_post_scaffold_hook,
)
from projectforge.subprocess_utils import progress_summary_for_line as _progress_summary_for_line


def test_claude_cmd_basic():
    cmd = _build_cmd("claude", "do stuff")
    assert cmd == [
        "claude",
        "--safe-mode",
        "-p",
        "--permission-mode",
        "acceptEdits",
        "--no-session-persistence",
        "do stuff",
    ]


def test_claude_cmd_with_model():
    cmd = _build_cmd("claude", "do stuff", model="opus")
    assert cmd == [
        "claude",
        "--safe-mode",
        "-p",
        "--permission-mode",
        "acceptEdits",
        "--no-session-persistence",
        "--model",
        "opus",
        "do stuff",
    ]


def test_antigravity_cmd_basic():
    cmd = _build_cmd("antigravity", "do stuff")
    assert cmd == [
        "agy",
        "--mode",
        "accept-edits",
        "--sandbox",
        "--print",
        "do stuff",
    ]


def test_antigravity_cmd_with_model():
    cmd = _build_cmd("antigravity", "do stuff", model="flash")
    assert cmd == [
        "agy",
        "--mode",
        "accept-edits",
        "--sandbox",
        "--model",
        "flash",
        "--print",
        "do stuff",
    ]


def test_codex_cmd_basic():
    cmd = _build_cmd("codex", "do stuff")
    assert cmd == [
        "codex",
        "--ask-for-approval",
        "never",
        "--sandbox",
        "workspace-write",
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-user-config",
        "--color",
        "never",
        "do stuff",
    ]


def test_codex_cmd_with_model():
    cmd = _build_cmd("codex", "do stuff", model="o3")
    assert cmd == [
        "codex",
        "--ask-for-approval",
        "never",
        "--sandbox",
        "workspace-write",
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-user-config",
        "--color",
        "never",
        "--model",
        "o3",
        "do stuff",
    ]


def test_provider_commands_bind_an_explicit_workspace(tmp_path):
    claude = _build_cmd("claude", "do stuff", project_dir=tmp_path)
    assert "--safe-mode" in claude

    codex = _build_cmd("codex", "do stuff", project_dir=tmp_path)
    assert codex[codex.index("--cd") + 1] == str(tmp_path.resolve())

    antigravity = _build_cmd("antigravity", "do stuff", project_dir=tmp_path)
    assert antigravity[antigravity.index("--add-dir") + 1] == str(tmp_path.resolve())
    assert antigravity[-2:] == ["--print", "do stuff"]


def test_unknown_backend_returns_empty():
    cmd = _build_cmd("unknown", "do stuff")
    assert cmd == []


def test_run_ai_executes_provider_command_and_returns_integer_compatible_exit(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        "projectforge.runner._build_cmd",
        lambda *_args, **_kwargs: [sys.executable, "-c", "print('Applying patch')"],
    )

    result = run_ai("claude", "prompt", tmp_path / "generated", label="Architecture & Core")

    assert isinstance(result, ProviderExit)
    assert result == 0
    assert result.failure_category is None
    assert (tmp_path / "generated").is_dir()


def test_run_ai_gives_provider_no_inherited_stdin(monkeypatch, tmp_path):
    # Headless providers receive their prompt as an argument and must never
    # block reading Forge's stdin. Popen passes stdin=DEVNULL so a child that
    # reads stdin gets immediate EOF instead of hanging on the terminal.
    monkeypatch.setattr(
        "projectforge.runner._build_cmd",
        lambda *_args, **_kwargs: [
            sys.executable,
            "-c",
            "import sys; sys.exit(0 if sys.stdin.read() == '' else 3)",
        ],
    )

    result = run_ai("codex", "prompt", tmp_path / "generated", label="Architecture & Core")

    assert result == 0


def test_run_ai_classifies_provider_failure_without_echoing_output(
    monkeypatch,
    tmp_path,
    capsys,
):
    private_output = "authentication failed for private-account@example.com"
    monkeypatch.setattr(
        "projectforge.runner._build_cmd",
        lambda *_args, **_kwargs: [
            sys.executable,
            "-c",
            f"import sys; print({private_output!r}); sys.exit(9)",
        ],
    )

    result = run_ai("claude", "prompt", tmp_path / "generated", label="Architecture & Core")

    assert result == 9
    assert result.failure_category == "authentication"
    assert private_output not in capsys.readouterr().out


def test_run_ai_treats_antigravity_headless_permission_as_failure(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        "projectforge.runner._build_cmd",
        lambda *_args, **_kwargs: [
            sys.executable,
            "-c",
            "print('no output produced: write_file permission denied in headless mode')",
        ],
    )

    result = run_ai(
        "antigravity",
        "prompt",
        tmp_path / "generated",
        label="Frontend & UI",
    )

    assert result == 1
    assert result.failure_category == "permission"


def test_run_ai_parallel_preserves_phase_order_and_failure_categories(monkeypatch, tmp_path):
    def command_for_phase(_backend, prompt, *_args, **_kwargs):
        if prompt == "fail":
            return [
                sys.executable,
                "-c",
                "import sys; print('login required'); sys.exit(9)",
            ]
        return [sys.executable, "-c", "print('Applying patch')"]

    monkeypatch.setattr("projectforge.runner._build_cmd", command_for_phase)

    results = run_ai_parallel(
        [
            {"label": "Frontend & UI", "backend": "antigravity", "prompt": "ok"},
            {"label": "Tests & Automation", "backend": "codex", "prompt": "fail"},
        ],
        tmp_path / "generated",
    )

    assert [(label, int(exit_code)) for label, exit_code in results] == [
        ("Frontend & UI", 0),
        ("Tests & Automation", 9),
    ]
    assert results[1][1].failure_category == "authentication"


def test_initial_phase_summary_matches_known_phase_labels():
    assert (
        _initial_phase_summary("Architecture & Core", "claude")
        == "Designing the project foundation"
    )
    assert (
        _initial_phase_summary("Frontend & UI", "antigravity")
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


def test_progress_output_redacts_credential_shaped_values():
    from projectforge.subprocess_utils import sanitize_progress_line

    clean = sanitize_progress_line("clone failed: ghp_abcdefghijklmnopqrstuvwxyz1234567890")

    assert "ghp_" not in clean
    assert "REDACTED" in clean


def test_progress_summary_for_line_does_not_forward_unmatched_or_noisy_updates():
    current = "Setting up tests and developer workflows"

    assert _progress_summary_for_line("Internal tool detail: request abc-123", current) == current
    assert _progress_summary_for_line("$ cat src/app/page.tsx", current) == current
    assert _progress_summary_for_line("Traceback at /private/project/tool.py", current) == (
        "Working through an issue in the scaffold"
    )


def test_initialize_git_repository_creates_unborn_main_branch(tmp_path):
    project_dir = tmp_path / "demo"

    assert initialize_git_repository(project_dir) is True

    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=project_dir,
        capture_output=True,
    )
    assert branch.stdout.strip() == "main"
    assert head.returncode != 0

    (project_dir / ".forge").mkdir()
    (project_dir / ".forge" / "progress.json").write_text("{}\n")
    ignored = subprocess.run(
        ["git", "check-ignore", ".forge/progress.json"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0


def test_ensure_git_init_commits_final_changes_after_provider_commit(tmp_path):
    project_dir = tmp_path / "demo"
    assert initialize_git_repository(project_dir) is True
    subprocess.run(["git", "config", "user.name", "Forge Test"], cwd=project_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "forge-test"],
        cwd=project_dir,
        check=True,
    )
    (project_dir / "README.md").write_text("Initial\n")
    assert ensure_git_init(project_dir) is True

    (project_dir / "README.md").write_text("Initial\n\nFinal badge\n")
    assert ensure_git_init(project_dir) is True

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    commit_count = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    assert status.stdout == ""
    assert commit_count.stdout.strip() == "2"


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
    monkeypatch.setattr("projectforge.runner.POST_SCAFFOLD_HOOK", tmp_path / "nope.sh")
    assert run_post_scaffold_hook(tmp_path, {"name": "demo"}) is True


def test_post_scaffold_hook_runs_script(tmp_path, monkeypatch):
    hook_path = tmp_path / "hook.sh"
    marker = tmp_path / "marker.txt"
    hook_path.write_text(f'#!/bin/bash\necho "$FORGE_PROJECT_NAME" > {marker}\n')
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

    monkeypatch.setattr("projectforge.runner.POST_SCAFFOLD_HOOK", hook_path)

    project_dir = tmp_path / "my-project"
    project_dir.mkdir()

    result = run_post_scaffold_hook(project_dir, {"name": "my-project", "stack": "nextjs"})
    assert result is True
    assert marker.read_text().strip() == "my-project"


def test_post_scaffold_hook_returns_false_on_failure(tmp_path, monkeypatch, capsys):
    hook_path = tmp_path / "hook.sh"
    hook_path.write_text(
        "#!/bin/bash\necho 'private stdout detail'\necho 'private stderr detail' >&2\nexit 1\n"
    )
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

    monkeypatch.setattr("projectforge.runner.POST_SCAFFOLD_HOOK", hook_path)

    project_dir = tmp_path / "fail-project"
    project_dir.mkdir()

    result = run_post_scaffold_hook(project_dir, {"name": "fail-project"})
    assert result is False
    output = capsys.readouterr().out
    assert "did not finish successfully" in output
    assert "private stdout detail" not in output
    assert "private stderr detail" not in output
    assert "code 1" not in output


def test_post_scaffold_hook_passes_env_vars(tmp_path, monkeypatch):
    hook_path = tmp_path / "hook.sh"
    env_dump = tmp_path / "env.txt"
    hook_path.write_text(f'#!/bin/bash\necho "$FORGE_STACK:$FORGE_DEMO_MODE" > {env_dump}\n')
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

    monkeypatch.setattr("projectforge.runner.POST_SCAFFOLD_HOOK", hook_path)

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
