"""Tests for per-subagent quality signal recording."""

import json
from pathlib import Path

from ubundiforge.agent_quality import append_agent_quality_signal


def test_writes_signal_to_jsonl(tmp_path: Path) -> None:
    log = tmp_path / "quality.jsonl"
    append_agent_quality_signal(
        log_path=log,
        phase="scaffold",
        backend="claude",
        task_id="task-1",
        task_description="Create main app",
        success=True,
        duration=1.5,
    )
    lines = log.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["type"] == "agent_task"
    assert entry["phase"] == "scaffold"
    assert entry["backend"] == "claude"
    assert entry["agent_task_id"] == "task-1"
    assert entry["agent_task_description"] == "Create main app"
    assert entry["success"] is True
    assert entry["agent_duration"] == 1.5
    assert "timestamp" in entry


def test_appends_multiple_signals(tmp_path: Path) -> None:
    log = tmp_path / "quality.jsonl"
    for i in range(3):
        append_agent_quality_signal(
            log_path=log,
            phase="scaffold",
            backend="gemini",
            task_id=f"task-{i}",
            task_description=f"Task {i}",
            success=True,
            duration=float(i),
        )
    lines = log.read_text().splitlines()
    assert len(lines) == 3
    for i, line in enumerate(lines):
        entry = json.loads(line)
        assert entry["agent_task_id"] == f"task-{i}"


def test_records_failure(tmp_path: Path) -> None:
    log = tmp_path / "quality.jsonl"
    append_agent_quality_signal(
        log_path=log,
        phase="test",
        backend="codex",
        task_id="failing-task",
        task_description="This task fails",
        success=False,
        duration=0.3,
    )
    entry = json.loads(log.read_text().strip())
    assert entry["success"] is False
    assert entry["agent_task_id"] == "failing-task"


def test_creates_parent_directory(tmp_path: Path) -> None:
    log = tmp_path / "deeply" / "nested" / "quality.jsonl"
    assert not log.parent.exists()
    append_agent_quality_signal(
        log_path=log,
        phase="scaffold",
        backend="claude",
        task_id="task-1",
        task_description="Test directory creation",
        success=True,
        duration=0.1,
    )
    assert log.exists()
    entry = json.loads(log.read_text().strip())
    assert entry["type"] == "agent_task"
