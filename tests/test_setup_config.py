"""Tests for resilient ProjectForge configuration persistence."""

import json
import stat

import pytest

from ubundiforge.setup import load_forge_config, save_forge_config


def test_save_forge_config_replaces_atomically(monkeypatch, tmp_path):
    forge_dir = tmp_path / ".forge"
    config_path = forge_dir / "config.json"
    monkeypatch.setattr("ubundiforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("ubundiforge.setup.CONFIG_PATH", config_path)

    save_forge_config({"preferred_editor": "code"})

    assert json.loads(config_path.read_text()) == {
        "config_version": 1,
        "preferred_editor": "code",
    }
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600
    assert list(forge_dir.glob(".config.json.*.tmp")) == []


def test_load_forge_config_preserves_corrupt_input(monkeypatch, tmp_path):
    forge_dir = tmp_path / ".forge"
    config_path = forge_dir / "config.json"
    forge_dir.mkdir()
    config_path.write_text("{ definitely not json")
    monkeypatch.setattr("ubundiforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("ubundiforge.setup.CONFIG_PATH", config_path)

    assert load_forge_config() == {}

    backups = list(forge_dir.glob("config.json.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "{ definitely not json"
    assert not config_path.exists()


def test_load_forge_config_migrates_v041_model_overrides_in_memory(monkeypatch, tmp_path):
    forge_dir = tmp_path / ".forge"
    config_path = forge_dir / "config.json"
    forge_dir.mkdir()
    config_path.write_text(json.dumps({"backend_models": {"claude": "opus"}}))
    monkeypatch.setattr("ubundiforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("ubundiforge.setup.CONFIG_PATH", config_path)

    config = load_forge_config()

    assert config["config_version"] == 1
    assert config["backend_models"] == {"claude": "opus"}


def test_save_forge_config_rejects_sensitive_or_unknown_keys(monkeypatch, tmp_path):
    forge_dir = tmp_path / ".forge"
    config_path = forge_dir / "config.json"
    monkeypatch.setattr("ubundiforge.setup.FORGE_DIR", forge_dir)
    monkeypatch.setattr("ubundiforge.setup.CONFIG_PATH", config_path)

    with pytest.raises(ValueError, match="unsupported config key"):
        save_forge_config({"api_token": "must-not-be-stored"})

    assert not config_path.exists()
