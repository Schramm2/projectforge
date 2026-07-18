"""Per-subagent quality signal recording for multi-agent orchestration."""

import json
from datetime import UTC, datetime
from pathlib import Path


def append_agent_quality_signal(
    *,
    log_path: Path,
    phase: str,
    backend: str,
    task_id: str,
    task_description: str,
    success: bool,
    duration: float,
) -> None:
    """Append a per-subagent quality signal to the JSONL log."""
    entry = {
        "type": "agent_task",
        "phase": phase,
        "backend": backend,
        "agent_task_id": task_id,
        "agent_task_description": task_description,
        "success": success,
        "agent_duration": duration,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
