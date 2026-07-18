#!/usr/bin/env python3
"""Scan tracked files for public-safety and privacy guardrails."""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BannedPattern:
    """A case-insensitive pattern that should not appear in public tracked files."""

    name: str
    regex: re.Pattern[str]


BANNED_PATTERNS = [
    BannedPattern(
        "local user path",
        re.compile(r"/(?:Users|home)/[^/\s]+(?:/|\b)", re.I),
    ),
    BannedPattern(
        "email address",
        re.compile(r"\b[\w.+-]+@(?:[\w-]+\.)+[A-Za-z]{2,}\b", re.I),
    ),
    BannedPattern("private workspace path", re.compile(r"Workspace\.nosync|Brain Dump", re.I)),
    BannedPattern("internal docs path", re.compile(r"\bdocs/internal\b", re.I)),
    BannedPattern(
        "public install placeholder",
        re.compile(
            r"<(?:tap-owner|tap|repository-url|release-tarball-url|tarball-url|sha256)>|"
            r"github\.com/projectforge/projectforge|"
            r"REPLACE_WITH_RELEASE_TARBALL_SHA256",
            re.I,
        ),
    ),
    BannedPattern(
        "private prompt wording",
        re.compile(r"\bprivate\s+prompts?\b|\binternal\s+repo\s+names?\b", re.I),
    ),
]

# Files that define or exercise the checks rather than public-facing content.
ALLOWLIST_FILES = {
    "scripts/scan_safety.py",
    "tests/test_scan_safety.py",
    "uv.lock",
}

BINARY_SUFFIXES = {
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".svgz",
    ".webm",
    ".woff",
    ".woff2",
}


def get_public_files() -> list[str]:
    """Get tracked and untracked non-ignored files via git ls-files."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        print(f"Warning: Git command failed ({exc}). Scanning workspace files directly...")
        # Fallback to general file walk excluding git/venv
        root = Path(".")
        files = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            parts = path.parts
            if ".git" in parts or ".venv" in parts or "dist" in parts or ".uv-cache" in parts:
                continue
            files.append(str(path))
        return files


def is_allowed(file_str: str, pattern_name: str, line: str) -> bool:
    """Return whether a banned match has a documented file-level exception."""
    if file_str in ALLOWLIST_FILES:
        return True
    if pattern_name == "email address":
        return "git@github.com" in line or re.search(
            r"@[A-Za-z0-9.-]*example\.(?:com|net|org|test)\b", line, re.I
        ) is not None
    return False


def scan_file(file_str: str, file_path: Path) -> list[tuple[int, str, str]]:
    """Scan a single file. Returns list of (line_num, pattern_name, line_content)."""
    violations = []
    if file_path.suffix.lower() in BINARY_SUFFIXES:
        return violations
    try:
        # Read text, ignoring binary decoding errors
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern in BANNED_PATTERNS:
                if pattern.regex.search(line) and not is_allowed(file_str, pattern.name, line):
                    violations.append((line_num, pattern.name, line.strip()))
    except OSError as exc:
        print(f"Skipping file {file_path} due to error: {exc}")
    return violations


def main() -> None:
    """Run the scanner."""
    public_files = [file_str for file_str in get_public_files() if Path(file_str).is_file()]
    total_violations = 0

    print(f"Scanning {len(public_files)} public working-tree files for safety guardrails...")

    for file_str in public_files:
        if file_str in ALLOWLIST_FILES:
            continue
        file_path = Path(file_str)
        if not file_path.exists():
            continue

        violations = scan_file(file_str, file_path)
        if violations:
            total_violations += len(violations)
            print(f"\n[VIOLATION] in {file_str}:")
            for line_num, pattern_name, line_content in violations:
                print(
                    f"  Line {line_num}: matched '{pattern_name}' -> \"{line_content}\""
                )

    if total_violations > 0:
        print(f"\nScan failed. Found {total_violations} safety violations.")
        sys.exit(1)

    print("Success: No safety violations found.")
    sys.exit(0)


if __name__ == "__main__":
    main()
