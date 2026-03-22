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


_MIN_DATA_POINTS = 8
_EMA_ALPHA = 0.2


def compute_backend_scores(
    signals: list[dict],
    *,
    stack: str,
    phase: str,
) -> dict[str, float]:
    """Compute weighted success scores per backend using exponential moving average.

    Returns:
        Dict mapping backend name to a score between 0.0 and 1.0.
        Empty dict if insufficient data (<8 points per backend).
    """
    by_backend: dict[str, list[dict]] = {}
    for s in signals:
        if s.get("stack") == stack and s.get("phase") == phase:
            backend = s.get("backend", "")
            by_backend.setdefault(backend, []).append(s)

    scores: dict[str, float] = {}
    for backend, entries in by_backend.items():
        if len(entries) < _MIN_DATA_POINTS:
            continue
        ema = 0.0
        initialized = False
        for entry in entries:
            success = sum(1 for k in SIGNAL_KEYS if entry.get(k, False)) / len(SIGNAL_KEYS)
            if not initialized:
                ema = success
                initialized = True
            else:
                ema = _EMA_ALPHA * success + (1 - _EMA_ALPHA) * ema
        scores[backend] = ema

    return scores
