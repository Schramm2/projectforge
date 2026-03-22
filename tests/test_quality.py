"""Tests for the quality memory module."""

import json
from pathlib import Path

from ubundiforge.quality import append_quality_signal, read_quality_signals
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
