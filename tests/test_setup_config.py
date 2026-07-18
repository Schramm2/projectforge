"""Tests for resilient ProjectForge configuration persistence."""

import json
import stat
from io import StringIO

import pytest
from rich.console import Console

from projectforge.setup import (
    _configure_conventions_onboarding,
    _print_legacy_conventions_warning,
    load_forge_config,
    save_forge_config,
)


def test_guided_convention_onboarding_creates_and_selects_profile(monkeypatch, tmp_path):
    profiles_dir = tmp_path / "profiles"
    output = StringIO()
    console = Console(file=output, force_terminal=False, color_system=None, width=120)
    text_answers = iter(
        [
            "team",
            "Use uv and pnpm.",
            "Run focused tests.",
            "Keep domain logic isolated.",
            "Use strict typing.",
            "Document runnable commands.",
            "Ask before adding production dependencies.",
        ]
    )

    monkeypatch.setattr("projectforge.convention_profiles.PROFILES_DIR", profiles_dir)
    monkeypatch.setattr("projectforge.setup.prompt_select", lambda *a, **k: _answer("guided"))
    monkeypatch.setattr(
        "projectforge.setup.prompt_text",
        lambda *a, **k: _answer(next(text_answers)),
    )
    monkeypatch.setattr("projectforge.setup.prompt_confirm", lambda *a, **k: _answer(True))

    selected = _configure_conventions_onboarding(console, "default")

    assert selected == "team"
    content = (profiles_dir / "team.md").read_text()
    assert "Use uv and pnpm." in content
    assert "Ask before adding production dependencies." in content
    assert "Convention Profile Preview" in output.getvalue()
    assert "Selected convention profile: team" in output.getvalue()


def test_convention_onboarding_imports_only_selected_nearby_instructions(monkeypatch, tmp_path):
    profiles_dir = tmp_path / "profiles"
    agents = tmp_path / "AGENTS.md"
    claude = tmp_path / "CLAUDE.md"
    agents.write_text("# Shared rules\n\nUse strict typing.")
    claude.write_text("# Unselected rules\n\nUse a different package manager.")
    output = StringIO()
    console = Console(file=output, force_terminal=False, color_system=None, width=120)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("projectforge.convention_profiles.PROFILES_DIR", profiles_dir)
    monkeypatch.setattr("projectforge.setup.prompt_select", lambda *a, **k: _answer("import"))
    monkeypatch.setattr("projectforge.setup.prompt_checkbox", lambda *a, **k: _answer([agents]))
    monkeypatch.setattr("projectforge.setup.prompt_text", lambda *a, **k: _answer("team"))
    monkeypatch.setattr("projectforge.setup.prompt_confirm", lambda *a, **k: _answer(True))

    selected = _configure_conventions_onboarding(console, "default")

    assert selected == "team"
    content = (profiles_dir / "team.md").read_text()
    assert "Use strict typing." in content
    assert "different package manager" not in content
    assert "includes that profile in future provider prompts" in output.getvalue()


def _answer(value):
    return type("Answer", (), {"ask": lambda self: value})()


def test_save_forge_config_replaces_atomically(monkeypatch, tmp_path):
    forge_dir = tmp_path / ".forge"
    config_path = forge_dir / "config.json"
    monkeypatch.setattr("projectforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("projectforge.setup.CONFIG_PATH", config_path)

    save_forge_config({"preferred_editor": "code"})

    assert json.loads(config_path.read_text()) == {
        "config_version": 1,
        "preferred_editor": "code",
    }
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600
    assert list(forge_dir.glob(".config.json.*.tmp")) == []


def test_legacy_conventions_warning_hides_local_path(monkeypatch, tmp_path):
    legacy_path = tmp_path / "private" / "conventions.md"
    legacy_path.parent.mkdir()
    legacy_path.write_text("legacy rules")
    monkeypatch.setattr("projectforge.setup.CONVENTIONS_PATH", legacy_path)
    output = StringIO()
    console = Console(file=output, force_terminal=False, color_system=None, width=120)

    _print_legacy_conventions_warning(console)

    assert "legacy user conventions file" in output.getvalue()
    assert "Import it as a profile" in output.getvalue()
    assert str(legacy_path) not in output.getvalue()


def test_load_forge_config_preserves_corrupt_input(monkeypatch, tmp_path, capsys):
    forge_dir = tmp_path / ".forge"
    config_path = forge_dir / "config.json"
    forge_dir.mkdir()
    config_path.write_text("{ definitely not json")
    monkeypatch.setattr("projectforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("projectforge.setup.CONFIG_PATH", config_path)

    assert load_forge_config() == {}

    backups = list(forge_dir.glob("config.json.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "{ definitely not json"
    assert not config_path.exists()
    output = capsys.readouterr().out
    assert "could not read your saved settings" in output
    assert str(config_path) not in output
    assert ".corrupt-" not in output


def test_load_forge_config_migrates_v041_model_overrides_in_memory(monkeypatch, tmp_path):
    forge_dir = tmp_path / ".forge"
    config_path = forge_dir / "config.json"
    forge_dir.mkdir()
    config_path.write_text(json.dumps({"backend_models": {"claude": "opus"}}))
    monkeypatch.setattr("projectforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("projectforge.setup.CONFIG_PATH", config_path)

    config = load_forge_config()

    assert config["config_version"] == 1
    assert config["backend_models"] == {"claude": "opus"}


def test_save_forge_config_rejects_sensitive_or_unknown_keys(monkeypatch, tmp_path):
    forge_dir = tmp_path / ".forge"
    config_path = forge_dir / "config.json"
    monkeypatch.setattr("projectforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("projectforge.setup.CONFIG_PATH", config_path)

    with pytest.raises(ValueError, match="unsupported config key"):
        save_forge_config({"api_token": "must-not-be-stored"})

    assert not config_path.exists()


def test_save_forge_config_rejects_credential_shaped_model_override(monkeypatch, tmp_path):
    forge_dir = tmp_path / ".forge"
    config_path = forge_dir / "config.json"
    monkeypatch.setattr("projectforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("projectforge.setup.CONFIG_PATH", config_path)

    with pytest.raises(ValueError, match="credential-like"):
        save_forge_config({"backend_models": {"codex": "ghp_abcdefghijklmnopqrstuvwxyz1234567890"}})

    assert not config_path.exists()
