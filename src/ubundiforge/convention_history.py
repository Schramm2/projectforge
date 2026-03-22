"""Git-backed history helpers for convention admin flows."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitHistoryResult:
    """Normalized git history output for a conventions target."""

    target: str
    available: bool
    entries: tuple[str, ...] = ()
    message: str = ""


def _git_workdir(root: Path) -> Path:
    resolved_root = root.resolve()
    if resolved_root.name == "conventions":
        return resolved_root.parent
    return resolved_root


def _git_target(target: str) -> str:
    cleaned = target.strip().strip("/")
    if not cleaned:
        return "conventions"
    if cleaned.startswith("conventions/"):
        return cleaned
    return f"conventions/{cleaned}"


def load_history(root: Path, target: str, *, limit: int = 10) -> GitHistoryResult:
    """Return recent git history for a conventions path without requiring interactivity."""

    git_target = _git_target(target)
    command = ["git", "log", "--oneline", "--", git_target]

    try:
        completed = subprocess.run(
            command,
            cwd=_git_workdir(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return GitHistoryResult(
            target=git_target,
            available=False,
            message="Git history is unavailable because git is not installed.",
        )
    except OSError as exc:
        return GitHistoryResult(
            target=git_target,
            available=False,
            message=f"Git history is unavailable: {exc}",
        )

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        message = stderr or "Git history is unavailable for this conventions target."
        return GitHistoryResult(
            target=git_target,
            available=False,
            message=message,
        )

    entries = tuple(line.strip() for line in completed.stdout.splitlines() if line.strip())[:limit]
    if not entries:
        return GitHistoryResult(
            target=git_target,
            available=False,
            message="No git history found for this conventions target.",
        )

    return GitHistoryResult(target=git_target, available=True, entries=entries)
