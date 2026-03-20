"""Scaffold logging and manifest generation."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from ubundiforge import __version__
from ubundiforge.conventions import FORGE_DIR

SCAFFOLD_LOG_PATH = FORGE_DIR / "scaffold.log"


def append_scaffold_log(
    answers: dict,
    phase_backends: list[tuple[str, str]],
    project_dir: Path,
) -> None:
    """Append a JSON-lines entry to ~/.forge/scaffold.log."""
    backends_used = sorted({b for _, b in phase_backends})
    entry = {
        "name": answers.get("name", ""),
        "stack": answers.get("stack", ""),
        "backends": backends_used,
        "directory": str(project_dir),
        "demo_mode": answers.get("demo_mode", False),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    FORGE_DIR.mkdir(parents=True, exist_ok=True)
    with SCAFFOLD_LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def write_scaffold_manifest(
    answers: dict,
    phase_backends: list[tuple[str, str]],
    project_dir: Path,
    conventions: str,
    *,
    model_override: str | None = None,
    backend_models: dict[str, str] | None = None,
) -> None:
    """Write .forge/scaffold.json inside the generated project."""
    backends_used = sorted({b for _, b in phase_backends})
    conv_hash = hashlib.sha256(conventions.encode()).hexdigest()[:16]

    manifest = {
        "forge_version": __version__,
        "name": answers.get("name", ""),
        "stack": answers.get("stack", ""),
        "description": answers.get("description", ""),
        "backends": backends_used,
        "routing": [{"phase": p, "backend": b} for p, b in phase_backends],
        "model_override": model_override,
        "backend_models": backend_models or {},
        "design_template": answers.get("design_template"),
        "media_collection": answers.get("media_collection"),
        "auth_provider": answers.get("auth_provider"),
        "demo_mode": answers.get("demo_mode", False),
        "conventions_hash": f"sha256:{conv_hash}",
        "timestamp": datetime.now(UTC).isoformat(),
    }

    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True, exist_ok=True)
    (forge_dir / "scaffold.json").write_text(json.dumps(manifest, indent=2) + "\n")
