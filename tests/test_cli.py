"""Tests for CLI execution paths."""

import json
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from rich.console import Console
from typer.testing import CliRunner

from projectforge import __version__
from projectforge.cli import (
    _format_duration,
    _provider_commitment_lines,
    _render_loaded_context,
    app,
)
from projectforge.config import BackendStatus
from projectforge.convention_models import ConventionContribution, ConventionValidationError
from projectforge.setup import run_setup

runner = CliRunner()


def test_version_output_uses_public_project_name():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"projectforge {__version__}"


def test_scaffold_context_hides_hashes_unless_verbose(monkeypatch):
    output = StringIO()
    monkeypatch.setattr(
        "projectforge.cli.console",
        Console(file=output, force_terminal=False, color_system=None, width=120),
    )
    source = ConventionContribution(
        source_id="bundled:global/shared",
        display_path="bundled:global/shared.md",
        sha256="sha256:secret-detail",
    )

    _render_loaded_context(
        {"claude"},
        {},
        model_override=None,
        approval_mode="safe",
        conventions="x" * 9800,
        claude_md_loaded=False,
        design_template_label=None,
        convention_sources=(source,),
        conventions_profile="team",
        project_brief_added=True,
        project_context_files=2,
    )

    assert "Convention profile: team" in output.getvalue()
    assert "Project brief: added; nearby context: 2 selected" in output.getvalue()
    assert "Conventions: 1 source, 9,800 chars (hashes recorded)" in output.getvalue()
    assert "sha256:secret-detail" not in output.getvalue()

    output.seek(0)
    output.truncate(0)
    _render_loaded_context(
        {"claude"},
        {},
        model_override=None,
        approval_mode="safe",
        conventions="x" * 9800,
        claude_md_loaded=False,
        design_template_label=None,
        convention_sources=(source,),
        verbose=True,
    )

    assert "sha256:secret-detail" in output.getvalue()


def test_preflight_commitment_helpers_quantify_time_calls_and_cost():
    lines = _provider_commitment_lines(
        [("architecture", "claude"), ("tests", "codex"), ("verify", "claude")],
        {"architecture"},
        agents=True,
    )
    output = "\n".join(line.plain for line in lines)

    assert _format_duration(400) == "6m 40s"
    assert "claude usage: typically 4-8" in output
    assert "codex usage: typically 4-8" in output
    assert "$1-$20+" in output


def test_stats_empty_shows_first_scaffold_guidance():
    result = runner.invoke(app, ["stats"])

    assert result.exit_code == 0
    assert "No scaffolds recorded yet" in result.stdout
    assert "0% success rate" not in result.stdout


def test_stats_hides_unreadable_history_detail(monkeypatch, tmp_path):
    scaffold_path = tmp_path / "scaffold.log"
    scaffold_path.write_text("{}\n")
    monkeypatch.setattr("projectforge.cli.SCAFFOLD_LOG_PATH", scaffold_path)
    original_read_text = Path.read_text

    def unreadable(path: Path, *args, **kwargs):
        if path == scaffold_path:
            raise OSError("private filesystem detail")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)

    result = runner.invoke(app, ["stats"])

    assert result.exit_code == 1
    assert "could not read the saved scaffold history" in result.stdout
    assert "private filesystem detail" not in result.stdout


def test_stats_hides_history_repair_failure_detail(monkeypatch):
    monkeypatch.setattr(
        "projectforge.history.repair_history",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("private filesystem detail")),
    )

    result = runner.invoke(app, ["stats", "--repair"])

    assert result.exit_code == 1
    assert "could not repair the saved scaffold history" in result.stdout
    assert "private filesystem detail" not in result.stdout


