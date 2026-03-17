"""Tests for compact logo rendering."""

from ubundiforge.logo import DEFAULT_MAX_HEIGHT, DEFAULT_MAX_WIDTH, FALLBACK_LOGO, render_logo


def test_render_logo_scales_asset_to_cli_friendly_size(tmp_path, monkeypatch):
    art_path = tmp_path / "ascii-art.txt"
    art_path.write_text(
        "\n".join(
            [
                "................................................",
                "....########..............########..............",
                "..##########............##########..............",
                ".###########............###########.............",
                "....########..............########..............",
                "................................................",
                "....########..............########..............",
                "..##########............##########..............",
                ".###########............###########.............",
                "....########..............########..............",
                "................................................",
                "....########..............########..............",
                "..##########............##########..............",
                ".###########............###########.............",
            ]
        )
    )
    monkeypatch.setattr("ubundiforge.logo.LOGO_PATHS", (art_path,))

    rendered = render_logo(terminal_width=80)
    lines = rendered.splitlines()

    assert lines
    assert len(lines) <= DEFAULT_MAX_HEIGHT
    assert max(len(line) for line in lines) <= DEFAULT_MAX_WIDTH
    assert "#" in rendered
    assert "." not in rendered


def test_render_logo_respects_narrow_terminal_width(tmp_path, monkeypatch):
    art_path = tmp_path / "ascii-art.txt"
    art_path.write_text(
        "\n".join(
            [
                "############################",
                "############################",
                "############################",
                "############################",
                "############################",
                "############################",
            ]
        )
    )
    monkeypatch.setattr("ubundiforge.logo.LOGO_PATHS", (art_path,))

    rendered = render_logo(terminal_width=24)

    assert max(len(line) for line in rendered.splitlines()) <= 20


def test_render_logo_falls_back_when_asset_is_missing(monkeypatch):
    monkeypatch.setattr("ubundiforge.logo.LOGO_PATHS", ())

    assert render_logo() == FALLBACK_LOGO
