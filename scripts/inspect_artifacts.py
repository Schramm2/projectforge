#!/usr/bin/env python3
"""Inspect built wheel and source archive for required release contents."""

from __future__ import annotations

import email
import tarfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def _one(pattern: str) -> Path:
    matches = sorted(DIST.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"Expected one {pattern} artifact, found {len(matches)}")
    return matches[0]


def inspect_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        required_suffixes = {
            "ubundiforge/__init__.py",
            "ubundiforge/skills/forge-scaffold/SKILL.md",
            "ubundiforge/skills/forge-scaffold/agents/openai.yaml",
        }
        for suffix in required_suffixes:
            if not any(name.endswith(suffix) for name in names):
                raise SystemExit(f"Wheel is missing {suffix}")
        if not any("ubundiforge/conventions/" in name for name in names):
            raise SystemExit("Wheel is missing bundled conventions")
        metadata_name = next((name for name in names if name.endswith(".dist-info/METADATA")), None)
        if metadata_name is None:
            raise SystemExit("Wheel is missing distribution metadata")
        metadata = email.message_from_bytes(archive.read(metadata_name))
        if metadata["Name"] != "projectforge":
            raise SystemExit(f"Unexpected wheel distribution name: {metadata['Name']}")
        if not metadata["Version"]:
            raise SystemExit("Wheel metadata has no version")
        if not metadata["Requires-Python"]:
            raise SystemExit("Wheel metadata has no Python requirement")


def inspect_sdist(path: Path) -> None:
    with tarfile.open(path, "r:gz") as archive:
        names = set(archive.getnames())
    required_suffixes = {
        "/README.md",
        "/CHANGELOG.md",
        "/SECURITY.md",
        "/LICENSE",
        "/docs/guides/getting-started.md",
        "/docs/guides/migrating-from-0.4.1.md",
        "/skills/forge-scaffold/SKILL.md",
        "/skills/forge-scaffold/agents/openai.yaml",
    }
    for suffix in required_suffixes:
        if not any(name.endswith(suffix) for name in names):
            raise SystemExit(f"Source archive is missing {suffix.removeprefix('/')}")
    if not any("/conventions/" in name for name in names):
        raise SystemExit("Source archive is missing bundled conventions")


def main() -> int:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    wheel = _one(f"projectforge-{version}-*.whl")
    sdist = _one(f"projectforge-{version}.tar.gz")
    inspect_wheel(wheel)
    inspect_sdist(sdist)
    print(f"Artifacts valid: {wheel.name}, {sdist.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
