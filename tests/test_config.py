"""Tests for backend readiness detection."""

from subprocess import CompletedProcess

from ubundiforge.config import BackendStatus, get_backend_status, get_usable_backends


def test_claude_status_reports_needs_login(monkeypatch):
    monkeypatch.setattr(
        "ubundiforge.config.check_backend_installed",
        lambda backend: backend == "claude",
    )
    monkeypatch.setattr(
        "ubundiforge.config._run_status_command",
        lambda cmd, timeout=5: CompletedProcess(
            args=cmd,
            returncode=1,
            stdout='{"loggedIn": false, "authMethod": "none", "apiProvider": "firstParty"}',
            stderr="",
        ),
    )

    status = get_backend_status("claude")

    assert status.installed is True
    assert status.ready is False
    assert status.login_command == "claude auth login"


def test_codex_status_reports_ready(monkeypatch):
    monkeypatch.setattr(
        "ubundiforge.config.check_backend_installed",
        lambda backend: backend == "codex",
    )
    monkeypatch.setattr(
        "ubundiforge.config._run_status_command",
        lambda cmd, timeout=5: CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="Logged in using ChatGPT",
            stderr="",
        ),
    )

    status = get_backend_status("codex")

    assert status.installed is True
    assert status.ready is True
    assert status.auth_mode == "chatgpt"


def test_gemini_status_reports_unknown_when_cli_responds(monkeypatch):
    monkeypatch.setattr(
        "ubundiforge.config.check_backend_installed",
        lambda backend: backend == "gemini",
    )
    monkeypatch.setattr(
        "ubundiforge.config._run_status_command",
        lambda cmd, timeout=5: CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="1.2.3",
            stderr="",
        ),
    )

    status = get_backend_status("gemini")

    assert status.installed is True
    assert status.ready is None
    assert "authentication" in status.detail.lower()


def test_get_usable_backends_requires_verified_readiness(monkeypatch):
    monkeypatch.setattr(
        "ubundiforge.config.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=True, ready=False),
            "gemini": BackendStatus(installed=True, ready=None),
            "codex": BackendStatus(installed=True, ready=True),
        },
    )

    assert get_usable_backends() == ["codex"]


def test_codex_nonzero_status_is_not_treated_as_ready(monkeypatch):
    monkeypatch.setattr(
        "ubundiforge.config.check_backend_installed",
        lambda backend: backend == "codex",
    )
    monkeypatch.setattr(
        "ubundiforge.config._run_status_command",
        lambda cmd, timeout=5: CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="Logged in using ChatGPT",
            stderr="status command failed",
        ),
    )

    status = get_backend_status("codex")

    assert status.installed is True
    assert status.ready is None
