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


def test_gemini_status_reports_ready_when_cli_responds(monkeypatch):
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
    assert status.ready is True
    assert "responded successfully" in status.detail


def test_get_usable_backends_excludes_known_unready_backends(monkeypatch):
    monkeypatch.setattr(
        "ubundiforge.config.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=True, ready=False),
            "gemini": BackendStatus(installed=True, ready=None),
            "codex": BackendStatus(installed=True, ready=True),
        },
    )

    assert get_usable_backends() == ["gemini", "codex"]