def test_stats_repair_quarantines_synthetic_history(monkeypatch, tmp_path):
    scaffold_path = tmp_path / "scaffold.log"
    quality_path = tmp_path / "quality.jsonl"
    scaffold_path.write_text(
        json.dumps(
            {
                "name": "mocked-flow",
                "directory": "mocked-flow",
                "stack": "fastapi",
                "timestamp": "2026-07-18T12:00:02+00:00",
            }
        )
        + "\n"
    )
    quality_path.write_text(
        json.dumps(
            {
                "stack": "fastapi",
                "phase": "architecture",
                "timestamp": "2026-07-18T12:00:00+00:00",
                "lint_clean": False,
                "tests_passed": False,
                "typecheck_clean": False,
                "health_ok": False,
                "built": False,
            }
        )
        + "\n"
    )
    monkeypatch.setattr("projectforge.cli.SCAFFOLD_LOG_PATH", scaffold_path)
    monkeypatch.setattr("projectforge.quality.QUALITY_LOG_PATH", quality_path)

    result = runner.invoke(app, ["stats", "--repair"])

    assert result.exit_code == 0
    assert "Quarantined 1 scaffold and 1 quality entries" in result.stdout
    assert "No scaffolds recorded yet" in result.stdout
    assert list((tmp_path / "quarantine").glob("*/scaffold.log"))
    assert list((tmp_path / "quarantine").glob("*/quality.jsonl"))


