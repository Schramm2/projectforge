"""Scaffold logging and manifest generation."""

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from ubundiforge import __version__
from ubundiforge.convention_models import ConventionContribution
from ubundiforge.conventions import FORGE_DIR
from ubundiforge.verify import VerifyReport

SCAFFOLD_LOG_PATH = FORGE_DIR / "scaffold.log"


def append_scaffold_log(
    answers: dict,
    phase_backends: list[tuple[str, str]],
    project_dir: Path,
    *,
    verify_report: VerifyReport | None = None,
    verification_requested: bool = False,
    duration_seconds: float | None = None,
) -> None:
    """Append a JSON-lines entry to ~/.forge/scaffold.log."""
    backends_used = sorted({b for _, b in phase_backends})
    entry = {
        "name": answers.get("name", ""),
        "stack": answers.get("stack", ""),
        "backends": backends_used,
        "directory": project_dir.name,
        "demo_mode": answers.get("demo_mode", False),
        "verification_status": (
            "passed"
            if verify_report is not None and verify_report.all_passed
            else "failed"
            if verify_report is not None
            else "not_run"
        ),
        "verification_requested": verification_requested,
        "duration_seconds": (
            round(duration_seconds, 3)
            if duration_seconds is not None
            and math.isfinite(duration_seconds)
            and duration_seconds >= 0
            else None
        ),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    FORGE_DIR.mkdir(parents=True, exist_ok=True)
    with SCAFFOLD_LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def latest_scaffold_duration(
    stack: str,
    *,
    log_path: Path | None = None,
) -> float | None:
    """Return the newest measured duration for ``stack`` from local history."""
    path = log_path or SCAFFOLD_LOG_PATH
    if not path.exists():
        return None

    try:
        lines = path.read_text().splitlines()
    except OSError:
        return None

    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        duration = entry.get("duration_seconds") if isinstance(entry, dict) else None
        if (
            entry.get("stack") == stack
            and isinstance(duration, (int, float))
            and not isinstance(duration, bool)
            and math.isfinite(duration)
            and duration >= 0
        ):
            return float(duration)
    return None


def write_scaffold_manifest(
    answers: dict,
    phase_backends: list[tuple[str, str]],
    project_dir: Path,
    conventions: str,
    *,
    model_override: str | None = None,
    backend_models: dict[str, str] | None = None,
    approval_mode: str = "safe",
    convention_sources: tuple[ConventionContribution, ...] = (),
) -> None:
    """Write .forge/scaffold.json inside the generated project."""
    backends_used = sorted({b for _, b in phase_backends})
    conv_hash = hashlib.sha256(conventions.encode()).hexdigest()

    manifest = {
        "forge_version": __version__,
        "name": answers.get("name", ""),
        "stack": answers.get("stack", ""),
        "description": answers.get("description", ""),
        "backends": backends_used,
        "routing": [{"phase": p, "backend": b} for p, b in phase_backends],
        "model_override": model_override,
        "backend_models": backend_models or {},
        "approval_mode": approval_mode,
        "design_template": answers.get("design_template"),
        "media_collection": answers.get("media_collection"),
        "auth_provider": answers.get("auth_provider"),
        "demo_mode": answers.get("demo_mode", False),
        "conventions_hash": f"sha256:{conv_hash}",
        "convention_sources": [
            {
                "source_id": source.source_id,
                "path": source.display_path,
                "sha256": source.sha256,
            }
            for source in convention_sources
        ],
        "timestamp": datetime.now(UTC).isoformat(),
    }

    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True, exist_ok=True)
    (forge_dir / "scaffold.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # Save conventions snapshot for replay
    (forge_dir / "conventions-snapshot.md").write_text(conventions)
