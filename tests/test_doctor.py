"""Tests for secret-safe ProjectForge diagnostics."""

import json

from projectforge.config import BackendStatus
from projectforge.doctor import (
    _provider_check,
    build_doctor_report,
    build_environment_report,
    doctor_exit_code,
)


def test_doctor_report_is_deterministic_and_excludes_provider_detail(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"preferred_editor": "code"}))
    monkeypatch.setattr("projectforge.doctor.CONFIG_PATH", config_path)
    monkeypatch.setattr(
        "projectforge.doctor.get_backend_statuses",
        lambda: {
            "antigravity": BackendStatus(installed=True, ready=None, detail="secret@example.com"),
            "codex": BackendStatus(
                installed=True,
                ready=True,
                detail="token=do-not-print",
                login_command="codex login",
                auth_mode="chatgpt",
            ),
            "claude": BackendStatus(installed=False, ready=False),
        },
    )
    monkeypatch.setattr(
        "projectforge.doctor.get_backend_version",
        lambda backend: {"codex": "codex-cli 1.2.3", "antigravity": "0.9.0"}.get(backend),
    )
    monkeypatch.setattr(
        "projectforge.doctor.build_environment_report",
        lambda: {
            "python": {"version": "3.12.1", "supported": True},
            "git": {"installed": True, "version": "git version 2.50.0"},
            "docker": {"installed": False, "version": None},
            "editors": {"code": True, "cursor": False},
        },
    )

    report = build_doctor_report()
    serialized = json.dumps(report)

    assert list(report["providers"]) == ["claude", "antigravity", "codex"]
    assert report["providers"]["antigravity"]["readiness"] == "check_inconclusive"
    assert report["providers"]["codex"]["auth_mode"] == "chatgpt"
    assert report["providers"]["codex"]["model_behavior"] == {
        "mode": "provider_default",
        "value": None,
    }
    assert report["providers"]["codex"]["capabilities"] == {
        "deterministic_status": True,
        "default_model": "provider_default",
        "approval_modes": {
            "safe": "workspace-write",
            "plan": "read-only",
            "unsafe": "bypass approvals and sandbox",
        },
        "unsafe_requires_consent": True,
    }
    assert report["providers"]["antigravity"]["capabilities"]["deterministic_status"] is True
    assert report["providers"]["antigravity"]["install_url"] == (
        "https://antigravity.google/docs/cli-install"
    )
    assert report["providers"]["antigravity"]["check"] == {
        "command": "agy --version; agy models",
        "observed": "The readiness check could not confirm sign-in.",
    }
    assert report["providers"]["claude"]["check"] == {
        "command": "PATH lookup for `claude`",
        "observed": "Forge could not find this tool on your system.",
    }
    assert "codex login" not in report["providers"]["codex"]["repair"]
    assert "manual readiness check" in report["providers"]["antigravity"]["repair"]
    assert report["config"] == {"status": "valid"}
    assert report["environment"]["python"]["supported"] is True
    assert "secret@example.com" not in serialized
    assert "do-not-print" not in serialized


def test_doctor_counts_supported_macos_app_as_available_editor(monkeypatch):
    monkeypatch.setattr(
        "projectforge.doctor._check_editor_installed",
        lambda command, _app_bundle: (False, command == "code"),
    )

    report = build_environment_report()

    assert report["editors"]["code"] is True
    assert report["editors"]["cursor"] is False


def test_doctor_reports_only_antigravity_version_command_when_models_was_not_run():
    check = _provider_check(
        "antigravity",
        BackendStatus(
            installed=True,
            ready=None,
            detail="Antigravity is installed, but Forge could not run its version check.",
        ),
    )

    assert check["command"] == "agy --version"


def test_doctor_reports_advanced_model_override_without_other_config(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"backend_models": {"claude": "sonnet"}}))
    monkeypatch.setattr("projectforge.doctor.CONFIG_PATH", config_path)
    monkeypatch.setattr(
        "projectforge.doctor.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=True, ready=True, auth_mode="authenticated"),
            "antigravity": BackendStatus(installed=False, ready=False),
            "codex": BackendStatus(installed=False, ready=False),
        },
    )
    monkeypatch.setattr("projectforge.doctor.get_backend_version", lambda backend: None)
    monkeypatch.setattr("projectforge.doctor.build_environment_report", lambda: {})

    report = build_doctor_report()

    assert report["providers"]["claude"]["model_behavior"] == {
        "mode": "override",
        "value": "sonnet",
    }
    assert report["providers"]["codex"]["model_behavior"] == {
        "mode": "provider_default",
        "value": None,
    }


def test_doctor_gives_identity_safe_login_guidance(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"preferred_editor": "code"}))
    monkeypatch.setattr("projectforge.doctor.CONFIG_PATH", config_path)
    monkeypatch.setattr(
        "projectforge.doctor.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=False, ready=False),
            "antigravity": BackendStatus(
                installed=True,
                ready=False,
                login_command="agy",
            ),
            "codex": BackendStatus(installed=False, ready=False),
        },
    )
    monkeypatch.setattr("projectforge.doctor.get_backend_version", lambda backend: None)
    monkeypatch.setattr("projectforge.doctor.build_environment_report", lambda: {})

    repair = build_doctor_report()["providers"]["antigravity"]["repair"]

    assert "official sign-in flow" in repair
    assert "projectforge doctor" in repair
    assert "agy" not in repair


def test_doctor_inconclusive_codex_has_exact_check_and_next_step(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"preferred_editor": "code"}))
    monkeypatch.setattr("projectforge.doctor.CONFIG_PATH", config_path)
    monkeypatch.setattr(
        "projectforge.doctor.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=False, ready=False),
            "antigravity": BackendStatus(installed=False, ready=False),
            "codex": BackendStatus(
                installed=True,
                ready=None,
                detail="Codex login status exited without a recognized result.",
            ),
        },
    )
    monkeypatch.setattr("projectforge.doctor.get_backend_version", lambda backend: None)
    monkeypatch.setattr("projectforge.doctor.build_environment_report", lambda: {})

    provider = build_doctor_report()["providers"]["codex"]

    assert provider["check"]["command"] == "codex login status"
    assert provider["check"]["observed"] == ("The readiness check could not confirm sign-in.")
    assert "manual readiness check" in provider["repair"]
    assert "codex" not in provider["repair"]


def test_doctor_exit_code_requires_valid_config_and_ready_provider():
    ready = {
        "status": "ready",
        "config": {"status": "valid"},
        "providers": {},
    }
    attention = {**ready, "status": "attention"}

    assert doctor_exit_code(ready) == 0
    assert doctor_exit_code(attention) == 1