def test_doctor_json_has_deterministic_exit_semantics(monkeypatch):
    report = {
        "schema_version": 1,
        "projectforge_version": __version__,
        "status": "attention",
        "config": {"status": "missing"},
        "providers": {},
    }
    monkeypatch.setattr("projectforge.cli.build_doctor_report", lambda: report)

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
                "check": {
                    "command": "claude auth status",
                    "observed": "Authentication is required.",
                },
                "repair": "Run claude auth login, then rerun forge doctor.",
            }
        },
    }
    monkeypatch.setattr("projectforge.cli.build_doctor_report", lambda: report)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "Editors: none found" in result.stdout
    assert "projectforge --setup" in result.stdout
    assert "model: provider default" in result.stdout
    assert "check: claude auth status" in result.stdout
    assert "observed: Authentication is required." in result.stdout
    assert "next: Run claude auth login" in result.stdout


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
    assert "normal protections" in result.stdout.lower()
    assert "isolated environment" in result.stdout.lower()


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
    monkeypatch.setattr("projectforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("projectforge.cli.needs_setup", lambda: True)
    monkeypatch.setattr("projectforge.cli.load_forge_config", lambda: {})
    monkeypatch.setattr(
        "projectforge.cli.get_backend_statuses",
        lambda: {
            backend: BackendStatus(installed=False, ready=False)
            for backend in ("claude", "antigravity", "codex")
        },
    )
    monkeypatch.setattr("projectforge.router.check_backend_installed", lambda backend: False)
    monkeypatch.setattr(
        "projectforge.cli.load_conventions",
        lambda stack=None: ("Use strict typing.", []),
    )
    monkeypatch.setattr("projectforge.cli.load_claude_md_template", lambda: None)

    def _fake_run_setup(console) -> None:
        setup_called[0] = True

    monkeypatch.setattr("projectforge.cli.run_setup", _fake_run_setup)


def _patch_live_scaffold_dependencies(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("projectforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("projectforge.cli.needs_setup", lambda: False)
    monkeypatch.setattr(
        "projectforge.cli.load_forge_config",
        lambda: {"projects_dir": str(tmp_path)},
    )
    monkeypatch.setattr(
        "projectforge.cli.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=True, ready=True),
            "antigravity": BackendStatus(installed=False, ready=False),
            "codex": BackendStatus(installed=False, ready=False),
        },
    )
    monkeypatch.setattr(
        "projectforge.cli.load_conventions",
        lambda stack=None: ("Use strict typing.", []),
    )
    monkeypatch.setattr("projectforge.cli.load_claude_md_template", lambda: None)
    monkeypatch.setattr("projectforge.cli.ensure_git_init", lambda project_dir: True)
    monkeypatch.setattr(
        "projectforge.cli.run_ai",
        lambda backend, prompt, project_dir, **kwargs: (
            project_dir.mkdir(parents=True, exist_ok=True) or 0
        ),
    )
    monkeypatch.setattr("projectforge.cli.append_quality_signal", lambda **kwargs: None)
    monkeypatch.setattr("projectforge.cli.append_scaffold_log", lambda *args, **kwargs: None)
    monkeypatch.setattr("projectforge.cli.record_preferences", lambda answers: None)
    monkeypatch.setattr("projectforge.cli.run_post_scaffold_hook", lambda *args: None)
    monkeypatch.setattr("projectforge.cli.write_card", lambda *args, **kwargs: None)
    monkeypatch.setattr("projectforge.cli.inject_badge_into_readme", lambda project_dir: None)


def _live_scaffold_command(name: str) -> list[str]:
    return [
        "--use",
        "claude",
        "--name",
        name,
        "--stack",
        "python-cli",
        "--description",
        "A persistence error test",
        "--no-docker",
        "--no-open",
        "--no-verify",
    ]


def test_scaffold_record_write_failure_has_safe_recovery(monkeypatch, tmp_path):
    _patch_live_scaffold_dependencies(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "projectforge.cli.write_scaffold_manifest",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("private filesystem detail")),
    )

    result = runner.invoke(app, _live_scaffold_command("record-failure"))

    assert result.exit_code == 1
    assert "could not save the scaffold record" in result.stdout
    assert "private filesystem detail" not in result.stdout


def test_optional_evidence_write_failure_preserves_project(monkeypatch, tmp_path):
    _patch_live_scaffold_dependencies(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "projectforge.cli.append_scaffold_log",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("private filesystem detail")),
    )

    result = runner.invoke(app, _live_scaffold_command("evidence-failure"))

    assert result.exit_code == 0
    assert "could not save some local history or verification files" in " ".join(
        result.stdout.split()
    )
    assert "private filesystem detail" not in result.stdout


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
        "projectforge.orchestrator._get_plan",
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
    monkeypatch.setattr("projectforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("projectforge.cli.needs_setup", lambda: False)
    monkeypatch.setattr(
        "projectforge.cli.load_forge_config",
        lambda: {"projects_dir": str(tmp_path)},
    )
    monkeypatch.setattr(
        "projectforge.cli.get_backend_statuses",
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
    assert "could not confirm that a selected ai tool is ready" in result.stdout.lower()


def test_removed_ai_tool_override_points_to_current_help():
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
    output = " ".join(result.stdout.lower().split())
    assert "ai tool option is no longer supported" in output
    assert "forge --help" in output
    assert "gemini" not in output


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


@pytest.mark.parametrize(
    ("extra_args", "expected_message"),
    [
        (["--stack", "unknown"], "That stack is not available"),
        (["--auth-provider", "unknown"], "authentication option is not available"),
        (
            ["--stack", "fastapi", "--auth-provider", "clerk"],
            "does not support an authentication option",
        ),
        (["--design-template", "unknown"], "design template is not available"),
        (
            ["--stack", "fastapi", "--design-template", "default-design-guide"],
            "does not support a design template",
        ),
        (["--ci-template", "unknown"], "CI template is not available"),
        (["--ci-actions", "unknown"], "CI checks do not work with this stack"),
    ],
)
def test_non_interactive_option_validation_keeps_actionable_errors(
    monkeypatch,
    extra_args,
    expected_message,
):
    setup_called = [False]
    _patch_prompt_only_dependencies(monkeypatch, setup_called=setup_called)
    command = [
        "--dry-run",
        "--name",
        "studio",
        "--stack",
        "nextjs",
        "--description",
        "A branded client portal",
        "--no-open",
        "--no-verify",
        *extra_args,
    ]

    result = runner.invoke(app, command)

    assert result.exit_code == 1
    assert expected_message in result.stdout


def test_dry_run_loads_compiled_conventions_for_requested_stack(monkeypatch):
    setup_called = [False]
    _patch_prompt_only_dependencies(monkeypatch, setup_called=setup_called)
    seen_stacks: list[str | None] = []

    def _fake_load_conventions(stack=None):
        seen_stacks.append(stack)
        return (f"compiled conventions for {stack}", [])

    monkeypatch.setattr("projectforge.cli.load_conventions", _fake_load_conventions)

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
        "projectforge.cli.load_conventions",
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
    assert "could not load the active conventions" in result.stdout
    assert "broken bundle" not in result.stdout


def test_mock_backends_cover_full_cli_flow_without_installed_ai_clis(monkeypatch, tmp_path):
    monkeypatch.setattr("projectforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("projectforge.cli.needs_setup", lambda: False)
    monkeypatch.setattr(
        "projectforge.cli.load_forge_config",
        lambda: {"projects_dir": str(tmp_path)},
    )
    monkeypatch.setattr(
        "projectforge.cli.load_conventions",
        lambda stack=None: ("Use strict typing.", []),
    )
    monkeypatch.setattr("projectforge.cli.load_claude_md_template", lambda: None)
    monkeypatch.setattr(
        "projectforge.cli.get_backend_statuses",
        lambda: {
            backend: BackendStatus(installed=True, ready=True)
            for backend in ("claude", "antigravity", "codex")
        },
    )
    monkeypatch.setattr("projectforge.router.check_backend_installed", lambda backend: True)

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

    monkeypatch.setattr("projectforge.cli.run_ai", _fake_run_ai)
    monkeypatch.setattr("projectforge.cli.run_ai_parallel", _fake_run_ai_parallel)
    monkeypatch.setattr("projectforge.cli.ensure_git_init", lambda project_dir: True)

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
    monkeypatch.setattr("projectforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("projectforge.cli.needs_setup", lambda: False)
    monkeypatch.setattr(
        "projectforge.cli.load_forge_config",
        lambda: {"projects_dir": str(tmp_path)},
    )
    monkeypatch.setattr(
        "projectforge.cli.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=True, ready=True),
            "antigravity": BackendStatus(installed=False, ready=False),
            "codex": BackendStatus(installed=False, ready=False),
        },
    )
    monkeypatch.setattr("projectforge.router.check_backend_installed", lambda backend: True)
    monkeypatch.setattr(
        "projectforge.cli.load_conventions",
        lambda stack=None: ("Use strict typing.", []),
    )
    monkeypatch.setattr("projectforge.cli.load_claude_md_template", lambda: None)
    monkeypatch.setattr("projectforge.cli.ensure_git_init", lambda project_dir: True)
    monkeypatch.setattr("projectforge.cli.append_quality_signal", lambda **kwargs: None)
    monkeypatch.setattr("projectforge.cli.append_scaffold_log", lambda *args, **kwargs: None)
    monkeypatch.setattr("projectforge.cli.record_preferences", lambda answers: None)
    monkeypatch.setattr("projectforge.cli.run_post_scaffold_hook", lambda *args: None)
    monkeypatch.setattr("projectforge.cli.write_card", lambda *args, **kwargs: None)
    monkeypatch.setattr("projectforge.cli.inject_badge_into_readme", lambda project_dir: None)

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

    monkeypatch.setattr("projectforge.cli.run_ai", _fake_run_ai)
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
    assert "completed work is safe" in first.stdout
    assert "exit 9" not in first.stdout
    assert "claude" not in first.stdout.lower().split("project generation stopped during", 1)[-1]

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
    monkeypatch.setattr("projectforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("projectforge.cli.needs_setup", lambda: True)

    setup_calls = {"count": 0}
    answer_calls = {"count": 0}

    def _fake_run_setup(console) -> dict:
        setup_calls["count"] += 1
        return {}

    monkeypatch.setattr("projectforge.cli.run_setup", _fake_run_setup)
    monkeypatch.setattr(
        "projectforge.cli.prompt_select",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: "exit"),
    )

    def _unexpected_collect_answers(*args, **kwargs):
        answer_calls["count"] += 1
        raise AssertionError("collect_answers should not run when the user exits after setup")

    monkeypatch.setattr("projectforge.cli.collect_answers", _unexpected_collect_answers)

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert setup_calls["count"] == 1
    assert answer_calls["count"] == 0
    assert (
        "Forge is configured and ready." in result.stdout
        or "Forge is configured, but no backends are ready yet." in result.stdout
    )


def test_first_run_setup_can_be_repeated_before_scaffolding(monkeypatch):
    monkeypatch.setattr("projectforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("projectforge.cli.needs_setup", lambda: True)

    setup_calls = {"count": 0}
    actions = iter(["setup", "exit"])

    def _fake_run_setup(console) -> dict:
        setup_calls["count"] += 1
        return {}

    monkeypatch.setattr("projectforge.cli.run_setup", _fake_run_setup)
    monkeypatch.setattr(
        "projectforge.cli.prompt_select",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: next(actions)),
    )
    monkeypatch.setattr(
        "projectforge.cli.collect_answers",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("collect_answers should not run when the user exits")
        ),
    )

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert setup_calls["count"] == 2


def test_first_run_with_explicit_scaffold_flags_skips_post_setup_prompt(monkeypatch, tmp_path):
    monkeypatch.setattr("projectforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("projectforge.cli.needs_setup", lambda: True)
    monkeypatch.setattr(
        "projectforge.cli.load_forge_config",
        lambda: {"projects_dir": str(tmp_path)},
    )
    monkeypatch.setattr(
        "projectforge.cli.load_conventions",
        lambda stack=None: ("Use strict typing.", []),
    )
    monkeypatch.setattr("projectforge.cli.load_claude_md_template", lambda: None)
    monkeypatch.setattr(
        "projectforge.cli.get_backend_statuses",
        lambda: {
            backend: BackendStatus(installed=True, ready=True)
            for backend in ("claude", "antigravity", "codex")
        },
    )
    monkeypatch.setattr("projectforge.router.check_backend_installed", lambda backend: True)

    setup_calls = {"count": 0}
    prompt_calls = {"count": 0}

    def _fake_run_setup(console) -> dict:
        setup_calls["count"] += 1
        return {}

    monkeypatch.setattr("projectforge.cli.run_setup", _fake_run_setup)

    def _unexpected_post_setup_prompt(*args, **kwargs):
        prompt_calls["count"] += 1
        raise AssertionError("post-setup prompt should be skipped for explicit scaffold runs")

    monkeypatch.setattr("projectforge.cli.prompt_select", _unexpected_post_setup_prompt)

    def _fake_run_ai(backend, prompt, project_dir, *args, **kwargs):
        project_dir.mkdir(parents=True, exist_ok=True)
        return 0

    def _fake_run_ai_parallel(phases, project_dir, verbose=False):
        project_dir.mkdir(parents=True, exist_ok=True)
        return []

    monkeypatch.setattr("projectforge.cli.run_ai", _fake_run_ai)
    monkeypatch.setattr("projectforge.cli.run_ai_parallel", _fake_run_ai_parallel)
    monkeypatch.setattr("projectforge.cli.ensure_git_init", lambda project_dir: True)

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
        "projectforge.cli.load_bundled_conventions",
        _fake_load_bundled_conventions,
    )
    monkeypatch.setattr(
        "projectforge.cli.load_conventions",
        lambda stack=None: (_ for _ in ()).throw(AssertionError("should use bundled replay path")),
    )
    monkeypatch.setattr("projectforge.router.check_backend_installed", lambda backend: True)

    result = runner.invoke(app, ["replay", "--dry-run"])
    output = " ".join(result.stdout.split())

    assert result.exit_code == 0
    assert seen_stacks == ["fastapi"]
    assert "compiled conventions for fastapi" in output
    assert "Forge will use current conventions, so replay results may differ." in output


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
        "projectforge.cli.load_conventions",
        lambda stack=None: (_ for _ in ()).throw(AssertionError("should not load current bundle")),
    )
    monkeypatch.setattr("projectforge.router.check_backend_installed", lambda backend: True)

    result = runner.invoke(app, ["replay", "--dry-run"])

    assert result.exit_code == 0
    assert "snapshot conventions" in result.stdout


def test_replay_restores_saved_project_brief_and_selected_context(monkeypatch, tmp_path):
    project_dir = tmp_path / "atlas"
    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True)
    (forge_dir / "scaffold.json").write_text(
        json.dumps(
            {
                "name": "atlas",
                "stack": "fastapi",
                "description": "Replay me",
                "project_brief": {
                    "audience": "Support coordinators",
                    "first_success": "Assign one shift",
                },
                "context_hash": "sha256:recorded",
                "routing": [{"phase": "architecture", "backend": "claude"}],
            }
        )
    )
    (forge_dir / "conventions-snapshot.md").write_text("snapshot conventions")
    (forge_dir / "context-snapshot.md").write_text(
        "<project_context>\nSelected file: PRODUCT.md\nSaved product context\n</project_context>\n"
    )

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("projectforge.router.check_backend_installed", lambda backend: True)

    result = runner.invoke(app, ["replay", "--dry-run"])

    assert result.exit_code == 0
    assert "Selected file: PRODUCT.md" in result.stdout
    assert "Saved product context" in result.stdout


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
        "projectforge.cli.load_bundled_conventions",
        lambda stack=None: (_ for _ in ()).throw(ConventionValidationError("unknown stack")),
    )
    monkeypatch.setattr("projectforge.router.check_backend_installed", lambda backend: True)

    result = runner.invoke(app, ["replay", "--dry-run"])

    assert result.exit_code == 1
    assert "could not load conventions for replay" in result.stdout
    assert "unknown stack" not in result.stdout


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
        "projectforge.cli.load_bundled_conventions",
        _fake_load_bundled_conventions,
    )
    monkeypatch.setattr("projectforge.router.check_backend_installed", lambda backend: True)

    result = runner.invoke(app, ["replay", "--dry-run"])
    output = " ".join(result.stdout.lower().split())

    assert result.exit_code == 1
    assert seen_stacks == []
    assert "recorded project type is no longer available" in output
    assert "not-a-real-stack" not in output


