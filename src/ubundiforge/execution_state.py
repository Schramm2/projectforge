"""Privacy-safe phase progress evidence for resumable scaffolds."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path


class ProgressContractError(ValueError):
    """Raised when resume evidence is missing, invalid, or belongs to another run."""


def _progress_path(project_dir: Path) -> Path:
    return project_dir / ".forge" / "progress.json"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _phase_contract(phase: str, backend: str, prompt: str) -> dict:
    digest = hashlib.sha256(prompt.encode()).hexdigest()
    return {
        "phase": phase,
        "backend": backend,
        "prompt_sha256": f"sha256:{digest}",
    }


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temp_path, 0o600)
    temp_path.replace(path)


def _read_progress(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ProgressContractError(
            "Resume requires valid .forge/progress.json progress evidence."
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ProgressContractError("Resume progress evidence uses an unsupported schema.")
    return payload


def initialize_progress(
    project_dir: Path,
    *,
    name: str,
    stack: str,
    approval_mode: str,
    phase_prompts: list[tuple[str, str, str]],
    resume: bool,
) -> dict:
    """Create progress evidence or validate and prepare it for a safe resume."""
    path = _progress_path(project_dir)
    contract = [_phase_contract(phase, backend, prompt) for phase, backend, prompt in phase_prompts]

    if not resume:
        timestamp = _now()
        payload = {
            "schema_version": 1,
            "name": name,
            "stack": stack,
            "approval_mode": approval_mode,
            "status": "running",
            "resume_count": 0,
            "created_at": timestamp,
            "updated_at": timestamp,
            "phases": [
                {
                    **item,
                    "status": "pending",
                    "attempts": 0,
                    "duration_seconds": 0.0,
                    "exit_code": None,
                    "last_failure_category": None,
                }
                for item in contract
            ],
        }
        _atomic_write(path, payload)
        return payload

    if not path.is_file():
        raise ProgressContractError(
            "Resume requires existing .forge/progress.json progress evidence."
        )
    payload = _read_progress(path)
    recorded_contract = [
        {key: item.get(key) for key in ("phase", "backend", "prompt_sha256")}
        for item in payload.get("phases", [])
        if isinstance(item, dict)
    ]
    if (
        payload.get("name") != name
        or payload.get("stack") != stack
        or payload.get("approval_mode") != approval_mode
        or recorded_contract != contract
    ):
        raise ProgressContractError(
            "Resume contract differs from the recorded name, stack, routing, prompt hashes, "
            "or approval mode. Start a new target or repeat the original options."
        )

    for phase in payload["phases"]:
        if phase.get("status") != "completed":
            phase["status"] = "pending"
            phase["exit_code"] = None
    payload["status"] = "running"
    payload["resume_count"] = int(payload.get("resume_count", 0)) + 1
    payload["updated_at"] = _now()
    _atomic_write(path, payload)
    return payload


def mark_phase(
    project_dir: Path,
    phase_name: str,
    *,
    status: str,
    duration_seconds: float = 0.0,
    exit_code: int | None = None,
    failure_category: str | None = None,
) -> dict:
    """Persist a phase transition without storing prompts or provider output."""
    if status not in {"running", "completed", "failed"}:
        raise ValueError(f"Unsupported phase status: {status}")
    path = _progress_path(project_dir)
    payload = _read_progress(path)
    phase = next(
        (item for item in payload.get("phases", []) if item.get("phase") == phase_name),
        None,
    )
    if phase is None:
        raise ProgressContractError(f"Phase {phase_name!r} is not in the progress contract.")

    if status == "running" or int(phase.get("attempts", 0)) == 0:
        phase["attempts"] = int(phase.get("attempts", 0)) + 1
    phase["status"] = status
    phase["duration_seconds"] = round(float(duration_seconds), 3)
    phase["exit_code"] = exit_code
    if failure_category:
        phase["last_failure_category"] = failure_category
    payload["status"] = "failed" if status == "failed" else "running"
    if all(item.get("status") == "completed" for item in payload.get("phases", [])):
        payload["status"] = "completed"
    payload["updated_at"] = _now()
    _atomic_write(path, payload)
    return payload
