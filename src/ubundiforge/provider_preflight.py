"""Explicit, short-lived readiness proofs for providers without a status API."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ubundiforge.conventions import FORGE_DIR
from ubundiforge.failure_taxonomy import classify_provider_failure

PREFLIGHT_PATH = FORGE_DIR / "provider-preflight.json"
PREFLIGHT_SCHEMA_VERSION = 1
PREFLIGHT_MAX_AGE = timedelta(hours=24)
GEMINI_READY_SENTINEL = "PROJECTFORGE_READY"
_GEMINI_PREFLIGHT_PROMPT = (
    f"Reply with exactly {GEMINI_READY_SENTINEL}. Do not call tools, read files, or write files."
)


@dataclass(frozen=True)
class PreflightResult:
    """Credential-free result from an explicit provider model preflight."""

    success: bool
    detail: str
    category: str | None = None


def _read_payload() -> dict:
    try:
        payload = json.loads(PREFLIGHT_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"schema_version": PREFLIGHT_SCHEMA_VERSION, "providers": {}}
    if not isinstance(payload, dict) or payload.get("schema_version") != PREFLIGHT_SCHEMA_VERSION:
        return {"schema_version": PREFLIGHT_SCHEMA_VERSION, "providers": {}}
    providers = payload.get("providers")
    if not isinstance(providers, dict):
        return {"schema_version": PREFLIGHT_SCHEMA_VERSION, "providers": {}}
    return {"schema_version": PREFLIGHT_SCHEMA_VERSION, "providers": providers}


def load_valid_preflight(backend: str, *, version: str) -> bool:
    """Return whether a version-matched provider proof is still fresh."""
    record = _read_payload()["providers"].get(backend)
    if not isinstance(record, dict) or record.get("version") != version:
        return False
    verified_at = record.get("verified_at")
    if not isinstance(verified_at, str):
        return False
    try:
        timestamp = datetime.fromisoformat(verified_at)
    except ValueError:
        return False
    if timestamp.tzinfo is None:
        return False
    age = datetime.now(UTC) - timestamp.astimezone(UTC)
    return timedelta(0) <= age <= PREFLIGHT_MAX_AGE


def _write_proof(backend: str, *, version: str) -> None:
    payload = _read_payload()
    payload["providers"][backend] = {
        "version": version,
        "verified_at": datetime.now(UTC).isoformat(),
    }
    PREFLIGHT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".provider-preflight-", dir=PREFLIGHT_PATH.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        temp_path.chmod(0o600)
        temp_path.replace(PREFLIGHT_PATH)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _run(command: list[str], *, cwd: Path | None = None, timeout: int = 90):
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_gemini_preflight() -> PreflightResult:
    """Make one consented read-only Gemini call and persist only bounded readiness evidence."""
    if shutil.which("gemini") is None:
        return PreflightResult(False, "Gemini CLI is not installed.", "missing_binary")

    try:
        version_result = _run(["gemini", "--version"], timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return PreflightResult(False, "Gemini version check failed.", "missing_binary")
    if version_result.returncode != 0:
        return PreflightResult(False, "Gemini version check failed.", "unknown")
    version_output = (version_result.stdout or version_result.stderr or "").strip()
    version = version_output.splitlines()[0][:160] if version_output else "unknown"

    command = [
        "gemini",
        "-p",
        _GEMINI_PREFLIGHT_PROMPT,
        "--approval-mode",
        "plan",
        "--sandbox",
        "--output-format",
        "json",
    ]
    try:
        with tempfile.TemporaryDirectory(prefix="projectforge-preflight-") as workspace:
            result = _run(command, cwd=Path(workspace))
    except subprocess.TimeoutExpired:
        return PreflightResult(False, "Gemini readiness preflight timed out.", "timeout")
    except (FileNotFoundError, OSError):
        return PreflightResult(False, "Gemini CLI could not be started.", "missing_binary")

    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if result.returncode == 0 and GEMINI_READY_SENTINEL in output:
        _write_proof("gemini", version=version)
        return PreflightResult(True, "Gemini readiness verified for 24 hours.")

    failure = classify_provider_failure(output, returncode=result.returncode)
    return PreflightResult(False, failure.summary, failure.category)
