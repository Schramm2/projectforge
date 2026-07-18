"""Tests for secret-safe ProjectForge diagnostics."""

import json

from ubundiforge.config import BackendStatus
from ubundiforge.doctor import build_doctor_report, doctor_exit_code


def test_doctor_report_is_deterministic_and_excludes_provider_detail(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"preferred_editor": "code"}))
    monkeypatch.setattr("ubundiforge.doctor.CONFIG_PATH", config_path)
    monkeypatch.setattr(
        "ubundiforge.doctor.get_backend_statuses",
        lambda: {
            "gemini": BackendStatus(installed=True, ready=None, detail="secret@example.com"),
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
        "ubundiforge.doctor.get_backend_version",
        lambda backend: {"codex": "codex-cli 1.2.3", "gemini": "0.9.0"}.get(backend),
    )
    monkeypatch.setattr(
        "ubundiforge.doctor.build_environment_report",
        lambda: {
            "python": {"version": "3.12.1", "supported": True},
            "git": {"installed": True, "version": "git version 2.50.0"},
            "docker": {"installed": False, "version": None},
            "editors": {"code": True, "cursor": False},
        },
    )

    report = build_doctor_report()
    serialized = json.dumps(report)

    assert list(report["providers"]) == ["claude", "gemini", "codex"]
    assert report["providers"]["gemini"]["readiness"] == "preflight_required"
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
    assert report["providers"]["gemini"]["capabilities"]["deterministic_status"] is False
    assert report["providers"]["gemini"]["install_url"] == (
        "https://geminicli.com/docs/get-started/installation/"
    )
    assert "codex login" not in report["providers"]["codex"]["repair"]
    assert "authentication" in report["providers"]["gemini"]["repair"].lower()
    assert report["config"] == {"status": "valid"}
    assert report["environment"]["python"]["supported"] is True
    assert "secret@example.com" not in serialized
    assert "do-not-print" not in serialized


def test_doctor_reports_advanced_model_override_without_other_config(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"backend_models": {"claude": "sonnet"}}))
    monkeypatch.setattr("ubundiforge.doctor.CONFIG_PATH", config_path)
    monkeypatch.setattr(
        "ubundiforge.doctor.get_backend_statuses",
        lambda: {
            "claude": BackendStatus(installed=True, ready=True, auth_mode="authenticated"),
            "gemini": BackendStatus(installed=False, ready=False),
            "codex": BackendStatus(installed=False, ready=False),
        },
    )
    monkeypatch.setattr("ubundiforge.doctor.get_backend_version", lambda backend: None)
    monkeypatch.setattr("ubundiforge.doctor.build_environment_report", lambda: {})

    report = build_doctor_report()

    assert report["providers"]["claude"]["model_behavior"] == {
        "mode": "override",
        "value": "sonnet",
    }
    assert report["providers"]["codex"]["model_behavior"] == {
        "mode": "provider_default",
        "value": None,
    }


def test_doctor_exit_code_requires_valid_config_and_ready_provider():
    ready = {
        "status": "ready",
        "config": {"status": "valid"},
        "providers": {},
    }
    attention = {**ready, "status": "attention"}

    assert doctor_exit_code(ready) == 0
    assert doctor_exit_code(attention) == 1
