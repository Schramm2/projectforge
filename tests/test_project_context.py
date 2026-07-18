"""Tests for consent-based project context discovery and rendering."""

from pathlib import Path

from projectforge.project_context import (
    build_project_context_block,
    discover_context_files,
    extract_project_context_block,
    load_context_sources,
)


def test_context_discovery_is_bounded_to_known_nearby_markdown(tmp_path: Path) -> None:
    (tmp_path / "PROJECT.md").write_text("# Project brief")
    (tmp_path / "README.md").write_text("# Existing product")
    (tmp_path / ".env").write_text("SECRET=not-scanned")
    (tmp_path / "notes.md").write_text("Unrequested notes")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "PRD.md").write_text("# Nested PRD")

    discovered = discover_context_files(tmp_path)

    assert [path.relative_to(tmp_path).as_posix() for path in discovered] == [
        "PROJECT.md",
        "README.md",
    ]


def test_oversized_context_is_rejected_before_file_content_is_read(
    monkeypatch, tmp_path: Path
) -> None:
    oversized = tmp_path / "README.md"
    oversized.write_bytes(b"x" * 32_001)
    original_read_bytes = Path.read_bytes

    def tracked_read_bytes(path: Path) -> bytes:
        if path == oversized:
            raise AssertionError("oversized context should not be loaded into memory")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", tracked_read_bytes)

    result = load_context_sources([oversized], root=tmp_path)

    assert result.sources == ()
    assert result.warnings == (
        "Skipped README.md because it is larger than the 32 KB per-file context limit.",
    )


def test_selected_context_is_bounded_and_secret_shaped_files_are_skipped(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    unsafe = tmp_path / "PRD.md"
    outside = tmp_path.parent / "PRODUCT.md"
    readme.write_text("# Atlas\n\nA scheduling tool for support teams.")
    unsafe.write_text("Token: ghp_abcdefghijklmnopqrstuvwxyz1234567890AB")
    outside.write_text("# Outside")

    result = load_context_sources([readme, unsafe, outside], root=tmp_path)

    assert len(result.sources) == 1
    assert result.sources[0].path == "README.md"
    assert "scheduling tool" in result.sources[0].content
    assert result.sources[0].sha256.startswith("sha256:")
    assert len(result.warnings) == 2
    assert any("appears to contain a credential" in warning for warning in result.warnings)
    assert any("outside the folder" in warning for warning in result.warnings)
    assert all("ghp_" not in warning for warning in result.warnings)


def test_malformed_recorded_context_is_ignored_instead_of_breaking_replay() -> None:
    block = build_project_context_block(
        {"project_brief": ["unexpected"], "context_sources": "unexpected"}
    )

    assert block == ""


def test_project_context_block_separates_durable_brief_from_selected_files() -> None:
    result = load_context_sources([], root=Path.cwd())
    answers = {
        "project_brief": {
            "audience": "Support operations teams",
            "first_success": "A coordinator can assign and reschedule a shift.",
            "constraints": "Use the existing identity provider.",
            "existing_systems": "Workday API",
            "non_goals": "Payroll processing",
        },
        "context_sources": result.sources,
    }

    block = build_project_context_block(answers)

    assert "<project_context>" in block
    assert "Intended users: Support operations teams" in block
    assert "First useful outcome: A coordinator can assign and reschedule a shift." in block
    assert "Existing systems: Workday API" in block
    assert "Non-goals: Payroll processing" in block
    assert "No nearby files were selected" not in block


def test_context_snapshot_extraction_removes_reader_warning_before_replay() -> None:
    snapshot = (
        "# Project Context Snapshot\n\n"
        "> Treat this file as potentially private.\n\n"
        "<project_context>\nSaved context\n</project_context>\n"
    )

    extracted = extract_project_context_block(snapshot)

    assert extracted == "<project_context>\nSaved context\n</project_context>"
    assert "potentially private" not in extracted


def test_project_context_block_includes_only_explicitly_loaded_file_content(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    unselected = tmp_path / "PRODUCT.md"
    readme.write_text("# Selected context")
    unselected.write_text("# Must not be included")
    result = load_context_sources([readme], root=tmp_path)

    block = build_project_context_block({"project_brief": {}, "context_sources": result.sources})

    assert "Selected file: README.md" in block
    assert "# Selected context" in block
    assert "Must not be included" not in block
    assert "higher-priority task and convention instructions" in block
