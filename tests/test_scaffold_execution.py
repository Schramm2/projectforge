"""Tests for the scaffold phase execution state machine."""

from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from projectforge.runner import ProviderExit
from projectforge.scaffold_execution import (
    PhaseExecutionDependencies,
    PhaseExecutionError,
    PhaseExecutionSettings,
    PhaseRoutePlan,
    ScaffoldPhaseExecutor,
)


def _settings(tmp_path: Path, *, use_agents: bool = False) -> PhaseExecutionSettings:
    return PhaseExecutionSettings(
        project_dir=tmp_path / "generated",
        stack="nextjs",
        conventions="Use strict typing.",
        model_override=None,
        backend_models={"claude": "configured-claude"},
        verbose=False,
        approval_mode="safe",
        allow_unsafe=False,
        use_agents=use_agents,
    )


def _console() -> Console:
    return Console(file=StringIO(), force_terminal=False, color_system=None, width=120)


def test_route_plan_names_execution_windows() -> None:
    plan = PhaseRoutePlan.from_pairs(
        [
            ("architecture", "claude"),
            ("frontend", "antigravity"),
            ("tests", "codex"),
            ("verify", "claude"),
        ]
    )

    assert [route.phase for route in plan.serial_first] == ["architecture"]
    assert [route.phase for route in plan.parallel_middle] == ["frontend", "tests"]
    assert [route.phase for route in plan.serial_last] == ["verify"]
    assert plan.can_parallel is True
    assert plan.execution_window_count == 3


def test_executor_runs_serial_parallel_serial_and_records_lifecycle(tmp_path: Path) -> None:
    plan = PhaseRoutePlan.from_pairs(
        [
            ("architecture", "claude"),
            ("frontend", "antigravity"),
            ("tests", "codex"),
            ("verify", "claude"),
        ]
    )
    prompts = [(route.phase, route.backend, f"prompt for {route.phase}") for route in plan.ordered]
    calls: list[tuple[str, object]] = []
    marks: list[tuple[str, str]] = []

    def run_phase(backend, prompt, project_dir, **kwargs):
        project_dir.mkdir(parents=True, exist_ok=True)
        calls.append(("serial", kwargs["label"]))
        assert kwargs["approval_mode"] == "safe"
        assert kwargs["allow_unsafe"] is False
        if backend == "claude":
            assert kwargs["model"] == "configured-claude"
        return 0

    def run_parallel(phases, project_dir, **kwargs):
        project_dir.mkdir(parents=True, exist_ok=True)
        calls.append(("parallel", [phase["label"] for phase in phases]))
        return [(phase["label"], 0) for phase in phases]

    def mark_phase(_project_dir, phase, *, status, **_kwargs):
        marks.append((phase, status))
        return {}

    result = ScaffoldPhaseExecutor(
        console=_console(),
        plan=plan,
        phase_prompts=prompts,
        completed_phases=set(),
        settings=_settings(tmp_path),
        dependencies=PhaseExecutionDependencies(
            run_phase=run_phase,
            run_parallel=run_parallel,
            mark_phase=mark_phase,
        ),
    ).execute()

    assert calls == [
        ("serial", "Architecture & Core"),
        ("parallel", ["Frontend & UI", "Tests & Automation"]),
        ("serial", "Verify & Fix"),
    ]
    assert marks == [
        ("architecture", "running"),
        ("architecture", "completed"),
        ("frontend", "running"),
        ("tests", "running"),
        ("frontend", "completed"),
        ("tests", "completed"),
        ("verify", "running"),
        ("verify", "completed"),
    ]
    assert result.agent_stats is None


def test_executor_preserves_completed_phase_and_stops_after_failure(tmp_path: Path) -> None:
    plan = PhaseRoutePlan.from_pairs(
        [
            ("architecture", "claude"),
            ("tests", "codex"),
            ("verify", "claude"),
        ]
    )
    prompts = [(route.phase, route.backend, f"prompt for {route.phase}") for route in plan.ordered]
    calls: list[str] = []
    marks: list[tuple[str, str, str | None]] = []

    def run_phase(_backend, _prompt, project_dir, **kwargs):
        project_dir.mkdir(parents=True, exist_ok=True)
        calls.append(kwargs["label"])
        return ProviderExit(9, failure_category="authentication")

    def mark_phase(_project_dir, phase, *, status, failure_category=None, **_kwargs):
        marks.append((phase, status, failure_category))
        return {}

    executor = ScaffoldPhaseExecutor(
        console=_console(),
        plan=plan,
        phase_prompts=prompts,
        completed_phases={"architecture"},
        settings=_settings(tmp_path),
        dependencies=PhaseExecutionDependencies(
            run_phase=run_phase,
            run_parallel=lambda *_args, **_kwargs: [],
            mark_phase=mark_phase,
        ),
    )

    with pytest.raises(PhaseExecutionError) as raised:
        executor.execute()

    assert calls == ["Tests & Automation"]
    assert marks == [
        ("tests", "running", None),
        ("tests", "failed", "authentication"),
    ]
    assert raised.value.failures[0].exit_code == 9
    assert raised.value.failures[0].label == "Tests & Automation"


def test_executor_aggregates_orchestrated_task_stats(tmp_path: Path) -> None:
    plan = PhaseRoutePlan.from_pairs(
        [("architecture", "claude"), ("tests", "codex"), ("verify", "claude")]
    )
    prompts = [(route.phase, route.backend, f"prompt for {route.phase}") for route in plan.ordered]
    calls: list[str] = []

    def run_orchestrated(**kwargs):
        kwargs["project_dir"].mkdir(parents=True, exist_ok=True)
        calls.append(kwargs["phase"])
        return 0, {"planned": 2, "completed": 2, "failed": 0}

    result = ScaffoldPhaseExecutor(
        console=_console(),
        plan=plan,
        phase_prompts=prompts,
        completed_phases=set(),
        settings=_settings(tmp_path, use_agents=True),
        dependencies=PhaseExecutionDependencies(
            run_phase=lambda *_args, **_kwargs: 0,
            run_parallel=lambda *_args, **_kwargs: [],
            mark_phase=lambda *_args, **_kwargs: {},
            run_orchestrated=run_orchestrated,
        ),
    ).execute()

    assert calls == ["architecture", "tests", "verify"]
    assert result.agent_stats == {"planned": 6, "completed": 6, "failed": 0}


def test_executor_rejects_missing_or_mismatched_prompts(tmp_path: Path) -> None:
    plan = PhaseRoutePlan.from_pairs([("architecture", "claude")])
    dependencies = PhaseExecutionDependencies(
        run_phase=lambda *_args, **_kwargs: 0,
        run_parallel=lambda *_args, **_kwargs: [],
        mark_phase=lambda *_args, **_kwargs: {},
    )

    with pytest.raises(ValueError, match="Missing prompt"):
        ScaffoldPhaseExecutor(
            console=_console(),
            plan=plan,
            phase_prompts=[],
            completed_phases=set(),
            settings=_settings(tmp_path),
            dependencies=dependencies,
        )

    with pytest.raises(ValueError, match="backend does not match"):
        ScaffoldPhaseExecutor(
            console=_console(),
            plan=plan,
            phase_prompts=[("architecture", "codex", "prompt")],
            completed_phases=set(),
            settings=_settings(tmp_path),
            dependencies=dependencies,
        )
