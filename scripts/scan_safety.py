#!/usr/bin/env python3
"""Scan tracked files for forbidden company/personal identifiers."""

import subprocess
import sys
from pathlib import Path

BANNED_TERMS = [
    "Ubundi",
    "ubundi.co.za",
    "matthew-schramm",
    "/Users/matthew-schramm",
    "docs/internal",
    "existing Ubundi repos",
    "homebrew-tap",
    "matthewubundi",
]

# Files that are allowed to contain references (e.g. this script, and git history/lockfiles)
ALLOWLIST_FILES = {
    "scripts/scan_safety.py",
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


def scan_file(file_path: Path) -> list[tuple[int, str, str]]:
    """Scan a single file for banned terms. Returns list of (line_num, term, line_content)."""
    violations = []
    try:
        # Read text, ignoring binary decoding errors
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for line_num, line in enumerate(content.splitlines(), 1):
            for term in BANNED_TERMS:
                if term in line:
                    violations.append((line_num, term, line.strip()))
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

        violations = scan_file(file_path)
        if violations:
            total_violations += len(violations)
            print(f"\n[VIOLATION] in {file_str}:")
            for line_num, term, line_content in violations:
                print(f"  Line {line_num}: found banned term '{term}' -> \"{line_content}\"")

    if total_violations > 0:
        print(f"\nScan failed. Found {total_violations} safety violations.")
        sys.exit(1)

    print("Success: No safety violations found.")
    sys.exit(0)


if __name__ == "__main__":
    main()
