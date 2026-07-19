"""Tests for post-scaffold evidence and handoff completion."""

from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from projectforge.scaffold_completion import (
    ScaffoldCompletionDependencies,
    ScaffoldCompletionSettings,
    ScaffoldRecordError,
    complete_scaffold,
)
from projectforge.verify import VerifyReport


def _settings(tmp_path: Path, **overrides) -> ScaffoldCompletionSettings:
    values = {
        "answers": {"name": "atlas", "stack": "fastapi"},
        "phase_backends": [("architecture", "claude"), ("verify", "claude")],
        "project_dir": tmp_path / "atlas",
        "conventions": "Use strict typing.",
        "model_override": None,
        "backend_models": {},
        "approval_mode": "safe",
        "convention_sources": (),
        "verification_requested": True,
        "verbose": False,
        "scaffold_started_at": 0.0,
        "sound_enabled": True,
        "open_editor": True,
        "preferred_editor": "code",
        "agent_stats": None,
    }
    values.update(overrides)
    return ScaffoldCompletionSettings(**values)


def _dependencies(calls: list[str], **overrides) -> ScaffoldCompletionDependencies:
    report = VerifyReport()
    defaults = {
        "write_manifest": lambda *_args, **_kwargs: calls.append("manifest"),
        "ensure_git": lambda _path: calls.append("git") or True,
        "verify": lambda *_args, **_kwargs: calls.append("verify") or report,
        "write_verification": lambda *_args: calls.append("verification-evidence"),
        "append_quality": lambda **_kwargs: calls.append("quality"),
        "run_hook": lambda *_args: calls.append("hook"),
        "append_log": lambda *_args, **_kwargs: calls.append("log"),
        "record_preferences": lambda _answers: calls.append("preferences"),
        "render_dashboard": lambda **_kwargs: calls.append("dashboard"),
        "write_card": lambda *_args, **_kwargs: calls.append("card"),
        "inject_readme_badge": lambda _path: calls.append("badge"),
        "play_sound": lambda **_kwargs: calls.append("sound"),
        "open_project": lambda *_args, **_kwargs: calls.append("editor"),
    }
    defaults.update(overrides)
    return ScaffoldCompletionDependencies(**defaults)


def test_completion_runs_required_evidence_and_handoff_in_order(tmp_path: Path) -> None:
    calls: list[str] = []
    console = Console(file=StringIO(), force_terminal=False, color_system=None)

    complete_scaffold(
        console=console,
        settings=_settings(tmp_path),
        dependencies=_dependencies(calls),
    )

    assert calls == [
        "manifest",
        "git",
        "verify",
        "verification-evidence",
        "quality",
        "hook",
        "log",
        "preferences",
        "dashboard",
        "card",
        "badge",
        "sound",
        "editor",
    ]


def test_completion_stops_when_required_manifest_cannot_be_saved(tmp_path: Path) -> None:
    calls: list[str] = []

    def fail_manifest(*_args, **_kwargs):
        calls.append("manifest")
        raise OSError("unwritable")

    with pytest.raises(ScaffoldRecordError):
        complete_scaffold(
            console=Console(file=StringIO(), force_terminal=False, color_system=None),
            settings=_settings(tmp_path),
            dependencies=_dependencies(calls, write_manifest=fail_manifest),
        )

    assert calls == ["manifest"]


def test_completion_keeps_project_when_optional_evidence_write_fails(tmp_path: Path) -> None:
    calls: list[str] = []
    output = StringIO()

    def fail_quality(**_kwargs):
        calls.append("quality")
        raise OSError("unwritable")

    complete_scaffold(
        console=Console(file=output, force_terminal=False, color_system=None),
        settings=_settings(tmp_path),
        dependencies=_dependencies(calls, append_quality=fail_quality),
    )

    assert "could not save some local history or verification files" in " ".join(
        output.getvalue().split()
    )
    assert calls[-2:] == ["sound", "editor"]


def test_completion_skips_verification_and_optional_desktop_actions(tmp_path: Path) -> None:
    calls: list[str] = []
    console = Console(file=StringIO(), force_terminal=False, color_system=None)

    complete_scaffold(
        console=console,
        settings=_settings(
            tmp_path,
            verification_requested=False,
            sound_enabled=False,
            open_editor=False,
        ),
        dependencies=_dependencies(calls),
    )

    assert "verify" not in calls
    assert "verification-evidence" not in calls
    assert "editor" not in calls
    assert "sound" in calls


def test_completion_prints_manual_git_recovery_when_init_fails(tmp_path: Path) -> None:
    calls: list[str] = []
    output = StringIO()

    complete_scaffold(
        console=Console(file=output, force_terminal=False, color_system=None),
        settings=_settings(tmp_path),
        dependencies=_dependencies(calls, ensure_git=lambda _path: False),
    )

    assert "git init && git add -A" in output.getvalue()
