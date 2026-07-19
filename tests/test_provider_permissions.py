"""Tests for scoped, temporary provider permission grants."""

from __future__ import annotations

import json

from projectforge.provider_permissions import (
    allow_rule,
    workspace_write_permission,
)


def _settings(tmp_path):
    return tmp_path / "settings.json"


def test_noop_for_non_antigravity(tmp_path):
    settings = _settings(tmp_path)
    with workspace_write_permission("codex", "safe", tmp_path, settings_path=settings):
        assert not settings.exists()
    assert not settings.exists()


def test_noop_for_antigravity_plan_and_unsafe(tmp_path):
    settings = _settings(tmp_path)
    for mode in ("plan", "unsafe"):
        with workspace_write_permission("antigravity", mode, tmp_path, settings_path=settings):
            assert not settings.exists()
    assert not settings.exists()


def test_grants_narrow_rule_and_restores_absence(tmp_path):
    ws = tmp_path / "project"
    ws.mkdir()
    settings = _settings(tmp_path)

    with workspace_write_permission("antigravity", "safe", ws, settings_path=settings):
        data = json.loads(settings.read_text())
        allow = data["permissions"]["allow"]
        assert allow == [f"write_file({ws.resolve()})"]
        # Never broadened to a wildcard.
        assert "write_file(*)" not in allow

    # Forge created the file, so it is removed to restore the prior state.
    assert not settings.exists()


def test_preserves_existing_user_settings(tmp_path):
    ws = tmp_path / "project"
    ws.mkdir()
    settings = _settings(tmp_path)
    original = {
        "permissions": {"allow": ["read_file(/tmp/example)"]},
        "model": "gemini-pro",
    }
    settings.write_text(json.dumps(original, indent=2) + "\n")
    original_bytes = settings.read_bytes()

    with workspace_write_permission("antigravity", "safe", ws, settings_path=settings):
        data = json.loads(settings.read_text())
        assert data["model"] == "gemini-pro"
        assert "read_file(/tmp/example)" in data["permissions"]["allow"]
        assert f"write_file({ws.resolve()})" in data["permissions"]["allow"]

    # The user's file is restored byte-for-byte.
    assert settings.read_bytes() == original_bytes


def test_reference_counted_for_shared_workspace(tmp_path):
    ws = tmp_path / "project"
    ws.mkdir()
    settings = _settings(tmp_path)

    with workspace_write_permission("antigravity", "safe", ws, settings_path=settings):
        with workspace_write_permission("antigravity", "safe", ws, settings_path=settings):
            assert settings.exists()
        # Inner exit must not revoke the rule while the outer run continues.
        assert settings.exists()
        allow = json.loads(settings.read_text())["permissions"]["allow"]
        assert allow == [f"write_file({ws.resolve()})"]

    assert not settings.exists()


def test_allow_rule_is_workspace_scoped(tmp_path):
    ws = tmp_path / "project"
    ws.mkdir()
    assert allow_rule(ws) == f"write_file({ws.resolve()})"
