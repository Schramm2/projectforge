"""Local history hygiene and one-time synthetic test-data repair."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ubundiforge.quality import QUALITY_LOG_PATH
from ubundiforge.scaffold_log import SCAFFOLD_LOG_PATH

_PYTEST_PATH_RE = re.compile(
    r"(?:^|[/\\])(?:pytest-of-[^/\\]+|pytest-current|pytest-\d+)(?:[/\\]|$)",
    re.IGNORECASE,
)
_KNOWN_SCAFFOLD_FIXTURES = {"mocked-flow", "guided-first-run"}
_KNOWN_AGENT_TASK_RE = re.compile(r"^Task [A-Z]$")


@dataclass(frozen=True)
class HistoryRepairResult:
    """Counts and quarantine location produced by a history repair."""

    scaffold_entries: int
    quality_entries: int
    quarantine_dir: Path | None

    @property
    def total_entries(self) -> int:
        return self.scaffold_entries + self.quality_entries


def _contains_pytest_path(entry: dict) -> bool:
    for key in ("directory", "project_dir", "project_path", "cwd", "workspace"):
        value = entry.get(key)
        if isinstance(value, str) and _PYTEST_PATH_RE.search(value):
            return True
    return False


def _is_synthetic_scaffold(entry: dict) -> bool:
    if _contains_pytest_path(entry):
        return True
    name = entry.get("name")
    directory = entry.get("directory")
    return name in _KNOWN_SCAFFOLD_FIXTURES and directory == name


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _fixture_run_windows(scaffold_lines: list[str]) -> list[tuple[str, datetime]]:
    windows: list[tuple[str, datetime]] = []
    for line in scaffold_lines:
        entry = json.loads(line)
        timestamp = _parse_timestamp(entry.get("timestamp"))
        stack = entry.get("stack")
        if timestamp is not None and isinstance(stack, str):
            windows.append((stack, timestamp))
    return windows


def _is_synthetic_quality(
    entry: dict,
    fixture_runs: list[tuple[str, datetime]] | None = None,
) -> bool:
    if _contains_pytest_path(entry):
        return True
    description = entry.get("agent_task_description")
    duration = entry.get("agent_duration")
    if (
        entry.get("type") == "agent_task"
        and isinstance(description, str)
        and _KNOWN_AGENT_TASK_RE.fullmatch(description) is not None
        and duration == 0.1
    ):
        return True

    timestamp = _parse_timestamp(entry.get("timestamp"))
    stack = entry.get("stack")
    return timestamp is not None and any(
        stack == fixture_stack and abs((timestamp - fixture_time).total_seconds()) <= 5
        for fixture_stack, fixture_time in (fixture_runs or [])
    )


def _partition_jsonl(path: Path, predicate) -> tuple[list[str], list[str]]:
    if not path.exists():
        return [], []

    kept: list[str] = []
    quarantined: list[str] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            kept.append(line)
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if isinstance(entry, dict) and predicate(entry):
            quarantined.append(line)
        else:
            kept.append(line)
    return kept, quarantined


def _atomic_write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp_path = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    temp_path = Path(raw_temp_path)
    try:
        with os.fdopen(fd, "w") as handle:
            if lines:
                handle.write("\n".join(lines) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def repair_history(
    *,
    scaffold_log_path: Path | None = None,
    quality_log_path: Path | None = None,
) -> HistoryRepairResult:
    """Quarantine recognizable pytest artifacts and preserve all other history."""

    scaffold_path = scaffold_log_path or SCAFFOLD_LOG_PATH
    quality_path = quality_log_path or QUALITY_LOG_PATH
    kept_scaffolds, bad_scaffolds = _partition_jsonl(scaffold_path, _is_synthetic_scaffold)
    fixture_runs = _fixture_run_windows(bad_scaffolds)
    kept_quality, bad_quality = _partition_jsonl(
        quality_path,
        lambda entry: _is_synthetic_quality(entry, fixture_runs),
    )

    if not bad_scaffolds and not bad_quality:
        return HistoryRepairResult(0, 0, None)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    quarantine_root = scaffold_path.parent / "quarantine"
    quarantine_dir = quarantine_root / timestamp
    suffix = 1
    while quarantine_dir.exists():
        quarantine_dir = quarantine_root / f"{timestamp}-{suffix}"
        suffix += 1
    quarantine_dir.mkdir(parents=True)

    if bad_scaffolds:
        (quarantine_dir / "scaffold.log").write_text("\n".join(bad_scaffolds) + "\n")
        _atomic_write_lines(scaffold_path, kept_scaffolds)
    if bad_quality:
        (quarantine_dir / "quality.jsonl").write_text("\n".join(bad_quality) + "\n")
        _atomic_write_lines(quality_path, kept_quality)

    return HistoryRepairResult(
        scaffold_entries=len(bad_scaffolds),
        quality_entries=len(bad_quality),
        quarantine_dir=quarantine_dir,
    )
