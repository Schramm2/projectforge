"""Tests for the adaptive preferences module."""

import json
from pathlib import Path

from ubundiforge.preferences import get_defaults, load_preferences, record_preferences


def test_record_preferences_creates_file(tmp_path: Path, monkeypatch):
    prefs_path = tmp_path / "preferences.json"
    monkeypatch.setattr("ubundiforge.preferences.PREFERENCES_PATH", prefs_path)
    monkeypatch.setattr("ubundiforge.preferences.FORGE_DIR", tmp_path)

    answers = {"stack": "fastapi", "docker": True, "auth_provider": "clerk"}
    record_preferences(answers)

    data = json.loads(prefs_path.read_text())
    assert data["stack"]["fastapi"] == 1
    assert data["docker"]["True"] == 1
    assert data["auth_provider"]["clerk"] == 1


def test_record_preferences_increments(tmp_path: Path, monkeypatch):
    prefs_path = tmp_path / "preferences.json"
    monkeypatch.setattr("ubundiforge.preferences.PREFERENCES_PATH", prefs_path)
    monkeypatch.setattr("ubundiforge.preferences.FORGE_DIR", tmp_path)

    record_preferences({"stack": "fastapi"})
    record_preferences({"stack": "fastapi"})
    record_preferences({"stack": "nextjs"})

    data = json.loads(prefs_path.read_text())
    assert data["stack"]["fastapi"] == 2
    assert data["stack"]["nextjs"] == 1


def test_load_preferences_empty(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("ubundiforge.preferences.PREFERENCES_PATH", tmp_path / "nope.json")
    assert load_preferences() == {}


def test_get_defaults_no_dominant(tmp_path: Path, monkeypatch):
    prefs_path = tmp_path / "preferences.json"
    prefs_path.write_text('{"stack": {"fastapi": 1, "nextjs": 1}}')
    monkeypatch.setattr("ubundiforge.preferences.PREFERENCES_PATH", prefs_path)

    defaults = get_defaults()
    assert "stack" not in defaults


def test_get_defaults_with_dominant(tmp_path: Path, monkeypatch):
    prefs_path = tmp_path / "preferences.json"
    prefs_path.write_text('{"stack": {"fastapi": 8, "nextjs": 1}}')
    monkeypatch.setattr("ubundiforge.preferences.PREFERENCES_PATH", prefs_path)

    defaults = get_defaults()
    assert defaults["stack"] == "fastapi"


def test_get_defaults_minimum_count(tmp_path: Path, monkeypatch):
    prefs_path = tmp_path / "preferences.json"
    prefs_path.write_text('{"stack": {"fastapi": 2}}')
    monkeypatch.setattr("ubundiforge.preferences.PREFERENCES_PATH", prefs_path)

    defaults = get_defaults()
    assert "stack" not in defaults


def test_record_preferences_skips_complex_types(tmp_path: Path, monkeypatch):
    prefs_path = tmp_path / "preferences.json"
    monkeypatch.setattr("ubundiforge.preferences.PREFERENCES_PATH", prefs_path)
    monkeypatch.setattr("ubundiforge.preferences.FORGE_DIR", tmp_path)

    answers = {
        "stack": "fastapi",
        "ci": {"include": True, "actions": ["lint"]},
        "services_list": ["pg"],
    }
    record_preferences(answers)

    data = json.loads(prefs_path.read_text())
    assert "stack" in data
    assert "ci" not in data  # dict skipped
    assert "services_list" not in data  # in skip keys
