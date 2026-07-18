"""Media asset detection, scanning, and import for scaffolded projects."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"

MEDIA_EXTENSIONS = frozenset(
    {
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
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Where assets land in the scaffolded project, per stack.
_TARGET_DIRS: dict[str, str] = {
    "nextjs": "public",
    "fastapi": "static",
    "fastapi-ai": "static",
    "both": "frontend/public",
    "python-cli": "assets",
    "ts-package": "assets",
    "python-worker": "assets",
}


@dataclass(frozen=True)
class AssetInfo:
    """A single media file found in the source directory."""

    relative_path: str
    extension: str
    size_bytes: int


@dataclass
class CopyResult:
    """Outcome of copying assets into a scaffolded project."""

    copied: int = 0
    skipped: int = 0
    target_dir: Path = field(default_factory=lambda: Path("."))
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MediaCollection:
    """A named folder of media assets inside ~/.forge/media/."""

    name: str
    path: Path
    file_count: int


def ensure_media_dir() -> Path:
    """Create ~/.forge/media/ if it doesn't exist and return the path."""
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    return MEDIA_DIR


def list_collections() -> list[MediaCollection]:
    """Return all media collections (subdirectories with media files).

    Each immediate subdirectory of ~/.forge/media/ that contains at least
    one recognised media file is considered a collection.
    """
    if not MEDIA_DIR.is_dir():
        return []

    collections: list[MediaCollection] = []
    for child in sorted(MEDIA_DIR.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        assets = scan_assets(child)
        if assets:
            collections.append(MediaCollection(name=child.name, path=child, file_count=len(assets)))
    return collections


def scan_media_dir() -> list[AssetInfo]:
    """Scan ~/.forge/media/ and return all recognised media files.

    Skips hidden files/directories and files exceeding MAX_FILE_SIZE.
    """
    return scan_assets(MEDIA_DIR)


def scan_assets(asset_dir: Path) -> list[AssetInfo]:
    """Walk *asset_dir* and return recognised media files."""
    if not asset_dir.is_dir():
        return []

    assets: list[AssetInfo] = []
    for path in sorted(asset_dir.rglob("*")):
        if not path.is_file():
            continue
        # Skip hidden files and directories
        if any(part.startswith(".") for part in path.relative_to(asset_dir).parts):
            continue
        if path.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        assets.append(
            AssetInfo(
                relative_path=str(path.relative_to(asset_dir)),
                extension=path.suffix.lower(),
                size_bytes=path.stat().st_size,
            )
        )
    return assets


def _format_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def build_asset_manifest(assets: list[AssetInfo], target_subdir: str) -> str:
    """Format a manifest block suitable for prompt injection."""
    if not assets:
        return ""

    lines = [
        f"Target directory: {target_subdir}/",
        "",
        "Files:",
    ]
    for asset in assets:
        lines.append(f"  {asset.relative_path} ({_format_size(asset.size_bytes)})")

    return "\n".join(lines)


def target_asset_dir(stack: str) -> str:
    """Return the canonical static-asset subdirectory for a stack."""
    return _TARGET_DIRS.get(stack, "assets")


def copy_assets(
    asset_dir: Path,
    project_dir: Path,
    stack: str,
) -> CopyResult:
    """Copy media assets into the scaffolded project.

    Preserves subdirectory structure. Skips files exceeding MAX_FILE_SIZE.
    """
    target_subdir = target_asset_dir(stack)
    dest = project_dir / target_subdir
    dest.mkdir(parents=True, exist_ok=True)

    result = CopyResult(target_dir=dest)
    assets = scan_assets(asset_dir)

    for asset in assets:
        src = asset_dir / asset.relative_path
        dst = dest / asset.relative_path

        if asset.size_bytes > MAX_FILE_SIZE:
            result.skipped += 1
            result.warnings.append(
                f"Skipped {asset.relative_path} ({_format_size(asset.size_bytes)} "
                f"exceeds {_format_size(MAX_FILE_SIZE)} limit)"
            )
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        result.copied += 1

    return result
