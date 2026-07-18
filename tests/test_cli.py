"""Tests for CLI execution paths."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from rich.console import Console
from typer.testing import CliRunner

from ubundiforge import __version__
from ubundiforge.cli import app
from ubundiforge.config import BackendStatus
from ubundiforge.convention_models import ConventionValidationError
from ubundiforge.setup import run_setup

runner = CliRunner()


def test_version_output_uses_public_project_name():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"projectforge {__version__}"
    assert "ubundiforge" not in result.stdout.lower()


def test_doctor_json_has_deterministic_exit_semantics(monkeypatch):
    report = {
        "schema_version": 1,
        "projectforge_version": __version__,
        "status": "attention",
        "config": {"status": "missing"},
        "providers": {},
    }
    monkeypatch.setattr("ubundiforge.cli.build_doctor_report", lambda: report)

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.stdout) == report


def test_doctor_human_output_includes_model_behavior_and_repair(monkeypatch):
    report = {
        "schema_version": 1,
        "projectforge_version": __version__,
        "status": "attention",
        "config": {"status": "valid"},
        "environment": {
            "python": {"version": "3.12.1", "supported": True},
            "git": {"installed": True, "version": "git version 2.50.0"},
            "docker": {"installed": False, "version": None},
            "editors": {},
        },
        "providers": {
            "claude": {
                "readiness": "needs_login",
                "version": "2.1.214",
                "auth_mode": None,
                "model_behavior": {"mode": "provider_default", "value": None},
                "repair": "Run claude auth login, then rerun forge doctor.",
            }
        },
    }
    monkeypatch.setattr("ubundiforge.cli.build_doctor_report", lambda: report)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "model: provider default" in result.stdout
    assert "claude auth login" in result.stdout


def test_doctor_help_promises_auth_check_without_model_calls():
    result = runner.invoke(app, ["doctor", "--help"], env={"TERM": "dumb"})
    output = " ".join(result.stdout.lower().split())

    assert result.exit_code == 0
    assert "authentication without model calls" in output
    assert "--preflight" not in result.stdout


def test_live_unsafe_mode_requires_explicit_cli_consent():
    result = runner.invoke(
        app,
        [
            "--approval-mode",
            "unsafe",
            "--name",
            "unsafe-demo",
            "--stack",
            "fastapi",
            "--description",
            "Must not start",
        ],
    )

    assert result.exit_code == 1
    assert "explicit consent" in result.stdout.lower()


def test_provider_running_commands_expose_approval_controls():
    plain_help_env = {"TERM": "dumb"}
    root_help = runner.invoke(app, ["--help"], env=plain_help_env)
    evolve_help = runner.invoke(app, ["evolve", "--help"], env=plain_help_env)
    replay_help = runner.invoke(app, ["replay", "--help"], env=plain_help_env)

    assert root_help.exit_code == 0
    assert evolve_help.exit_code == 0
    assert replay_help.exit_code == 0
    for output in (root_help.stdout, evolve_help.stdout, replay_help.stdout):
        assert "--approval-mode" in output
        assert "--allow-unsafe" in output


def _patch_prompt_only_dependencies(monkeypatch, *, setup_called: list[bool]) -> None:
    monkeypatch.setattr("ubundiforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("ubundiforge.cli.needs_setup", lambda: True)
    monkeypatch.setattr("ubundiforge.cli.load_forge_config", lambda: {})
    monkeypatch.setattr(
        "ubundiforge.cli.get_backend_statuses",
        lambda: {
            backend: BackendStatus(installed=False, ready=False)
            for backend in ("claude", "antigravity", "codex")
        },
    )
    monkeypatch.setattr("ubundiforge.router.check_backend_installed", lambda backend: False)
    monkeypatch.setattr(
        "ubundiforge.cli.load_conventions",
        lambda stack=None: ("Use strict typing.", []),
    )
    monkeypatch.setattr("ubundiforge.cli.load_claude_md_template", lambda: None)

    def _fake_run_setup(console) -> None:
        setup_called[0] = True

    monkeypatch.setattr("ubundiforge.cli.run_setup", _fake_run_setup)


def test_dry_run_skips_setup_and_missing_backend_checks(monkeypatch):
    setup_called = [False]
    _patch_prompt_only_dependencies(monkeypatch, setup_called=setup_called)

    result = runner.invoke(
        app,
        [
            "--dry-run",
            "--name",
            "ci-smoke",
            "--stack",
            "fastapi",
            "--description",
            "CI smoke test",
            "--no-docker",
            "--no-open",
            "--no-verify",
        ],
    )

    assert result.exit_code == 0
    assert setup_called[0] is False
    assert "CI smoke test" in result.stdout
    assert "<project>" in result.stdout
    assert "<stack>Python API (FastAPI)</stack>" in result.stdout
    assert "Use strict typing." in result.stdout
    assert "Approval mode: safe" in result.stdout
    assert "model: provider default" in result.stdout


def test_dry_run_agents_never_starts_provider_processes(monkeypatch):
    setup_called = [False]
    _patch_prompt_only_dependencies(monkeypatch, setup_called=setup_called)
    monkeypatch.setattr(
        "ubundiforge.orchestrator._get_plan",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("dry-run must not call a provider planner")
        ),
    )

    result = runner.invoke(
        app,
        [
            "--dry-run",
            "--agents",
            "--name",
            "preview-only",
            "--stack",
            "fastapi",
            "--description",
            "No provider calls",
            "--no-docker",
            "--no-open",
            "--no-verify",
        ],
    )

    assert result.exit_code == 0
    assert "no model calls made" in result.stdout


def test_unknown_provider_readiness_is_not_executable(monkeypatch, tmp_path):
    monkeypatch.setattr("ubundiforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("ubundiforge.cli.needs_setup", lambda: False)
    monkeypatch.setattr(
        "ubundiforge.cli.load_forge_config",
        lambda: {"projects_dir": str(tmp_path)},
    )
    monkeypatch.setattr(
        "ubundiforge.cli.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=False, ready=False),
            "antigravity": BackendStatus(installed=True, ready=None),
            "codex": BackendStatus(installed=False, ready=False),
        },
    )

    result = runner.invoke(
        app,
        [
            "--use",
            "antigravity",
            "--name",
            "auth-check-inconclusive",
            "--stack",
            "fastapi",
            "--description",
            "Must not run",
            "--no-open",
            "--no-verify",
        ],
    )

    assert result.exit_code == 1
    assert "could not confirm authentication" in result.stdout.lower()


def test_removed_gemini_override_points_to_antigravity():
    result = runner.invoke(
        app,
        [
            "--dry-run",
            "--use",
            "gemini",
            "--name",
            "migration-check",
            "--stack",
            "fastapi",
            "--description",
            "Must not route to a retired CLI",
        ],
    )

    assert result.exit_code == 1
    assert "gemini cli backend was removed" in result.stdout.lower()
    assert "--use antigravity" in " ".join(result.stdout.lower().split())


def test_export_skips_setup_and_writes_prompt(monkeypatch, tmp_path):
    setup_called = [False]
    _patch_prompt_only_dependencies(monkeypatch, setup_called=setup_called)
    export_path = tmp_path / "prompt.md"

    result = runner.invoke(
        app,
        [
            "--export",
            str(export_path),
            "--name",
            "atlas",
            "--stack",
            "nextjs",
            "--description",
            "A customer dashboard",
            "--no-docker",
            "--no-open",
            "--no-verify",
        ],
    )

    assert result.exit_code == 0
    assert setup_called[0] is False
    assert export_path.exists()
    assert "A customer dashboard" in export_path.read_text()
    assert "Prompt exported to" in result.stdout


def test_export_keeps_specialist_phase_routing_without_installed_backends(monkeypatch, tmp_path):
    setup_called = [False]
    _patch_prompt_only_dependencies(monkeypatch, setup_called=setup_called)
    export_path = tmp_path / "prompt.md"

    result = runner.invoke(
        app,
        [
            "--export",
            str(export_path),
            "--name",
            "studio",
            "--stack",
            "nextjs",
            "--description",
            "A branded client portal",
            "--no-docker",
            "--no-open",
            "--no-verify",
        ],
    )

    exported = export_path.read_text()

    assert result.exit_code == 0
    assert setup_called[0] is False
    assert export_path.exists()
    assert "=== Architecture & Core (claude) ===" in exported
    assert "=== Frontend & UI (antigravity) ===" in exported
    assert "=== Tests & Automation (codex) ===" in exported
    assert "=== Verify & Fix (claude) ===" in exported


def test_dry_run_integration_includes_auth_ci_and_extra_sections(monkeypatch):
    setup_called = [False]
    _patch_prompt_only_dependencies(monkeypatch, setup_called=setup_called)

    result = runner.invoke(
        app,
        [
            "--dry-run",
            "--use",
            "claude",
            "--name",
            "studio",
            "--stack",
            "nextjs",
            "--description",
            "A branded client portal",
            "--auth-provider",
            "clerk",
            "--ci",
            "--ci-template",
            "questionnaire",
            "--ci-actions",
            "lint,typecheck,unit-tests",
            "--extra",
            "Use Tailwind v4",
            "--no-docker",
            "--no-open",
            "--no-verify",
        ],
    )

    assert result.exit_code == 0
    assert setup_called[0] is False
    assert "Authentication to scaffold:" in result.stdout
    assert "CI GUIDANCE:" in result.stdout
    assert ".github/workflows/ci.yml" in result.stdout
    assert "Use Tailwind v4" in result.stdout
    assert "DEMO MODE" in result.stdout


def test_dry_run_loads_compiled_conventions_for_requested_stack(monkeypatch):
    setup_called = [False]
    _patch_prompt_only_dependencies(monkeypatch, setup_called=setup_called)
    seen_stacks: list[str | None] = []

    def _fake_load_conventions(stack=None):
        seen_stacks.append(stack)
        return (f"compiled conventions for {stack}", [])

    monkeypatch.setattr("ubundiforge.cli.load_conventions", _fake_load_conventions)

    result = runner.invoke(
        app,
        [
            "--dry-run",
            "--name",
            "bundle-smoke",
            "--stack",
            "fastapi",
            "--description",
            "Exercise stack-aware conventions",
            "--no-docker",
            "--no-open",
            "--no-verify",
        ],
    )

    assert result.exit_code == 0
    assert seen_stacks == ["fastapi"]
    assert "compiled conventions for fastapi" in result.stdout


def test_dry_run_reports_bundle_validation_errors(monkeypatch):
    setup_called = [False]
    _patch_prompt_only_dependencies(monkeypatch, setup_called=setup_called)
    monkeypatch.setattr(
        "ubundiforge.cli.load_conventions",
        lambda stack=None: (_ for _ in ()).throw(ConventionValidationError("broken bundle")),
    )

    result = runner.invoke(
        app,
        [
            "--dry-run",
            "--name",
            "bundle-smoke",
            "--stack",
            "fastapi",
            "--description",
            "Exercise stack-aware conventions",
            "--no-docker",
            "--no-open",
            "--no-verify",
        ],
    )

    assert result.exit_code == 1
    assert "broken bundle" in result.stdout


def test_mock_backends_cover_full_cli_flow_without_installed_ai_clis(monkeypatch, tmp_path):
    monkeypatch.setattr("ubundiforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("ubundiforge.cli.needs_setup", lambda: False)
    monkeypatch.setattr(
        "ubundiforge.cli.load_forge_config",
        lambda: {"projects_dir": str(tmp_path)},
    )
    monkeypatch.setattr(
        "ubundiforge.cli.load_conventions",
        lambda stack=None: ("Use strict typing.", []),
    )
    monkeypatch.setattr("ubundiforge.cli.load_claude_md_template", lambda: None)
    monkeypatch.setattr(
        "ubundiforge.cli.get_backend_statuses",
        lambda: {
            backend: BackendStatus(installed=True, ready=True)
            for backend in ("claude", "antigravity", "codex")
        },
    )
    monkeypatch.setattr("ubundiforge.router.check_backend_installed", lambda backend: True)

    phase_calls: list[str] = []

    def _write_phase_output(project_dir: Path, slug: str, backend: str, prompt: str) -> None:
        (project_dir / f"{slug}.txt").write_text(f"{backend}\n{prompt[:80]}\n")

    def _fake_run_ai(
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
        assert approval_mode == "safe"
        assert allow_unsafe is False
        phase_calls.append(label)
        project_dir.mkdir(parents=True, exist_ok=True)
        slug = label.lower().replace(" & ", "-").replace(" ", "-")
        (project_dir / f"{slug}.txt").write_text(f"{backend}\n{prompt[:80]}\n")
        return 0

    def _fake_run_ai_parallel(
        phases: list[dict],
        project_dir: Path,
        verbose: bool = False,
    ) -> list[tuple[str, int]]:
        results: list[tuple[str, int]] = []
        project_dir.mkdir(parents=True, exist_ok=True)
        for phase in phases:
            phase_calls.append(phase["label"])
            slug = phase["label"].lower().replace(" & ", "-").replace(" ", "-")
            _write_phase_output(project_dir, slug, phase["backend"], phase["prompt"])
            results.append((phase["label"], 0))
        return results

    monkeypatch.setattr("ubundiforge.cli.run_ai", _fake_run_ai)
    monkeypatch.setattr("ubundiforge.cli.run_ai_parallel", _fake_run_ai_parallel)
    monkeypatch.setattr("ubundiforge.cli.ensure_git_init", lambda project_dir: True)

    result = runner.invoke(
        app,
        [
            "--name",
            "mocked-flow",
            "--stack",
            "nextjs",
            "--description",
            "A mocked full scaffold run",
            "--no-docker",
            "--no-open",
            "--no-verify",
        ],
    )

    project_dir = tmp_path / "mocked-flow"

    assert result.exit_code == 0
    assert phase_calls == [
        "Architecture & Core",
        "Frontend & UI",
        "Tests & Automation",
        "Verify & Fix",
    ]
    assert project_dir.exists()
    assert (project_dir / "architecture-core.txt").exists()
    assert (project_dir / "frontend-ui.txt").exists()
    assert (project_dir / "tests-automation.txt").exists()
    assert (project_dir / "verify-fix.txt").exists()
    assert "Project Created" in result.stdout


def test_root_help_documents_safe_resume_contract():
    result = runner.invoke(app, ["--help"], env={"TERM": "dumb"})

    assert result.exit_code == 0
    assert "--resume" in result.stdout
    assert "completed phases" in result.stdout


def test_resume_preserves_completed_phases_and_finishes_failed_scaffold(monkeypatch, tmp_path):
    monkeypatch.setattr("ubundiforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("ubundiforge.cli.needs_setup", lambda: False)
    monkeypatch.setattr(
        "ubundiforge.cli.load_forge_config",
        lambda: {"projects_dir": str(tmp_path)},
    )
    monkeypatch.setattr(
        "ubundiforge.cli.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=True, ready=True),
            "antigravity": BackendStatus(installed=False, ready=False),
            "codex": BackendStatus(installed=False, ready=False),
        },
    )
    monkeypatch.setattr("ubundiforge.router.check_backend_installed", lambda backend: True)
    monkeypatch.setattr(
        "ubundiforge.cli.load_conventions",
        lambda stack=None: ("Use strict typing.", []),
    )
    monkeypatch.setattr("ubundiforge.cli.load_claude_md_template", lambda: None)
    monkeypatch.setattr("ubundiforge.cli.ensure_git_init", lambda project_dir: True)
    monkeypatch.setattr("ubundiforge.cli.append_quality_signal", lambda **kwargs: None)
    monkeypatch.setattr("ubundiforge.cli.append_scaffold_log", lambda *args: None)
    monkeypatch.setattr("ubundiforge.cli.record_preferences", lambda answers: None)
    monkeypatch.setattr("ubundiforge.cli.run_post_scaffold_hook", lambda *args: None)
    monkeypatch.setattr("ubundiforge.cli.write_card", lambda *args, **kwargs: None)
    monkeypatch.setattr("ubundiforge.cli.inject_badge_into_readme", lambda project_dir: None)

    calls: list[str] = []
    failed_once = {"value": False}

    def _fake_run_ai(
        backend,
        prompt,
        project_dir,
        model=None,
        verbose=False,
        label="",
        phase_context=None,
        approval_mode="safe",
        allow_unsafe=False,
    ):
        calls.append(label)
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / f"{label.lower().replace(' ', '-')}.txt").write_text("partial")
        if label == "Tests & Automation" and not failed_once["value"]:
            failed_once["value"] = True
            return 9
        return 0

    monkeypatch.setattr("ubundiforge.cli.run_ai", _fake_run_ai)
    command = [
        "--use",
        "claude",
        "--name",
        "resumable",
        "--stack",
        "fastapi",
        "--description",
        "A resumable API",
        "--no-docker",
        "--no-open",
        "--no-verify",
    ]

    first = runner.invoke(app, command)
    assert first.exit_code == 9
    assert calls == ["Architecture & Core", "Tests & Automation"]
    assert "Partial project output" in first.stdout

    second = runner.invoke(app, [*command, "--resume"])
    assert second.exit_code == 0
    assert calls == [
        "Architecture & Core",
        "Tests & Automation",
        "Tests & Automation",
        "Verify & Fix",
    ]
    assert "Preserved completed phase: Architecture & Core" in second.stdout

    progress = json.loads((tmp_path / "resumable" / ".forge" / "progress.json").read_text())
    assert progress["status"] == "completed"
    assert progress["resume_count"] == 1
    assert [phase["attempts"] for phase in progress["phases"]] == [1, 2, 1]


def test_first_run_setup_prompts_before_interactive_scaffold(monkeypatch):
    monkeypatch.setattr("ubundiforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("ubundiforge.cli.needs_setup", lambda: True)

    setup_calls = {"count": 0}
    answer_calls = {"count": 0}

    def _fake_run_setup(console) -> dict:
        setup_calls["count"] += 1
        return {}

    monkeypatch.setattr("ubundiforge.cli.run_setup", _fake_run_setup)
    monkeypatch.setattr(
        "ubundiforge.cli.prompt_select",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: "exit"),
    )

    def _unexpected_collect_answers(*args, **kwargs):
        answer_calls["count"] += 1
        raise AssertionError("collect_answers should not run when the user exits after setup")

    monkeypatch.setattr("ubundiforge.cli.collect_answers", _unexpected_collect_answers)

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert setup_calls["count"] == 1
    assert answer_calls["count"] == 0
    assert (
        "Forge is configured and ready." in result.stdout
        or "Forge is configured, but no backends are ready yet." in result.stdout
    )


def test_first_run_setup_can_be_repeated_before_scaffolding(monkeypatch):
    monkeypatch.setattr("ubundiforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("ubundiforge.cli.needs_setup", lambda: True)

    setup_calls = {"count": 0}
    actions = iter(["setup", "exit"])

    def _fake_run_setup(console) -> dict:
        setup_calls["count"] += 1
        return {}

    monkeypatch.setattr("ubundiforge.cli.run_setup", _fake_run_setup)
    monkeypatch.setattr(
        "ubundiforge.cli.prompt_select",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: next(actions)),
    )
    monkeypatch.setattr(
        "ubundiforge.cli.collect_answers",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("collect_answers should not run when the user exits")
        ),
    )

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert setup_calls["count"] == 2


def test_first_run_with_explicit_scaffold_flags_skips_post_setup_prompt(monkeypatch, tmp_path):
    monkeypatch.setattr("ubundiforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("ubundiforge.cli.needs_setup", lambda: True)
    monkeypatch.setattr(
        "ubundiforge.cli.load_forge_config",
        lambda: {"projects_dir": str(tmp_path)},
    )
    monkeypatch.setattr(
        "ubundiforge.cli.load_conventions",
        lambda stack=None: ("Use strict typing.", []),
    )
    monkeypatch.setattr("ubundiforge.cli.load_claude_md_template", lambda: None)
    monkeypatch.setattr(
        "ubundiforge.cli.get_backend_statuses",
        lambda: {
            backend: BackendStatus(installed=True, ready=True)
            for backend in ("claude", "antigravity", "codex")
        },
    )
    monkeypatch.setattr("ubundiforge.router.check_backend_installed", lambda backend: True)

    setup_calls = {"count": 0}
    prompt_calls = {"count": 0}

    def _fake_run_setup(console) -> dict:
        setup_calls["count"] += 1
        return {}

    monkeypatch.setattr("ubundiforge.cli.run_setup", _fake_run_setup)

    def _unexpected_post_setup_prompt(*args, **kwargs):
        prompt_calls["count"] += 1
        raise AssertionError("post-setup prompt should be skipped for explicit scaffold runs")

    monkeypatch.setattr("ubundiforge.cli.prompt_select", _unexpected_post_setup_prompt)

    def _fake_run_ai(backend, prompt, project_dir, *args, **kwargs):
        project_dir.mkdir(parents=True, exist_ok=True)
        return 0

    def _fake_run_ai_parallel(phases, project_dir, verbose=False):
        project_dir.mkdir(parents=True, exist_ok=True)
        return []

    monkeypatch.setattr("ubundiforge.cli.run_ai", _fake_run_ai)
    monkeypatch.setattr("ubundiforge.cli.run_ai_parallel", _fake_run_ai_parallel)
    monkeypatch.setattr("ubundiforge.cli.ensure_git_init", lambda project_dir: True)

    result = runner.invoke(
        app,
        [
            "--name",
            "guided-first-run",
            "--stack",
            "fastapi",
            "--description",
            "A first-run explicit scaffold",
            "--no-docker",
            "--no-open",
            "--no-verify",
        ],
    )

    assert result.exit_code == 0
    assert setup_calls["count"] == 1
    assert prompt_calls["count"] == 0
    assert "Project Created" in result.stdout


def test_replay_without_snapshot_loads_compiled_conventions_for_manifest_stack(
    monkeypatch,
    tmp_path,
):
    project_dir = tmp_path / "atlas"
    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True)
    (forge_dir / "scaffold.json").write_text(
        json.dumps(
            {
                "name": "atlas",
                "stack": "fastapi",
                "description": "Replay me",
                "routing": [{"phase": "architecture", "backend": "claude"}],
            }
        )
    )

    seen_stacks: list[str | None] = []

    def _fake_load_bundled_conventions(stack=None):
        seen_stacks.append(stack)
        return (f"compiled conventions for {stack}", [])

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(
        "ubundiforge.cli.load_bundled_conventions",
        _fake_load_bundled_conventions,
    )
    monkeypatch.setattr(
        "ubundiforge.cli.load_conventions",
        lambda stack=None: (_ for _ in ()).throw(AssertionError("should use bundled replay path")),
    )
    monkeypatch.setattr("ubundiforge.router.check_backend_installed", lambda backend: True)

    result = runner.invoke(app, ["replay", "--dry-run"])
    output = " ".join(result.stdout.split())

    assert result.exit_code == 0
    assert seen_stacks == ["fastapi"]
    assert "compiled conventions for fastapi" in output
    assert "Using current bundled conventions for stack 'fastapi'." in output


def test_replay_prefers_snapshot_over_compiled_bundle(monkeypatch, tmp_path):
    project_dir = tmp_path / "atlas"
    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True)
    (forge_dir / "scaffold.json").write_text(
        json.dumps(
            {
                "name": "atlas",
                "stack": "fastapi",
                "description": "Replay me",
                "routing": [{"phase": "architecture", "backend": "claude"}],
            }
        )
    )
    (forge_dir / "conventions-snapshot.md").write_text("snapshot conventions")

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(
        "ubundiforge.cli.load_conventions",
        lambda stack=None: (_ for _ in ()).throw(AssertionError("should not load current bundle")),
    )
    monkeypatch.setattr("ubundiforge.router.check_backend_installed", lambda backend: True)

    result = runner.invoke(app, ["replay", "--dry-run"])

    assert result.exit_code == 0
    assert "snapshot conventions" in result.stdout


def test_replay_reports_bundle_validation_errors(monkeypatch, tmp_path):
    project_dir = tmp_path / "atlas"
    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True)
    (forge_dir / "scaffold.json").write_text(
        json.dumps(
            {
                "name": "atlas",
                "stack": "fastapi",
                "description": "Replay me",
                "routing": [{"phase": "architecture", "backend": "claude"}],
            }
        )
    )

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(
        "ubundiforge.cli.load_bundled_conventions",
        lambda stack=None: (_ for _ in ()).throw(ConventionValidationError("unknown stack")),
    )
    monkeypatch.setattr("ubundiforge.router.check_backend_installed", lambda backend: True)

    result = runner.invoke(app, ["replay", "--dry-run"])

    assert result.exit_code == 1
    assert "unknown stack" in result.stdout


def test_replay_unknown_manifest_stack_falls_back_to_default_bundle(monkeypatch, tmp_path):
    project_dir = tmp_path / "atlas"
    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True)
    (forge_dir / "scaffold.json").write_text(
        json.dumps(
            {
                "name": "atlas",
                "stack": "not-a-real-stack",
                "description": "Replay me",
                "routing": [{"phase": "architecture", "backend": "claude"}],
            }
        )
    )

    seen_stacks: list[str | None] = []

    def _fake_load_bundled_conventions(stack=None):
        seen_stacks.append(stack)
        if stack == "not-a-real-stack":
            raise ConventionValidationError("Unknown convention record: stacks/not-a-real-stack")
        return ("compiled default conventions", [])

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(
        "ubundiforge.cli.load_bundled_conventions",
        _fake_load_bundled_conventions,
    )
    monkeypatch.setattr("ubundiforge.router.check_backend_installed", lambda backend: True)

    result = runner.invoke(app, ["replay", "--dry-run"])
    output = " ".join(result.stdout.lower().split())

    assert result.exit_code == 0
    assert seen_stacks == ["not-a-real-stack", None]
    assert "compiled default conventions" in result.stdout
    assert "falling back to current bundled conventions" in output
    assert "no conventions snapshot found. using current conventions." in output


def test_resolve_project_dir_allows_rename(monkeypatch, tmp_path):
    from ubundiforge.cli import _resolve_project_dir

    target = tmp_path / "existing"
    target.mkdir()
    (target / "keep.txt").write_text("keep")

    answers = {"name": "existing"}
    actions = iter(["rename"])

    monkeypatch.setattr(
        "ubundiforge.cli.prompt_select",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: next(actions)),
    )
    monkeypatch.setattr(
        "ubundiforge.cli.prompt_text",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: "renamed-project"),
    )

    project_dir = _resolve_project_dir(tmp_path, answers)

    assert answers["name"] == "renamed-project"
    assert project_dir == tmp_path / "renamed-project"
    assert (target / "keep.txt").exists()


def test_run_setup_does_not_create_legacy_conventions_file(monkeypatch, tmp_path):
    console = Console(record=True, width=120)
    forge_dir = tmp_path / ".forge"
    config_path = forge_dir / "config.json"
    conventions_path = forge_dir / "conventions.md"

    prompt_select_answers = iter(["_provider_default"])

    monkeypatch.setattr("ubundiforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("ubundiforge.setup.CONFIG_PATH", config_path)
    monkeypatch.setattr("ubundiforge.setup.CONVENTIONS_PATH", conventions_path)
    monkeypatch.setattr(
        "ubundiforge.setup.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=True, ready=True),
            "antigravity": BackendStatus(installed=False, ready=False),
            "codex": BackendStatus(installed=False, ready=False),
        },
    )
    monkeypatch.setattr("ubundiforge.setup.load_forge_config", lambda: {})
    monkeypatch.setattr("ubundiforge.setup._check_editor_installed", lambda *_: (False, False))
    monkeypatch.setattr(
        "ubundiforge.setup.prompt_select",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: next(prompt_select_answers)),
    )
    monkeypatch.setattr(
        "ubundiforge.setup.prompt_text",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: ""),
    )
    monkeypatch.setattr("ubundiforge.media_assets.list_collections", lambda: [])
    monkeypatch.setattr("ubundiforge.media_assets.MEDIA_DIR", tmp_path / "media")
    monkeypatch.setattr(
        "ubundiforge.setup.shutil.which",
        lambda cmd: None if cmd in {"git", "docker"} else f"/usr/bin/{cmd}",
    )

    config = run_setup(console)
    output = console.export_text()

    assert config["available_backends"] == ["claude"]
    assert config["backend_models"] == {}
    assert not conventions_path.exists()
    assert "bundled conventions" in output.lower()
    assert "bundled source tree" in output.lower()
    assert "forge admin conventions" in output


def test_setup_missing_providers_shows_official_install_auth_recheck_flow(monkeypatch):
    console = Console(record=True, width=160)
    monkeypatch.setattr(
        "ubundiforge.setup.get_backend_statuses",
        lambda: {
            backend: BackendStatus(installed=False, ready=False)
            for backend in ("claude", "antigravity", "codex")
        },
    )

    with pytest.raises(SystemExit):
        run_setup(console)

    output = console.export_text()
    assert "https://code.claude.com/docs/en/setup" in output
    assert "https://antigravity.google/docs/cli-install" in output
    assert "https://github.com/openai/codex" in output
    assert "forge doctor" in output


def test_admin_conventions_validate_passes() -> None:
    result = runner.invoke(app, ["admin", "conventions", "--validate"])

    assert result.exit_code == 0
    assert "Validation passed" in result.stdout


def test_user_convention_profile_init_select_and_inspect(monkeypatch, tmp_path):
    forge_dir = tmp_path / ".forge"
    profiles_dir = forge_dir / "profiles"
    config_path = forge_dir / "config.json"
    monkeypatch.setattr("ubundiforge.convention_profiles.PROFILES_DIR", profiles_dir)
    monkeypatch.setattr("ubundiforge.conventions.PROFILES_DIR", profiles_dir)
    monkeypatch.setattr("ubundiforge.conventions.CONVENTIONS_PATH", forge_dir / "conventions.md")
    monkeypatch.setattr(
        "ubundiforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / "project" / ".forge" / "conventions.md",
    )
    monkeypatch.setattr("ubundiforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("ubundiforge.setup.CONFIG_PATH", config_path)

    initialized = runner.invoke(app, ["conventions", "init", "team"])
    selected = runner.invoke(app, ["conventions", "select", "team"])
    inspected = runner.invoke(
        app,
        ["conventions", "inspect", "--stack", "fastapi", "--json"],
    )

    assert initialized.exit_code == 0
    assert selected.exit_code == 0
    assert inspected.exit_code == 0
    assert json.loads(config_path.read_text())["conventions_profile"] == "team"
    report = json.loads(inspected.stdout)
    assert report["profile"] == "team"
    assert any(source["source_id"] == "profile:team" for source in report["sources"])


def test_admin_conventions_preview_stack() -> None:
    result = runner.invoke(app, ["admin", "conventions", "--preview-stack", "fastapi"])

    assert result.exit_code == 0
    assert "Compiled bundle: fastapi" in result.stdout


def test_admin_conventions_history_degrades_gracefully(monkeypatch) -> None:
    from ubundiforge.convention_history import GitHistoryResult

    monkeypatch.setattr(
        "ubundiforge.cli.load_history",
        lambda root, target: GitHistoryResult(
            target=target,
            available=False,
            entries=(),
            message="Git history is unavailable.",
        ),
    )

    result = runner.invoke(app, ["admin", "conventions", "--history", "fastapi"])

    assert result.exit_code == 0
    assert "Git history is unavailable." in result.stdout


def test_admin_conventions_history_allows_top_level_scope_targets(monkeypatch) -> None:
    from ubundiforge.convention_history import GitHistoryResult

    seen_targets: list[str] = []

    def _fake_load_history(root, target):
        seen_targets.append(target)
        return GitHistoryResult(
            target=target,
            available=True,
            entries=("abc123 Update global conventions",),
        )

    monkeypatch.setattr("ubundiforge.cli.load_history", _fake_load_history)

    result = runner.invoke(app, ["admin", "conventions", "--history", "global"])

    assert result.exit_code == 0
    assert seen_targets == ["global"]
    assert "abc123 Update global conventions" in result.stdout


def test_admin_conventions_open_prints_repo_markdown_path() -> None:
    result = runner.invoke(app, ["admin", "conventions", "--open", "global/shared.md"])

    assert result.exit_code == 0
    assert "shared.md" in result.stdout


def test_admin_conventions_defaults_to_interactive_menu(monkeypatch) -> None:
    actions = iter(["validate"])

    monkeypatch.setattr(
        "ubundiforge.cli.prompt_select",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: next(actions)),
    )

    result = runner.invoke(app, ["admin", "conventions"])

    assert result.exit_code == 0
    assert "Validation passed" in result.stdout
