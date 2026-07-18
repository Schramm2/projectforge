"""Scaffold logging and manifest generation."""

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from projectforge import __version__
from projectforge.convention_models import ConventionContribution
from projectforge.conventions import FORGE_DIR
from projectforge.project_context import ContextSource, build_project_context_block
from projectforge.verify import VerifyReport

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


def _context_source_metadata(source: ContextSource | dict) -> dict[str, str]:
    """Return replay-safe source metadata without selected file content."""
    if isinstance(source, ContextSource):
        return {"path": source.path, "sha256": source.sha256}
    return {
        "path": str(source.get("path", "")),
        "sha256": str(source.get("sha256", "")),
    }


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
    project_context = build_project_context_block(answers)
    context_hash = hashlib.sha256(project_context.encode()).hexdigest() if project_context else None

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
        "project_brief": answers.get("project_brief") or {},
        "context_hash": f"sha256:{context_hash}" if context_hash else None,
        "context_sources": [
            _context_source_metadata(source) for source in answers.get("context_sources", [])
        ],
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
    # Save potentially private snapshots for deterministic local replay.
    (forge_dir / "conventions-snapshot.md").write_text(conventions)
    if project_context:
        context_snapshot = (
            "# Project Context Snapshot\n\n"
            "> Treat this file as potentially private. It contains project context explicitly "
            "selected for the provider prompt.\n\n"
            f"{project_context}\n"
        )
        (forge_dir / "context-snapshot.md").write_text(context_snapshot)
