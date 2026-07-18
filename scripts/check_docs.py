#!/usr/bin/env python3
"""Fail when a tracked Markdown document contains a broken local link."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")


def _markdown_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def broken_links() -> list[str]:
    """Return human-readable failures for missing repository-local link targets."""
    failures: list[str] = []
    for document in _markdown_files():
        for line_number, line in enumerate(document.read_text().splitlines(), start=1):
            for raw_target in LINK_RE.findall(line):
                target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
                if (
                    not target
                    or target.startswith(("http://", "https://", "mailto:", "#"))
                    or "{" in target
                ):
                    continue
                path_text = unquote(target.split("#", 1)[0])
                resolved = (document.parent / path_text).resolve()
                if not resolved.exists():
                    relative_document = document.relative_to(ROOT)
                    failures.append(f"{relative_document}:{line_number}: missing {target}")
    return failures


def main() -> int:
    failures = broken_links()
    if failures:
        print("Broken local documentation links:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Documentation links are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
