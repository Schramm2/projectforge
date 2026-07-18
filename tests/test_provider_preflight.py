"""Tests for explicit, credential-free provider readiness proofs."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from subprocess import CompletedProcess

from ubundiforge.provider_preflight import (
    GEMINI_READY_SENTINEL,
    load_valid_preflight,
    run_gemini_preflight,
)


def test_gemini_preflight_is_plan_only_and_writes_bounded_proof(monkeypatch, tmp_path):
    proof_path = tmp_path / "provider-preflight.json"
    observed: dict = {}

    monkeypatch.setattr("ubundiforge.provider_preflight.PREFLIGHT_PATH", proof_path)
    monkeypatch.setattr("ubundiforge.provider_preflight.shutil.which", lambda name: "/bin/gemini")

    def fake_run(command, **kwargs):
        if command == ["gemini", "--version"]:
            return CompletedProcess(command, 0, "0.51.0\n", "")
        observed["command"] = command
        observed["cwd"] = kwargs["cwd"]
        return CompletedProcess(command, 0, json.dumps({"response": GEMINI_READY_SENTINEL}), "")

    monkeypatch.setattr("ubundiforge.provider_preflight.subprocess.run", fake_run)

    result = run_gemini_preflight()

    assert result.success is True
    assert observed["command"][0] == "gemini"
    assert observed["command"][observed["command"].index("--approval-mode") + 1] == "plan"
    assert "--sandbox" in observed["command"]
    assert "--output-format" in observed["command"]
    assert proof_path.stat().st_mode & 0o777 == 0o600
    proof = json.loads(proof_path.read_text())
    assert proof["providers"]["gemini"]["version"] == "0.51.0"
    assert "response" not in proof["providers"]["gemini"]
    assert "output" not in proof["providers"]["gemini"]


def test_preflight_proof_must_be_fresh_and_match_runtime_version(monkeypatch, tmp_path):
    proof_path = tmp_path / "provider-preflight.json"
    monkeypatch.setattr("ubundiforge.provider_preflight.PREFLIGHT_PATH", proof_path)
    proof_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "providers": {
                    "gemini": {
                        "version": "0.51.0",
                        "verified_at": (
                            datetime.now(UTC) - timedelta(hours=25)
                        ).isoformat(),
                    }
                },
            }
        )
    )

    assert load_valid_preflight("gemini", version="0.51.0") is False

    payload = json.loads(proof_path.read_text())
    payload["providers"]["gemini"]["verified_at"] = datetime.now(UTC).isoformat()
    proof_path.write_text(json.dumps(payload))

    assert load_valid_preflight("gemini", version="0.50.0") is False
    assert load_valid_preflight("gemini", version="0.51.0") is True


def test_failed_preflight_is_classified_without_persisting_provider_output(monkeypatch, tmp_path):
    proof_path = tmp_path / "provider-preflight.json"
    monkeypatch.setattr("ubundiforge.provider_preflight.PREFLIGHT_PATH", proof_path)
    monkeypatch.setattr("ubundiforge.provider_preflight.shutil.which", lambda name: "/bin/gemini")

    def fake_run(command, **kwargs):
        if command == ["gemini", "--version"]:
            return CompletedProcess(command, 0, "0.51.0\n", "")
        return CompletedProcess(command, 1, "", "Login required for person@example.com")

    monkeypatch.setattr("ubundiforge.provider_preflight.subprocess.run", fake_run)

    result = run_gemini_preflight()

    assert result.success is False
    assert result.category == "authentication"
    assert not proof_path.exists()
    assert "example.com" not in result.detail
