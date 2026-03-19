"""Tests for ubundiforge.media_assets."""

from pathlib import Path

from ubundiforge.media_assets import (
    MEDIA_EXTENSIONS,
    AssetInfo,
    build_asset_manifest,
    copy_assets,
    list_collections,
    scan_assets,
    target_asset_dir,
)


def _create_file(path: Path, content: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_scan_assets_finds_media_files(tmp_path: Path) -> None:
    _create_file(tmp_path / "logo.svg", b"<svg/>")
    _create_file(tmp_path / "hero.png", b"\x89PNG")
    _create_file(tmp_path / "readme.txt", b"not media")

    assets = scan_assets(tmp_path)
    extensions = {a.extension for a in assets}
    assert extensions == {".svg", ".png"}


def test_scan_assets_skips_hidden_files(tmp_path: Path) -> None:
    _create_file(tmp_path / ".hidden" / "secret.png", b"\x89PNG")
    _create_file(tmp_path / ".DS_Store", b"ds")
    _create_file(tmp_path / "visible.png", b"\x89PNG")

    assets = scan_assets(tmp_path)
    assert len(assets) == 1
    assert assets[0].relative_path == "visible.png"


def test_scan_assets_preserves_subdirectory_structure(tmp_path: Path) -> None:
    _create_file(tmp_path / "icons" / "favicon.ico", b"ico")
    _create_file(tmp_path / "images" / "bg.jpg", b"jpg")

    assets = scan_assets(tmp_path)
    paths = {a.relative_path for a in assets}
    assert "icons/favicon.ico" in paths
    assert "images/bg.jpg" in paths


def test_scan_assets_returns_empty_for_missing_dir(tmp_path: Path) -> None:
    assert scan_assets(tmp_path / "nonexistent") == []


def test_scan_assets_returns_empty_for_empty_dir(tmp_path: Path) -> None:
    assert scan_assets(tmp_path) == []


def test_build_asset_manifest_formats_file_listing() -> None:
    assets = [
        AssetInfo(relative_path="logo.svg", extension=".svg", size_bytes=2048),
        AssetInfo(relative_path="images/hero.png", extension=".png", size_bytes=150_000),
    ]
    manifest = build_asset_manifest(assets, "public")

    assert "Target directory: public/" in manifest
    assert "logo.svg (2.0 KB)" in manifest
    assert "images/hero.png (146.5 KB)" in manifest


def test_build_asset_manifest_returns_empty_for_no_assets() -> None:
    assert build_asset_manifest([], "public") == ""


def test_target_asset_dir_returns_correct_paths() -> None:
    assert target_asset_dir("nextjs") == "public"
    assert target_asset_dir("fastapi") == "static"
    assert target_asset_dir("both") == "frontend/public"
    assert target_asset_dir("python-cli") == "assets"
    assert target_asset_dir("unknown") == "assets"


def test_copy_assets_copies_files(tmp_path: Path) -> None:
    src = tmp_path / "source"
    dest = tmp_path / "project"
    _create_file(src / "logo.svg", b"<svg/>")
    _create_file(src / "icons" / "fav.ico", b"ico")

    result = copy_assets(src, dest, "nextjs")

    assert result.copied == 2
    assert result.skipped == 0
    assert (dest / "public" / "logo.svg").exists()
    assert (dest / "public" / "icons" / "fav.ico").exists()


def test_copy_assets_skips_oversized_files(tmp_path: Path) -> None:
    src = tmp_path / "source"
    dest = tmp_path / "project"
    _create_file(src / "small.png", b"x" * 100)
    _create_file(src / "huge.mp4", b"x" * (11 * 1024 * 1024))

    result = copy_assets(src, dest, "nextjs")

    assert result.copied == 1
    assert result.skipped == 1
    assert len(result.warnings) == 1
    assert "huge.mp4" in result.warnings[0]


def test_list_collections_finds_subdirectories(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setattr("ubundiforge.media_assets.MEDIA_DIR", tmp_path)

    _create_file(tmp_path / "ubundi" / "logo.svg", b"<svg/>")
    _create_file(tmp_path / "ubundi" / "hero.png", b"png")
    _create_file(tmp_path / "client-x" / "banner.jpg", b"jpg")
    # Hidden dir should be skipped
    _create_file(tmp_path / ".hidden" / "secret.png", b"png")
    # Loose file at root (not a collection)
    _create_file(tmp_path / "stray.png", b"png")

    collections = list_collections()
    names = {c.name for c in collections}
    assert names == {"ubundi", "client-x"}

    ubundi = next(c for c in collections if c.name == "ubundi")
    assert ubundi.file_count == 2


def test_list_collections_returns_empty_when_no_dirs(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setattr("ubundiforge.media_assets.MEDIA_DIR", tmp_path)
    # Only loose files, no subdirectories
    _create_file(tmp_path / "stray.png", b"png")

    assert list_collections() == []


def test_list_collections_skips_dirs_without_media(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setattr("ubundiforge.media_assets.MEDIA_DIR", tmp_path)
    _create_file(tmp_path / "empty-brand" / "readme.txt", b"not media")

    assert list_collections() == []


def test_all_expected_extensions_covered() -> None:
    expected = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".webp",
        ".avif",
        ".mp4",
        ".webm",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".pdf",
    }
    assert MEDIA_EXTENSIONS == expected
