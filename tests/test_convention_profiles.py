"""Tests for user-owned convention profile lifecycle."""

import pytest

from projectforge.convention_models import ConventionValidationError
from projectforge.convention_profiles import (
    create_guided_profile,
    discover_instruction_files,
    import_profile,
    import_profile_sources,
    initialize_profile,
    list_profiles,
)


def test_initialize_profile_creates_stable_default_without_overwrite(monkeypatch, tmp_path):
    monkeypatch.setattr("projectforge.convention_profiles.PROFILES_DIR", tmp_path / "profiles")

    path = initialize_profile("default")

    assert path.name == "default.md"
    content = path.read_text()
    assert "Convention Profile" in content
    assert "## Testing and verification" in content
    assert "## Rules Forge should respect" in content
    with pytest.raises(ConventionValidationError, match="already exists"):
        initialize_profile("default")


def test_profile_names_cannot_escape_profile_directory(monkeypatch, tmp_path):
    monkeypatch.setattr("projectforge.convention_profiles.PROFILES_DIR", tmp_path / "profiles")

    with pytest.raises(ConventionValidationError, match="profile name is not valid"):
        initialize_profile("../outside")


def test_guided_profile_records_only_the_preferences_the_user_supplied(monkeypatch, tmp_path):
    monkeypatch.setattr("projectforge.convention_profiles.PROFILES_DIR", tmp_path / "profiles")

    path = create_guided_profile(
        "team",
        {
            "toolchain": "Use uv for Python and pnpm for TypeScript.",
            "testing": "Require focused tests and run them before handoff.",
            "architecture": "",
            "code_style": "Prefer strict typing.",
            "git_docs": "",
            "guardrails": "Do not add production dependencies without approval.",
        },
    )

    content = path.read_text()
    assert "## Toolchain" in content
    assert "Use uv for Python and pnpm for TypeScript." in content
    assert "## Testing and verification" in content
    assert "## Architecture and organization" not in content
    assert "Do not add production dependencies without approval." in content


def test_instruction_discovery_is_bounded_to_known_files(monkeypatch, tmp_path):
    (tmp_path / "AGENTS.md").write_text("# Shared rules")
    (tmp_path / "README.md").write_text("# Product")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "copilot-instructions.md").write_text("# Copilot rules")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "CLAUDE.md").write_text("# Nested rules")

    discovered = discover_instruction_files(tmp_path)

    assert [path.relative_to(tmp_path).as_posix() for path in discovered] == [
        "AGENTS.md",
        ".github/copilot-instructions.md",
    ]


def test_oversized_instruction_is_rejected_before_content_is_read(monkeypatch, tmp_path):
    monkeypatch.setattr("projectforge.convention_profiles.PROFILES_DIR", tmp_path / "profiles")
    oversized = tmp_path / "AGENTS.md"
    oversized.write_bytes(b"x" * 1_000_001)
    original_read_text = type(oversized).read_text

    def tracked_read_text(path, *args, **kwargs):
        if path == oversized:
            raise AssertionError("oversized instruction should not be loaded into memory")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(type(oversized), "read_text", tracked_read_text)

    with pytest.raises(ConventionValidationError, match="larger than 1 MB"):
        import_profile(oversized, "too-large")


def test_import_profile_sources_combines_selected_files_and_rejects_secrets(monkeypatch, tmp_path):
    monkeypatch.setattr("projectforge.convention_profiles.PROFILES_DIR", tmp_path / "profiles")
    agents = tmp_path / "AGENTS.md"
    claude = tmp_path / "CLAUDE.md"
    agents.write_text("# Shared rules\n\nUse strict typing.")
    claude.write_text("# Commands\n\nRun focused tests before handoff.")

    imported = import_profile_sources([agents, claude], "team")

    content = imported.read_text()
    assert "Source: AGENTS.md" in content
    assert "Use strict typing." in content
    assert "Source: CLAUDE.md" in content
    assert "Run focused tests before handoff." in content

    unsafe = tmp_path / "unsafe.md"
    unsafe.write_text("Never print ghp_abcdefghijklmnopqrstuvwxyz1234567890AB")
    with pytest.raises(ConventionValidationError, match="looks like a credential"):
        import_profile_sources([agents, unsafe], "unsafe")


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
