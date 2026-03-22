"""Quality memory — tracks scaffold quality signals for backend tuning."""

import json
import logging
from datetime import UTC, datetime

from ubundiforge.conventions import FORGE_DIR
from ubundiforge.verify import VerifyReport

QUALITY_LOG_PATH = FORGE_DIR / "quality.jsonl"

logger = logging.getLogger(__name__)

SIGNAL_KEYS = ("lint_clean", "tests_passed", "typecheck_clean", "health_ok", "built")


def _extract_signals(report: VerifyReport | None) -> dict[str, bool]:
    """Extract boolean quality signals from a VerifyReport."""
    if report is None:
        return {
            "lint_clean": False,
            "tests_passed": False,
            "typecheck_clean": False,
            "health_ok": False,
            "built": False,
        }
    checks = {c.name: c.passed for c in report.checks if not c.skipped}
    return {
        "lint_clean": checks.get("lint", False),
        "tests_passed": checks.get("test", False),
        "typecheck_clean": checks.get("typecheck", False),
        "health_ok": checks.get("health", False),
        "built": checks.get("build", checks.get("install", False)),
    }


def append_quality_signal(
    *,
    stack: str,
    phase_backends: list[tuple[str, str]],
    verify_report: VerifyReport | None,
) -> None:
    """Append quality signal entries to ~/.forge/quality.jsonl (one per phase)."""
    signals = _extract_signals(verify_report)
    timestamp = datetime.now(UTC).isoformat()

    FORGE_DIR.mkdir(parents=True, exist_ok=True)
    with QUALITY_LOG_PATH.open("a") as f:
        for phase, backend in phase_backends:
            entry = {
                "stack": stack,
                "backend": backend,
                "phase": phase,
                "timestamp": timestamp,
                **signals,
            }
            f.write(json.dumps(entry) + "\n")


def read_quality_signals() -> list[dict]:
    """Read all quality signal entries. Skips malformed lines."""
    if not QUALITY_LOG_PATH.exists():
        return []
    warned = False
    entries: list[dict] = []
    for line in QUALITY_LOG_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            if not warned:
                logger.warning("Skipping malformed line in quality.jsonl")
                warned = True
    return entries
