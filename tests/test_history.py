"""Tests for local history repair."""

import json
from pathlib import Path

from projectforge.history import repair_history


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.write_text("".join(json.dumps(entry) + "\n" for entry in entries))


def test_repair_history_quarantines_pytest_paths_and_known_fixtures(tmp_path: Path) -> None:
    scaffold_path = tmp_path / "scaffold.log"
    quality_path = tmp_path / "quality.jsonl"
    real_scaffold = {"name": "atlas", "directory": "atlas", "stack": "fastapi"}
    pytest_scaffold = {
        "name": "temp-project",
        "directory": "/tmp/pytest-of-matthew/pytest-7/temp-project",
    }
    fixture_scaffold = {
        "name": "mocked-flow",
        "directory": "mocked-flow",
        "stack": "fastapi",
        "timestamp": "2026-07-18T12:00:02+00:00",
    }
    real_quality = {
        "type": "scaffold_phase",
        "stack": "fastapi",
        "phase": "verify",
        "backend": "claude",
        "lint_clean": True,
        "tests_passed": True,
        "typecheck_clean": True,
        "health_ok": True,
        "built": True,
    }
    fixture_quality = {
        "type": "agent_task",
        "agent_task_description": "Task A",
        "agent_duration": 0.1,
    }
    correlated_fixture_quality = {
        "stack": "fastapi",
        "phase": "architecture",
        "timestamp": "2026-07-18T12:00:00+00:00",
        "lint_clean": False,
        "tests_passed": False,
        "typecheck_clean": False,
        "health_ok": False,
        "built": False,
    }
    _write_jsonl(scaffold_path, [real_scaffold, pytest_scaffold, fixture_scaffold])
    _write_jsonl(
        quality_path,
        [real_quality, fixture_quality, correlated_fixture_quality],
    )

    result = repair_history(
        scaffold_log_path=scaffold_path,
        quality_log_path=quality_path,
    )

    assert result.scaffold_entries == 2
    assert result.quality_entries == 2
    assert result.quarantine_dir is not None
    assert json.loads(scaffold_path.read_text()) == real_scaffold
    assert json.loads(quality_path.read_text()) == real_quality
    assert (result.quarantine_dir / "scaffold.log").exists()
    assert (result.quarantine_dir / "quality.jsonl").exists()


def test_repair_history_preserves_unrecognized_and_malformed_entries(tmp_path: Path) -> None:
    scaffold_path = tmp_path / "scaffold.log"
    quality_path = tmp_path / "quality.jsonl"
    scaffold_path.write_text('{"name":"real","directory":"real"}\nnot-json\n')
    quality_path.write_text('{"type":"agent_task","agent_task_description":"Real task"}\n')

    result = repair_history(
        scaffold_log_path=scaffold_path,
        quality_log_path=quality_path,
    )

    assert result.total_entries == 0
    assert result.quarantine_dir is None
    assert "not-json" in scaffold_path.read_text()
