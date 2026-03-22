"""Tests for CLI execution paths."""

import json
from pathlib import Path
from types import SimpleNamespace

from rich.console import Console
from typer.testing import CliRunner

from ubundiforge.cli import app
from ubundiforge.config import BackendStatus
from ubundiforge.setup import run_setup

runner = CliRunner()


def _patch_prompt_only_dependencies(monkeypatch, *, setup_called: list[bool]) -> None:
    monkeypatch.setattr("ubundiforge.cli.print_logo", lambda console: None)
    monkeypatch.setattr("ubundiforge.cli.needs_setup", lambda: True)
    monkeypatch.setattr("ubundiforge.cli.load_forge_config", lambda: {})
    monkeypatch.setattr(
        "ubundiforge.cli.get_backend_statuses",
        lambda: {
            backend: BackendStatus(installed=False, ready=False)
            for backend in ("claude", "gemini", "codex")
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
    assert "=== Frontend & UI (gemini) ===" in exported
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
            for backend in ("claude", "gemini", "codex")
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
    ) -> int:
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
    assert "Project Ready" in result.stdout


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
            for backend in ("claude", "gemini", "codex")
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
    monkeypatch.setattr("ubundiforge.cli.run_ai", lambda *args, **kwargs: 0)
    monkeypatch.setattr(
        "ubundiforge.cli.run_ai_parallel",
        lambda phases, project_dir, verbose=False: [],
    )
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
    assert "Project Ready" in result.stdout


def test_replay_without_snapshot_loads_compiled_conventions_for_manifest_stack(monkeypatch, tmp_path):
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

    def _fake_load_conventions(stack=None):
        seen_stacks.append(stack)
        return (f"compiled conventions for {stack}", [])

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr("ubundiforge.cli.load_conventions", _fake_load_conventions)
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

    prompt_select_answers = iter(["claude-opus-4-6"])

    monkeypatch.setattr("ubundiforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("ubundiforge.setup.CONFIG_PATH", config_path)
    monkeypatch.setattr("ubundiforge.setup.CONVENTIONS_PATH", conventions_path)
    monkeypatch.setattr(
        "ubundiforge.setup.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=True, ready=True),
            "gemini": BackendStatus(installed=False, ready=False),
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
    assert not conventions_path.exists()
    assert "bundled conventions" in output.lower()
    assert "forge admin conventions" in output
