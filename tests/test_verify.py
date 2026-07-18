"""Tests for the post-scaffold verification module."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from ubundiforge.verify import (
    CheckResult,
    VerifyReport,
    _check_health,
    _extract_port,
    _health_settings,
    _install_deps,
    _run_check,
    print_report,
    verify_scaffold,
    write_verification_report,
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


@patch("ubundiforge.verify.time.sleep", return_value=None)
@patch("ubundiforge.verify.urlopen")
@patch("ubundiforge.verify.subprocess.Popen")
def test_health_result_records_configured_endpoint_and_command(
    mock_popen, mock_urlopen, _mock_sleep, tmp_path
):
    process = MagicMock()
    process.poll.return_value = None
    mock_popen.return_value = process
    mock_urlopen.return_value = MagicMock(status=200)

    result = _check_health(tmp_path, "uvicorn app:app --port 8123", endpoints=("/status",))

    assert result.passed is True
    assert result.command == "uvicorn app:app --port 8123"
    assert result.cwd == str(tmp_path)
    assert result.timeout_seconds == 12
    assert result.request_timeout_seconds == 3
    assert result.attempted_endpoints == ("http://localhost:8123/status",)


def test_health_settings_uses_safe_generated_project_metadata(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "atlas"
version = "0.1.0"

[tool.forge.verification]
health_endpoints = ["/healthz", "/readyz"]
health_startup_timeout = 20
health_request_timeout = 4
"""
    )

    assert _health_settings(tmp_path) == (("/healthz", "/readyz"), 20, 4)


@pytest.mark.parametrize(
    "toml_body",
    [
        'health_endpoints = ["http://example.com/steal"]',
        'health_endpoints = ["/health"]\nhealth_startup_timeout = 0',
        'health_endpoints = ["/health"]\nhealth_request_timeout = 31',
    ],
)
def test_health_settings_rejects_unsafe_generated_metadata(tmp_path, toml_body):
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "atlas"\nversion = "0.1.0"\n\n[tool.forge.verification]\n{toml_body}\n'
    )

    assert _health_settings(tmp_path) == (("/health", "/ready"), 12, 3)


# --- _run_check ---


@patch("ubundiforge.verify.subprocess.run")
def test_run_check_pass(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    result = _run_check("lint", "uv run ruff check .", tmp_path)
    assert result.passed is True
    assert result.name == "lint"
    assert result.command == "uv run ruff check ."
    assert result.cwd == str(tmp_path)
    assert result.timeout_seconds == 60
    assert result.exit_code == 0


@patch("ubundiforge.verify.subprocess.run")
def test_run_check_does_not_leak_parent_virtual_environment(mock_run, monkeypatch, tmp_path):
    monkeypatch.setenv("VIRTUAL_ENV", "/private/parent/.venv")
    mock_run.return_value = MagicMock(returncode=0)

    _run_check("lint", "uv run ruff check .", tmp_path)

    assert "VIRTUAL_ENV" not in mock_run.call_args.kwargs["env"]


@patch("ubundiforge.verify.subprocess.run")
def test_run_check_fail(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=1, stderr="some error output")
    result = _run_check("lint", "uv run ruff check .", tmp_path)
    assert result.passed is False
    assert "some error output" in result.detail
    assert result.exit_code == 1
    assert "uv run ruff check ." in result.remediation


@patch("ubundiforge.verify.subprocess.run")
def test_run_check_timeout(mock_run, tmp_path):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=60)
    result = _run_check("test", "uv run pytest tests/", tmp_path)
    assert result.passed is False
    assert "timed out" in result.detail
    assert result.exit_code is None
    assert result.timeout_seconds == 60


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


@patch("ubundiforge.verify._check_health")
@patch("ubundiforge.verify._run_check")
def test_python_verification_uses_generated_project_metadata(mock_check, mock_health, tmp_path):
    """Regression: the showcase layout must not inherit stale stack command assumptions."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "showcase"
version = "0.1.0"

[project.optional-dependencies]
dev = ["pytest", "ruff", "mypy"]

[tool.pytest.ini_options]
testpaths = ["tests"]
"""
    )
    mock_check.return_value = CheckResult(name="check", passed=True)
    mock_health.return_value = CheckResult(name="health", passed=True)

    report = verify_scaffold("python-cli", tmp_path)

    commands = [call.args[1] for call in mock_check.call_args_list]
    assert commands[0] == "uv sync --extra dev"
    assert "uv run pytest -q" in commands
    assert report.all_passed is True


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


def test_write_verification_report_persists_reproducible_command_metadata(tmp_path):
    report = VerifyReport(
        checks=[
            CheckResult(
                name="test",
                passed=False,
                detail="one test failed",
                command="uv run pytest -q",
                cwd=str(tmp_path),
                timeout_seconds=30,
                exit_code=1,
                remediation="Run the test command and inspect output.",
                duration_seconds=1.25,
            )
        ]
    )

    output_path = write_verification_report(report, tmp_path)
    payload = __import__("json").loads(output_path.read_text())

    assert payload["all_passed"] is False
    assert payload["checks"][0]["cwd"] == "."
    assert payload["checks"][0]["command"] == "uv run pytest -q"
    assert payload["checks"][0]["exit_code"] == 1
    assert payload["checks"][0]["request_timeout_seconds"] is None


def test_write_verification_report_defensively_redacts_all_text_fields(tmp_path):
    token = "ghp_abcdefghijklmnopqrstuvwxyz1234567890"
    report = VerifyReport(
        checks=[
            CheckResult(
                name="test",
                passed=False,
                detail=f"failed with {token} in {tmp_path}",
                command=f"tool --token {token}",
                cwd=str(tmp_path),
                remediation=f"run in {tmp_path} then remove {token}",
                attempted_endpoints=(f"http://localhost:8000/{token}",),
            )
        ]
    )

    output_path = write_verification_report(report, tmp_path)
    raw = output_path.read_text()

    assert token not in raw
    assert str(tmp_path) not in raw
    assert "REDACTED" in raw
