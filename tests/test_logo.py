"""Tests for block-art logo rendering."""

from ubundiforge.logo import render_logo_text


def test_render_logo_text_produces_block_art():
    text = render_logo_text()
    plain = text.plain
    lines = plain.splitlines()

    assert len(lines) == 8  # 7 rows + 1 shadow row
    assert "\u2588\u2588" in plain


def test_render_logo_text_has_white_and_shadow_styles():
    text = render_logo_text()
    styles = {span.style for span in text._spans}
    assert any("bright_white" in str(s) for s in styles)
    assert any("#444444" in str(s) for s in styles)
