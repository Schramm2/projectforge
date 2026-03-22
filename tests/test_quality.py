"""Tests for the quality memory module."""

import json
from pathlib import Path

from ubundiforge.quality import append_quality_signal, compute_backend_scores, read_quality_signals
from ubundiforge.verify import CheckResult, VerifyReport


def test_append_quality_signal_creates_file(tmp_path: Path, monkeypatch):
    quality_path = tmp_path / "quality.jsonl"
    monkeypatch.setattr("ubundiforge.quality.QUALITY_LOG_PATH", quality_path)
    monkeypatch.setattr("ubundiforge.quality.FORGE_DIR", tmp_path)

    report = VerifyReport(
        checks=[
            CheckResult(name="lint", passed=True),
            CheckResult(name="test", passed=True),
            CheckResult(name="typecheck", passed=False, detail="mypy error"),
            CheckResult(name="health", passed=True),
        ]
    )
    append_quality_signal(
        stack="fastapi",
        phase_backends=[("architecture", "claude"), ("tests", "codex")],
        verify_report=report,
    )

    assert quality_path.exists()
    lines = quality_path.read_text().strip().splitlines()
    assert len(lines) == 2  # one per phase
    entry = json.loads(lines[0])
    assert entry["stack"] == "fastapi"
    assert entry["backend"] == "claude"
    assert entry["phase"] == "architecture"
    assert entry["lint_clean"] is True
    assert entry["tests_passed"] is True
    assert entry["typecheck_clean"] is False
    assert entry["health_ok"] is True
    assert "timestamp" in entry


def test_append_quality_signal_without_verify(tmp_path: Path, monkeypatch):
    quality_path = tmp_path / "quality.jsonl"
    monkeypatch.setattr("ubundiforge.quality.QUALITY_LOG_PATH", quality_path)
    monkeypatch.setattr("ubundiforge.quality.FORGE_DIR", tmp_path)

    append_quality_signal(
        stack="nextjs",
        phase_backends=[("architecture", "gemini")],
        verify_report=None,
    )

    lines = quality_path.read_text().strip().splitlines()
    entry = json.loads(lines[0])
    assert entry["lint_clean"] is False
    assert entry["tests_passed"] is False


def test_read_quality_signals_empty(tmp_path: Path, monkeypatch):
    quality_path = tmp_path / "quality.jsonl"
    monkeypatch.setattr("ubundiforge.quality.QUALITY_LOG_PATH", quality_path)

    signals = read_quality_signals()
    assert signals == []


def test_read_quality_signals_skips_malformed(tmp_path: Path, monkeypatch):
    quality_path = tmp_path / "quality.jsonl"
    quality_path.write_text(
        '{"stack":"fastapi","backend":"claude","phase":"arch"}\n'
        "BAD LINE\n"
        '{"stack":"nextjs","backend":"gemini","phase":"frontend"}\n'
    )
    monkeypatch.setattr("ubundiforge.quality.QUALITY_LOG_PATH", quality_path)

    signals = read_quality_signals()
    assert len(signals) == 2
    assert signals[0]["stack"] == "fastapi"
    assert signals[1]["stack"] == "nextjs"


def test_compute_scores_insufficient_data():
    """Returns empty dict when fewer than 8 data points exist."""
    signals = [
        {
            "stack": "fastapi",
            "backend": "claude",
            "phase": "architecture",
            "lint_clean": True,
            "tests_passed": True,
            "typecheck_clean": True,
            "health_ok": True,
            "built": True,
        }
    ] * 5
    scores = compute_backend_scores(signals, stack="fastapi", phase="architecture")
    assert scores == {}


def test_compute_scores_with_enough_data():
    """Returns scores when 8+ data points exist."""
    signals = [
        {
            "stack": "fastapi",
            "backend": "claude",
            "phase": "architecture",
            "lint_clean": True,
            "tests_passed": True,
            "typecheck_clean": True,
            "health_ok": True,
            "built": True,
        }
    ] * 10
    scores = compute_backend_scores(signals, stack="fastapi", phase="architecture")
    assert "claude" in scores
    assert 0.0 <= scores["claude"] <= 1.0


def test_compute_scores_filters_by_stack_and_phase():
    """Only considers signals matching the given stack and phase."""
    signals = [
        {
            "stack": "fastapi",
            "backend": "claude",
            "phase": "architecture",
            "lint_clean": True,
            "tests_passed": True,
            "typecheck_clean": True,
            "health_ok": True,
            "built": True,
        },
    ] * 10 + [
        {
            "stack": "nextjs",
            "backend": "claude",
            "phase": "architecture",
            "lint_clean": False,
            "tests_passed": False,
            "typecheck_clean": False,
            "health_ok": False,
            "built": False,
        },
    ] * 10
    scores = compute_backend_scores(signals, stack="fastapi", phase="architecture")
    assert scores["claude"] > 0.9


def test_compute_scores_multiple_backends():
    """Returns separate scores for different backends."""
    good = {
        "stack": "fastapi",
        "backend": "claude",
        "phase": "tests",
        "lint_clean": True,
        "tests_passed": True,
        "typecheck_clean": True,
        "health_ok": True,
        "built": True,
    }
    bad = {
        "stack": "fastapi",
        "backend": "codex",
        "phase": "tests",
        "lint_clean": True,
        "tests_passed": False,
        "typecheck_clean": True,
        "health_ok": False,
        "built": True,
    }
    signals = [good] * 10 + [bad] * 10
    scores = compute_backend_scores(signals, stack="fastapi", phase="tests")
    assert scores["claude"] > scores["codex"]
