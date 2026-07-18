"""Tests for user-owned convention profile lifecycle."""

import pytest

from projectforge.convention_models import ConventionValidationError
from projectforge.convention_profiles import import_profile, initialize_profile, list_profiles


def test_initialize_profile_creates_stable_default_without_overwrite(monkeypatch, tmp_path):
    monkeypatch.setattr("projectforge.convention_profiles.PROFILES_DIR", tmp_path / "profiles")

    path = initialize_profile("default")

    assert path.name == "default.md"
    assert "Convention Profile" in path.read_text()
    with pytest.raises(ConventionValidationError, match="already exists"):
        initialize_profile("default")


def test_profile_names_cannot_escape_profile_directory(monkeypatch, tmp_path):
    monkeypatch.setattr("projectforge.convention_profiles.PROFILES_DIR", tmp_path / "profiles")

    with pytest.raises(ConventionValidationError, match="profile name is not valid"):
        initialize_profile("../outside")


def test_import_profile_accepts_instruction_markdown_and_rejects_secrets(monkeypatch, tmp_path):
    monkeypatch.setattr("projectforge.convention_profiles.PROFILES_DIR", tmp_path / "profiles")
    source = tmp_path / "AGENTS.md"
    source.write_text("# Agent rules\n\nUse strict typing and focused tests.")

    imported = import_profile(source, "team")

    assert imported.read_text() == source.read_text()
    assert list_profiles() == ("team",)

    secret_source = tmp_path / "CLAUDE.md"
    secret_source.write_text("Never print ghp_abcdefghijklmnopqrstuvwxyz1234567890AB")
    with pytest.raises(ConventionValidationError, match="looks like a credential"):
        import_profile(secret_source, "unsafe")