def test_replay_corrupt_scaffold_record_has_safe_recovery(monkeypatch, tmp_path):
    project_dir = tmp_path / "atlas"
    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True)
    (forge_dir / "scaffold.json").write_text("{not valid json")
    monkeypatch.chdir(project_dir)

    result = runner.invoke(app, ["replay", "--dry-run"])

    assert result.exit_code == 1
    assert "could not read this project's scaffold record" in result.stdout
    assert "JSONDecodeError" not in result.stdout
    assert "scaffold.json" not in result.stdout


def test_check_export_failure_has_safe_recovery(monkeypatch, tmp_path):
    export_path = tmp_path / "audit.md"
    monkeypatch.chdir(tmp_path)
    original_write_text = Path.write_text

    def unwritable(path: Path, *args, **kwargs):
        if path == export_path:
            raise OSError("private filesystem detail")
        return original_write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", unwritable)

    result = runner.invoke(app, ["check", "--export", str(export_path)])

    assert result.exit_code == 1
    assert "could not save the audit report" in result.stdout
    assert "private filesystem detail" not in result.stdout


def test_evolve_record_write_failure_has_safe_recovery(monkeypatch, tmp_path):
    project_dir = tmp_path / "atlas"
    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True)
    manifest_path = forge_dir / "scaffold.json"
    manifest_path.write_text(
        json.dumps({"name": "atlas", "stack": "fastapi", "description": "Evolve me"})
    )
    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("projectforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("projectforge.cli.check_backend_installed", lambda backend: True)
    monkeypatch.setattr("projectforge.cli.run_ai", lambda *args, **kwargs: 0)
    original_write_text = Path.write_text

    def unwritable(path: Path, *args, **kwargs):
        if path == manifest_path:
            raise OSError("private filesystem detail")
        return original_write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", unwritable)

    result = runner.invoke(app, ["evolve", "auth", "--use", "claude"])

    assert result.exit_code == 1
    assert "could not update the scaffold record" in result.stdout
    assert "private filesystem detail" not in result.stdout


def test_replay_diff_write_failure_has_safe_recovery(monkeypatch, tmp_path):
    project_dir = tmp_path / "atlas"
    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True)
    (forge_dir / "scaffold.json").write_text(
        json.dumps(
            {
                "name": "atlas",
                "stack": "python-cli",
                "description": "Replay me",
                "routing": [{"phase": "architecture", "backend": "claude"}],
            }
        )
    )
    (forge_dir / "conventions-snapshot.md").write_text("snapshot conventions")
    replay_dir = tmp_path / "replay"
    replay_dir.mkdir()
    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("projectforge.router.check_backend_installed", lambda backend: True)
    monkeypatch.setattr("projectforge.cli.run_ai", lambda *args, **kwargs: 0)
    monkeypatch.setattr("tempfile.mkdtemp", lambda **_kwargs: str(replay_dir))
    original_write_text = Path.write_text

    def unwritable(path: Path, *args, **kwargs):
        if path.name.startswith("replay-diff-"):
            raise OSError("private filesystem detail")
        return original_write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", unwritable)

    result = runner.invoke(app, ["replay", "--diff"])

    assert result.exit_code == 1
    assert "could not save the diff report" in result.stdout
    assert "private filesystem detail" not in result.stdout


