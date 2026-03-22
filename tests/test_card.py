# tests/test_card.py
"""Tests for the Forge card and badge generator."""

from pathlib import Path

from ubundiforge.card import generate_badge_svg, generate_card_svg, inject_badge_into_readme


def test_generate_badge_svg():
    svg = generate_badge_svg()
    assert svg.startswith("<svg")
    assert "UbundiForge" in svg
    assert "</svg>" in svg


def test_generate_card_svg():
    svg = generate_card_svg(
        name="pulse", stack="fastapi", backends=["claude", "codex"], date="2026-03-22"
    )
    assert svg.startswith("<svg")
    assert "pulse" in svg
    assert "fastapi" in svg
    assert "</svg>" in svg


def test_inject_badge_into_readme(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text("# My Project\n\nSome description.\n")
    inject_badge_into_readme(tmp_path)
    content = readme.read_text()
    assert "UbundiForge" in content
    assert "# My Project" in content  # heading preserved


def test_inject_badge_no_readme(tmp_path: Path):
    """Does not crash when README doesn't exist."""
    inject_badge_into_readme(tmp_path)  # should not raise


def test_inject_badge_idempotent(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text("# My Project\n\nSome description.\n")
    inject_badge_into_readme(tmp_path)
    inject_badge_into_readme(tmp_path)
    content = readme.read_text()
    assert content.count("UbundiForge") == 1  # not duplicated
