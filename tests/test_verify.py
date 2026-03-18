"""Tests for the post-scaffold verification module."""

import subprocess
from unittest.mock import MagicMock, patch

from rich.console import Console

from ubundiforge.verify import (
    CheckResult,
    VerifyReport,
    _extract_port,
    _install_deps,
    _run_check,
    print_report,
    verify_scaffold,
)

# --- CheckResult / VerifyReport ---


def test_check_result_defaults():
    r = CheckResult(name="lint", passed=True)
    assert r.name == "lint"
    assert r.passed is True
    assert r.detail == ""
    assert r.skipped is False


def test_verify_report_all_passed():
    report = VerifyReport(
        checks=[
            CheckResult(name="install", passed=True),
            CheckResult(name="lint", passed=True),
        ]
    )
    assert report.all_passed is True


def test_verify_report_with_failure():
    report = VerifyReport(
        checks=[
            CheckResult(name="install", passed=True),
            CheckResult(name="lint", passed=False, detail="ruff error"),
        ]
    )
    assert report.all_passed is False


def test_verify_report_skipped_dont_count_as_failure():
    report = VerifyReport(
        checks=[
            CheckResult(name="install", passed=True),
            CheckResult(name="typecheck", passed=False, skipped=True, detail="deps not installed"),
        ]
    )
    assert report.all_passed is True


def test_verify_report_empty():
    report = VerifyReport()
    assert report.all_passed is True


# --- _extract_port ---


def test_extract_port_from_uvicorn():
    assert _extract_port("uvicorn api.app:app --host 0.0.0.0 --port 8000") == 8000


def test_extract_port_custom():
    assert _extract_port("uvicorn api.app:app --port 3000") == 3000


def test_extract_port_default():
    assert _extract_port("uvicorn api.app:app") == 8000


# --- _run_check ---


@patch("ubundiforge.verify.subprocess.run")
def test_run_check_pass(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    result = _run_check("lint", "uv run ruff check .", tmp_path)
    assert result.passed is True
    assert result.name == "lint"


@patch("ubundiforge.verify.subprocess.run")
def test_run_check_fail(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=1, stderr="some error output")
    result = _run_check("lint", "uv run ruff check .", tmp_path)
    assert result.passed is False
    assert "some error output" in result.detail


@patch("ubundiforge.verify.subprocess.run")
def test_run_check_timeout(mock_run, tmp_path):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=30)
    result = _run_check("test", "uv run pytest tests/", tmp_path)
    assert result.passed is False
    assert "timed out" in result.detail


# --- _install_deps ---


@patch("ubundiforge.verify._run_check")
def test_install_deps_python_stack(mock_check, tmp_path):
    mock_check.return_value = CheckResult(name="install", passed=True)
    result = _install_deps("fastapi", tmp_path)
    assert result.passed is True
    mock_check.assert_called_once_with("install", "uv sync", tmp_path, timeout=60)


@patch("ubundiforge.verify._run_check")
def test_install_deps_node_stack(mock_check, tmp_path):
    mock_check.return_value = CheckResult(name="install", passed=True)
    result = _install_deps("nextjs", tmp_path)
    assert result.passed is True
    mock_check.assert_called_once_with("install", "npm install", tmp_path, timeout=60)


@patch("ubundiforge.verify._run_check")
def test_install_deps_fullstack(mock_check, tmp_path):
    # Create frontend dir so npm install runs
    (tmp_path / "frontend").mkdir()
    mock_check.return_value = CheckResult(name="install", passed=True)
    result = _install_deps("both", tmp_path)
    assert result.passed is True
    assert mock_check.call_count == 2


def test_install_deps_unknown_stack(tmp_path):
    result = _install_deps("unknown", tmp_path)
    assert result.passed is False
    assert "unknown stack" in result.detail


# --- verify_scaffold ---


@patch("ubundiforge.verify._check_health")
@patch("ubundiforge.verify._run_check")
@patch("ubundiforge.verify._install_deps")
def test_verify_scaffold_all_pass(mock_install, mock_check, mock_health, tmp_path):
    mock_install.return_value = CheckResult(name="install", passed=True)
    mock_check.return_value = CheckResult(name="check", passed=True)
    mock_health.return_value = CheckResult(name="health", passed=True)

    report = verify_scaffold("fastapi", tmp_path)
    assert report.all_passed is True
    # install + lint + typecheck + test + health = 5
    assert len(report.checks) == 5


@patch("ubundiforge.verify._install_deps")
def test_verify_scaffold_install_failure_skips_rest(mock_install, tmp_path):
    mock_install.return_value = CheckResult(name="install", passed=False, detail="failed")

    report = verify_scaffold("fastapi", tmp_path)
    assert report.all_passed is False
    # install (failed) + lint, typecheck, test, health (all skipped) = 5
    assert len(report.checks) == 5
    assert report.checks[0].passed is False
    assert all(c.skipped for c in report.checks[1:])


def test_verify_scaffold_unknown_stack(tmp_path):
    report = verify_scaffold("nonexistent", tmp_path)
    assert report.all_passed is False


@patch("ubundiforge.verify._run_check")
@patch("ubundiforge.verify._install_deps")
def test_verify_scaffold_no_health_for_cli(mock_install, mock_check, tmp_path):
    """python-cli has no run command, so health check should not appear."""
    mock_install.return_value = CheckResult(name="install", passed=True)
    mock_check.return_value = CheckResult(name="check", passed=True)

    report = verify_scaffold("python-cli", tmp_path)
    assert report.all_passed is True
    check_names = [c.name for c in report.checks]
    assert "health" not in check_names


# --- print_report ---


def test_print_report_renders():
    report = VerifyReport(
        checks=[
            CheckResult(name="install", passed=True),
            CheckResult(name="lint", passed=False, detail="ruff error"),
            CheckResult(name="typecheck", passed=False, skipped=True, detail="deps not installed"),
        ]
    )
    console = Console(file=MagicMock(), force_terminal=True, width=120)
    # Should not raise
    print_report(report, console)
