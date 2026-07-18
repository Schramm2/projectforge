"""Tests for resumable scaffold phase evidence."""

import json

import pytest

from ubundiforge.execution_state import (
    ProgressContractError,
    initialize_progress,
    mark_phase,
)


def _contract():
    return [
        ("architecture", "claude", "private architecture prompt"),
        ("tests", "codex", "private tests prompt"),
    ]


def test_progress_records_hashes_without_prompts_and_updates_atomically(tmp_path):
    state = initialize_progress(
        tmp_path,
        name="atlas",
        stack="fastapi",
        approval_mode="safe",
        phase_prompts=_contract(),
        resume=False,
    )

    payload = json.loads((tmp_path / ".forge" / "progress.json").read_text())
    assert state == payload
    assert payload["schema_version"] == 1
    assert [phase["status"] for phase in payload["phases"]] == ["pending", "pending"]
    assert payload["phases"][0]["prompt_sha256"].startswith("sha256:")
    assert "private architecture prompt" not in (tmp_path / ".forge" / "progress.json").read_text()
    assert not (tmp_path / ".forge" / "progress.json.tmp").exists()

    mark_phase(tmp_path, "architecture", status="completed", duration_seconds=12.345)
    payload = json.loads((tmp_path / ".forge" / "progress.json").read_text())
    assert payload["phases"][0]["status"] == "completed"
    assert payload["phases"][0]["duration_seconds"] == 12.345


def test_resume_preserves_completed_phases_and_retries_incomplete_phases(tmp_path):
    initialize_progress(
        tmp_path,
        name="atlas",
        stack="fastapi",
        approval_mode="safe",
        phase_prompts=_contract(),
        resume=False,
    )
    mark_phase(tmp_path, "architecture", status="completed", duration_seconds=4)
    mark_phase(
        tmp_path,
        "tests",
        status="failed",
        exit_code=9,
        failure_category="quota",
        duration_seconds=2,
    )

    resumed = initialize_progress(
        tmp_path,
        name="atlas",
        stack="fastapi",
        approval_mode="safe",
        phase_prompts=_contract(),
        resume=True,
    )

    assert [phase["status"] for phase in resumed["phases"]] == ["completed", "pending"]
    assert resumed["resume_count"] == 1
    assert resumed["phases"][1]["attempts"] == 1
    assert resumed["phases"][1]["last_failure_category"] == "quota"


def test_resume_migrates_retired_gemini_backend_without_weakening_contract(tmp_path):
    contract = [("frontend", "antigravity", "private frontend prompt")]
    initialize_progress(
        tmp_path,
        name="atlas",
        stack="nextjs",
        approval_mode="safe",
        phase_prompts=contract,
        resume=False,
    )
    progress_path = tmp_path / ".forge" / "progress.json"
    legacy = json.loads(progress_path.read_text())
    legacy["phases"][0]["backend"] = "gemini"
    progress_path.write_text(json.dumps(legacy))

    resumed = initialize_progress(
        tmp_path,
        name="atlas",
        stack="nextjs",
        approval_mode="safe",
        phase_prompts=contract,
        resume=True,
    )

    assert resumed["phases"][0]["backend"] == "antigravity"
    assert resumed["resume_count"] == 1


@pytest.mark.parametrize(
    ("name", "stack", "approval_mode", "phases"),
    [
        ("changed", "fastapi", "safe", _contract()),
        ("atlas", "python-cli", "safe", _contract()),
        ("atlas", "fastapi", "unsafe", _contract()),
        ("atlas", "fastapi", "safe", [("architecture", "codex", "changed")]),
    ],
)
def test_resume_rejects_a_changed_execution_contract(tmp_path, name, stack, approval_mode, phases):
    initialize_progress(
        tmp_path,
        name="atlas",
        stack="fastapi",
        approval_mode="safe",
        phase_prompts=_contract(),
        resume=False,
    )

    with pytest.raises(ProgressContractError):
        initialize_progress(
            tmp_path,
            name=name,
            stack=stack,
            approval_mode=approval_mode,
            phase_prompts=phases,
            resume=True,
        )


def test_resume_requires_existing_progress_evidence(tmp_path):
    with pytest.raises(ProgressContractError, match="progress evidence"):
        initialize_progress(
            tmp_path,
            name="atlas",
            stack="fastapi",
            approval_mode="safe",
            phase_prompts=_contract(),
            resume=True,
        )
