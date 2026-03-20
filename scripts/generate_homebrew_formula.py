#!/usr/bin/env python3
"""Generate the Forge Homebrew formula from uv.lock."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ubundiforge.homebrew import (  # noqa: E402
    DEFAULT_HOMEPAGE,
    DEFAULT_PYTHON_FORMULA,
    DEFAULT_SOURCE_SHA256,
    DEFAULT_SOURCE_URL,
    write_homebrew_formula,
)


def parse_args() -> argparse.Namespace:
    """Parse generator arguments."""
    parser = argparse.ArgumentParser(
        description="Generate Formula/ubundiforge.rb from pyproject and uv.lock metadata.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "Formula" / "ubundiforge.rb",
        help="Formula output path.",
    )
    parser.add_argument(
        "--lock",
        type=Path,
        default=ROOT / "uv.lock",
        help="Path to uv.lock.",
    )
    parser.add_argument(
        "--source-url",
        default=DEFAULT_SOURCE_URL,
        help="Public tarball URL for the release source archive.",
    )
    parser.add_argument(
        "--source-sha256",
        default=DEFAULT_SOURCE_SHA256,
        help="SHA-256 for the public source tarball.",
    )
    parser.add_argument(
        "--homepage",
        default=DEFAULT_HOMEPAGE,
        help="Project homepage shown in Homebrew.",
    )
    parser.add_argument(
        "--python-formula",
        default=DEFAULT_PYTHON_FORMULA,
        help='Homebrew Python formula to depend on, for example "python@3.13".',
    )
    return parser.parse_args()


def main() -> None:
    """Generate the formula file."""
    args = parse_args()
    path = write_homebrew_formula(
        args.output,
        lock_path=args.lock,
        source_url=args.source_url,
        source_sha256=args.source_sha256,
        homepage=args.homepage,
        python_formula=args.python_formula,
    )
    print(path)


if __name__ == "__main__":
    main()