def test_resolve_project_dir_allows_rename(monkeypatch, tmp_path):
    from projectforge.cli import _resolve_project_dir

    target = tmp_path / "existing"
    target.mkdir()
    (target / "keep.txt").write_text("keep")

    answers = {"name": "existing"}
    actions = iter(["rename"])

    monkeypatch.setattr(
        "projectforge.cli.prompt_select",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: next(actions)),
    )
    monkeypatch.setattr(
        "projectforge.cli.prompt_text",
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

    prompt_select_answers = iter(["_provider_default", "keep"])

    monkeypatch.setattr("projectforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("projectforge.setup.CONFIG_PATH", config_path)
    monkeypatch.setattr("projectforge.setup.CONVENTIONS_PATH", conventions_path)
    monkeypatch.setattr(
        "projectforge.setup.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=True, ready=True),
            "antigravity": BackendStatus(installed=False, ready=False),
            "codex": BackendStatus(installed=False, ready=False),
        },
    )
    monkeypatch.setattr(
        "projectforge.setup.load_forge_config",
        lambda: {
            "conventions_profile": "team",
            "agents": True,
            "sound": False,
        },
    )
    monkeypatch.setattr("projectforge.setup._check_editor_installed", lambda *_: (False, False))
    monkeypatch.setattr(
        "projectforge.setup.prompt_select",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: next(prompt_select_answers)),
    )
    monkeypatch.setattr(
        "projectforge.setup.prompt_text",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: ""),
    )
    monkeypatch.setattr("projectforge.media_assets.list_collections", lambda: [])
    monkeypatch.setattr("projectforge.media_assets.MEDIA_DIR", tmp_path / "media")
    monkeypatch.setattr(
        "projectforge.setup.shutil.which",
        lambda cmd: None if cmd in {"git", "docker"} else f"/usr/bin/{cmd}",
    )

    config = run_setup(console)
    output = console.export_text()

    assert config["available_backends"] == ["claude"]
    assert config["backend_models"] == {}
    assert config["conventions_profile"] == "team"
    assert config["agents"] is True
    assert config["sound"] is False
    assert not conventions_path.exists()
    assert "Conventions tell Forge how you want projects built" in output
    assert "import team instructions" in output
    assert "change the selected profile later" in output


