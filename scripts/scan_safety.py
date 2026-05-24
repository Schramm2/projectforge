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


@dataclass(frozen=True)
class AllowedOccurrence:
    """A narrow exception for compatibility references that are safe to publish."""

    pattern_name: str
    path_regex: re.Pattern[str]
    line_regex: re.Pattern[str]
    reason: str


BANNED_PATTERNS = [
    BannedPattern("legacy company brand", re.compile(r"\bubundi\b|ubundi(?=[._-])", re.I)),
    BannedPattern("legacy package brand", re.compile(r"\bubundiforge\b", re.I)),
    BannedPattern("personal GitHub owner", re.compile(r"\bmatthewubundi\b", re.I)),
    BannedPattern("personal machine/user name", re.compile(r"\bmatthew-schramm\b", re.I)),
    BannedPattern("personal local path", re.compile(r"/Users/matthew-schramm(?:-ubundi)?", re.I)),
    BannedPattern(
        "private email/domain",
        re.compile(r"\b[\w.+-]+@ubundi\.co\.za\b|\bubundi\.co\.za\b", re.I),
    ),
    BannedPattern("internal docs path", re.compile(r"\bdocs/internal\b", re.I)),
    BannedPattern("private repo wording", re.compile(r"\bexisting\s+ubundi\s+repos?\b", re.I)),
    BannedPattern("old tap name", re.compile(r"\bhomebrew-tap\b", re.I)),
    BannedPattern(
        "private prompt wording",
        re.compile(r"\bprivate\s+prompts?\b|\binternal\s+repo\s+names?\b", re.I),
    ),
]

UBUNDIFORGE_NAMESPACE_LINE = re.compile(
    r"("
    r"\bfrom ubundiforge\b|"
    r"\bimport ubundiforge\b|"
    r"ubundiforge\.[A-Za-z0-9_.]+|"
    r"src/ubundiforge|"
    r"python -m ubundiforge|"
    r"ubundiforge.__main__:main|"
    r"packages = \[\"src/ubundiforge\"\]|"
    r"ubundiforge/conventions|"
    r"/src/ubundiforge|"
    r"test -d src/ubundiforge|"
    r"compatibility namespace|"
    r"Python import namespace remains `ubundiforge`|"
    r"Module entry point for `python -m ubundiforge`|"
    r"Tests for ubundiforge\.media_assets|"
    r"# src/ubundiforge/card\.py|"
    r"console\.print\(f\"ubundiforge \{__version__\}\"\)"
    r")",
    re.I,
)

ALLOWLIST = [
    AllowedOccurrence(
        "legacy package brand",
        re.compile(r".*"),
        UBUNDIFORGE_NAMESPACE_LINE,
        "The Python package directory/import namespace remains for compatibility.",
    ),
    AllowedOccurrence(
        "legacy company brand",
        re.compile(r"scripts/scan_safety\.py"),
        re.compile(r".*"),
        "The scanner must define the exact legacy brand terms it blocks.",
    ),
    AllowedOccurrence(
        "legacy package brand",
        re.compile(r"scripts/scan_safety\.py"),
        re.compile(r".*"),
        "The scanner must define the exact legacy package terms it blocks.",
    ),
    AllowedOccurrence(
        "personal GitHub owner",
        re.compile(r"scripts/scan_safety\.py"),
        re.compile(r".*"),
        "The scanner must define the exact personal owner term it blocks.",
    ),
    AllowedOccurrence(
        "personal machine/user name",
        re.compile(r"scripts/scan_safety\.py"),
        re.compile(r".*"),
        "The scanner must define the exact local machine/user term it blocks.",
    ),
    AllowedOccurrence(
        "personal local path",
        re.compile(r"scripts/scan_safety\.py"),
        re.compile(r".*"),
        "The scanner must define the exact local path prefix it blocks.",
    ),
    AllowedOccurrence(
        "private email/domain",
        re.compile(r"scripts/scan_safety\.py"),
        re.compile(r".*"),
        "The scanner must define the exact private domain it blocks.",
    ),
    AllowedOccurrence(
        "internal docs path",
        re.compile(r"scripts/scan_safety\.py"),
        re.compile(r".*"),
        "The scanner must define the exact internal docs path it blocks.",
    ),
    AllowedOccurrence(
        "private repo wording",
        re.compile(r"scripts/scan_safety\.py"),
        re.compile(r".*"),
        "The scanner must define the exact private repo wording it blocks.",
    ),
    AllowedOccurrence(
        "old tap name",
        re.compile(r"scripts/scan_safety\.py"),
        re.compile(r".*"),
        "The scanner must define the exact old tap name it blocks.",
    ),
    AllowedOccurrence(
        "private prompt wording",
        re.compile(r"scripts/scan_safety\.py"),
        re.compile(r".*"),
        "The scanner must define the exact private prompt wording it blocks.",
    ),
]

# Files that are allowed to contain references (e.g. this script, and git history/lockfiles)
ALLOWLIST_FILES = {
    "uv.lock",
}


def get_tracked_files() -> list[str]:
    """Get list of tracked files via git ls-files."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
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
    """Return whether a banned match has a documented compatibility exception."""
    return any(
        item.pattern_name == pattern_name
        and item.path_regex.fullmatch(file_str)
        and item.line_regex.search(line)
        for item in ALLOWLIST
    )


def scan_file(file_str: str, file_path: Path) -> list[tuple[int, str, str]]:
    """Scan a single file. Returns list of (line_num, pattern_name, line_content)."""
    violations = []
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
    tracked_files = get_tracked_files()
    total_violations = 0

    print(f"Scanning {len(tracked_files)} tracked files for safety guardrails...")

    for file_str in tracked_files:
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
