"""Tests for backend readiness detection."""

from subprocess import CompletedProcess

from ubundiforge.config import (
    BackendStatus,
    check_backend_installed,
    get_backend_status,
    get_usable_backends,
)
from ubundiforge.setup import _normalize_forge_config


def test_antigravity_install_check_uses_agy_binary(monkeypatch):
    observed: list[str] = []

    def fake_which(command):
        observed.append(command)
        return "/usr/local/bin/agy"

    monkeypatch.setattr("ubundiforge.config.shutil.which", fake_which)

    assert check_backend_installed("antigravity") is True
    assert observed == ["agy"]


def test_legacy_gemini_config_migrates_to_antigravity_and_drops_model_override():
    normalized = _normalize_forge_config(
        {
            "available_backends": ["claude", "gemini", "antigravity"],
            "backend_models": {
                "gemini": "gemini-2.5-pro",
                "antigravity": "Gemini 3.5 Flash (High)",
            },
        }
    )

    assert normalized["available_backends"] == ["claude", "antigravity"]
    assert normalized["backend_models"] == {"antigravity": "Gemini 3.5 Flash (High)"}


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


def test_antigravity_status_reports_ready_when_models_are_available(monkeypatch):
    monkeypatch.setattr(
        "ubundiforge.config.check_backend_installed",
        lambda backend: backend == "antigravity",
    )

    def fake_run(cmd, timeout=5):
        if cmd == ["agy", "--version"]:
            return CompletedProcess(cmd, 0, "1.1.0\n", "")
        assert cmd == ["agy", "models"]
        assert timeout == 15
        return CompletedProcess(cmd, 0, "Gemini 3.5 Flash (High)\n", "")

    monkeypatch.setattr("ubundiforge.config._run_status_command", fake_run)

    status = get_backend_status("antigravity")

    assert status.installed is True
    assert status.ready is True
    assert status.auth_mode == "google_sign_in"
    assert status.login_command == "agy"


def test_antigravity_status_reports_needs_login_without_google_session(monkeypatch):
    monkeypatch.setattr(
        "ubundiforge.config.check_backend_installed",
        lambda backend: backend == "antigravity",
    )

    def fake_run(cmd, timeout=5):
        if cmd == ["agy", "--version"]:
            return CompletedProcess(cmd, 0, "1.1.0\n", "")
        return CompletedProcess(
            cmd,
            1,
            "",
            "Error: Please sign in to view available models. Launch the CLI without arguments.",
        )

    monkeypatch.setattr("ubundiforge.config._run_status_command", fake_run)

    status = get_backend_status("antigravity")

    assert status.ready is False
    assert status.login_command == "agy"


def test_antigravity_status_is_unknown_on_non_auth_failure(monkeypatch):
    monkeypatch.setattr(
        "ubundiforge.config.check_backend_installed",
        lambda backend: backend == "antigravity",
    )

    def fake_run(cmd, timeout=5):
        if cmd == ["agy", "--version"]:
            return CompletedProcess(cmd, 0, "1.1.0\n", "")
        return CompletedProcess(cmd, 1, "", "Network unavailable")

    monkeypatch.setattr("ubundiforge.config._run_status_command", fake_run)

    status = get_backend_status("antigravity")

    assert status.installed is True
    assert status.ready is None


def test_get_usable_backends_requires_verified_readiness(monkeypatch):
    monkeypatch.setattr(
        "ubundiforge.config.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=True, ready=False),
            "antigravity": BackendStatus(installed=True, ready=None),
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