def test_setup_missing_providers_shows_official_install_auth_recheck_flow(monkeypatch):
    console = Console(record=True, width=160)
    monkeypatch.setattr(
        "projectforge.setup.get_backend_statuses",
        lambda: {
            backend: BackendStatus(installed=False, ready=False)
            for backend in ("claude", "antigravity", "codex")
        },
    )

    with pytest.raises(SystemExit):
        run_setup(console)

    output = console.export_text()
    assert "projectforge#install-and-authenticate-a-provider" in output
    assert "could not find a supported AI tool" in output
    assert "forge doctor" in output


def test_admin_conventions_validate_passes() -> None:
    result = runner.invoke(app, ["admin", "conventions", "--validate"])

    assert result.exit_code == 0
    assert "Validation passed" in result.stdout


def test_user_convention_profile_init_select_and_inspect(monkeypatch, tmp_path):
    forge_dir = tmp_path / ".forge"
    profiles_dir = forge_dir / "profiles"
    config_path = forge_dir / "config.json"
    monkeypatch.setattr("projectforge.convention_profiles.PROFILES_DIR", profiles_dir)
    monkeypatch.setattr("projectforge.conventions.PROFILES_DIR", profiles_dir)
    monkeypatch.setattr("projectforge.conventions.CONVENTIONS_PATH", forge_dir / "conventions.md")
    monkeypatch.setattr(
        "projectforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / "project" / ".forge" / "conventions.md",
    )
    monkeypatch.setattr("projectforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("projectforge.setup.CONFIG_PATH", config_path)

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
    from projectforge.convention_history import GitHistoryResult

    monkeypatch.setattr(
        "projectforge.cli.load_history",
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
    from projectforge.convention_history import GitHistoryResult

    seen_targets: list[str] = []

    def _fake_load_history(root, target):
        seen_targets.append(target)
        return GitHistoryResult(
            target=target,
            available=True,
            entries=("abc123 Update global conventions",),
        )

    monkeypatch.setattr("projectforge.cli.load_history", _fake_load_history)

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
        "projectforge.cli.prompt_select",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: next(actions)),
    )

    result = runner.invoke(app, ["admin", "conventions"])

    assert result.exit_code == 0
    assert "Validation passed" in result.stdout
