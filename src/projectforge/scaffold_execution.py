"""Execute a scaffold's ordered provider phases and persist their lifecycle."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypedDict

from rich.console import Console

from projectforge.router import PHASE_ARCHITECTURE, PHASE_LABELS, PHASE_VERIFY
from projectforge.ui import BACKEND_ACCENTS, make_file_tree, make_step_panel, status_line

PhaseRoutePair = tuple[str, str]
PhasePromptTriple = tuple[str, str, str]
PhaseStatus = Literal["pending", "active", "completed", "failed"]


class PhaseTimelineItem(TypedDict):
    """Mutable display state shared with the streaming provider runner."""

    label: str
    status: PhaseStatus
    elapsed: float
    accent: str


class ParallelPhaseRequest(TypedDict):
    """Input contract consumed by ``run_ai_parallel``."""

    label: str
    backend: str
    prompt: str
    model: str | None
    approval_mode: str
    allow_unsafe: bool


@dataclass(frozen=True)
class PhaseRoute:
    """A scaffold phase assigned to one provider backend."""

    phase: str
    backend: str

    @property
    def label(self) -> str:
        return PHASE_LABELS.get(self.phase, self.phase)


@dataclass(frozen=True)
class PhaseRoutePlan:
    """The execution windows implied by an ordered phase-to-backend routing result."""

    ordered: tuple[PhaseRoute, ...]
    serial_first: tuple[PhaseRoute, ...]
    parallel_middle: tuple[PhaseRoute, ...]
    serial_last: tuple[PhaseRoute, ...]

    @classmethod
    def from_pairs(cls, phase_backends: list[PhaseRoutePair]) -> PhaseRoutePlan:
        ordered = tuple(PhaseRoute(phase, backend) for phase, backend in phase_backends)
        return cls(
            ordered=ordered,
            serial_first=tuple(route for route in ordered if route.phase == PHASE_ARCHITECTURE),
            parallel_middle=tuple(
                route for route in ordered if route.phase not in {PHASE_ARCHITECTURE, PHASE_VERIFY}
            ),
            serial_last=tuple(route for route in ordered if route.phase == PHASE_VERIFY),
        )

    @property
    def can_parallel(self) -> bool:
        return len(self.parallel_middle) > 1

    @property
    def execution_window_count(self) -> int:
        middle_windows = 1 if self.can_parallel else len(self.parallel_middle)
        return len(self.serial_first) + middle_windows + len(self.serial_last)


@dataclass(frozen=True)
class PhaseExecutionSettings:
    """Stable inputs shared by every provider phase in one scaffold."""

    project_dir: Path
    stack: str
    conventions: str
    model_override: str | None
    backend_models: dict[str, str]
    verbose: bool
    approval_mode: str
    allow_unsafe: bool
    use_agents: bool


@dataclass(frozen=True)
class FailedPhase:
    """A provider phase that could not complete."""

    backend: str
    label: str
    exit_code: int


class PhaseExecutionError(Exception):
    """Stop execution after one or more provider phases fail."""

    def __init__(self, failures: tuple[FailedPhase, ...]) -> None:
        self.failures = failures
        super().__init__(f"{len(failures)} scaffold phase(s) failed")


@dataclass
class AgentTaskStats:
    """Aggregate task counts returned by orchestrated provider phases."""

    planned: int = 0
    completed: int = 0
    failed: int = 0

    def add(self, phase_stats: dict[str, int]) -> None:
        self.planned += phase_stats.get("planned", 0)
        self.completed += phase_stats.get("completed", 0)
        self.failed += phase_stats.get("failed", 0)

    def as_dict(self) -> dict[str, int]:
        return {
            "planned": self.planned,
            "completed": self.completed,
            "failed": self.failed,
        }


@dataclass(frozen=True)
class PhaseExecutionResult:
    """Execution metadata needed by the post-scaffold dashboard."""

    agent_stats: dict[str, int] | None


class PhaseRunner(Protocol):
    def __call__(
        self,
        backend: str,
        prompt: str,
        project_dir: Path,
        *,
        model: str | None,
        verbose: bool,
        label: str,
        phase_context: list[PhaseTimelineItem],
        approval_mode: str,
        allow_unsafe: bool,
    ) -> int: ...


class ParallelPhaseRunner(Protocol):
    def __call__(
        self,
        phases: list[ParallelPhaseRequest],
        project_dir: Path,
        *,
        verbose: bool,
    ) -> list[tuple[str, int]]: ...


class OrchestratedPhaseRunner(Protocol):
    def __call__(
        self,
        *,
        phase: str,
        backend: str,
        prompt: str,
        project_dir: Path,
        stack: str,
        conventions: str,
        model: str | None,
        verbose: bool,
        approval_mode: str,
        allow_unsafe: bool,
    ) -> tuple[int, dict[str, int]]: ...


PhaseMarker = Callable[..., dict]


@dataclass(frozen=True)
class PhaseExecutionDependencies:
    """Side-effecting operations supplied by the CLI composition root."""

    run_phase: PhaseRunner
    run_parallel: ParallelPhaseRunner
    mark_phase: PhaseMarker
    run_orchestrated: OrchestratedPhaseRunner | None = None


class ScaffoldPhaseExecutor:
    """Run serial and parallel provider windows as one explicit state machine."""

    def __init__(
        self,
        *,
        console: Console,
        plan: PhaseRoutePlan,
        phase_prompts: list[PhasePromptTriple],
        completed_phases: set[str],
        settings: PhaseExecutionSettings,
        dependencies: PhaseExecutionDependencies,
    ) -> None:
        self.console = console
        self.plan = plan
        self.completed_phases = completed_phases
        self.settings = settings
        self.dependencies = dependencies
        self.prompts = self._index_prompts(phase_prompts)
        self.timeline = self._build_timeline()
        self.agent_stats = AgentTaskStats()
        self.ran_orchestrated_phase = False

    def _index_prompts(self, phase_prompts: list[PhasePromptTriple]) -> dict[str, str]:
        prompts: dict[str, str] = {}
        prompt_backends: dict[str, str] = {}
        for phase, backend, prompt in phase_prompts:
            if phase in prompts:
                raise ValueError(f"Duplicate prompt for scaffold phase: {phase}")
            prompts[phase] = prompt
            prompt_backends[phase] = backend

        for route in self.plan.ordered:
            if route.phase not in prompts:
                raise ValueError(f"Missing prompt for scaffold phase: {route.phase}")
            if prompt_backends[route.phase] != route.backend:
                raise ValueError(f"Prompt backend does not match route for phase: {route.phase}")
        return prompts

    def _build_timeline(self) -> list[PhaseTimelineItem]:
        return [
            {
                "label": route.label,
                "status": "completed" if route.phase in self.completed_phases else "pending",
                "elapsed": 0.0,
                "accent": BACKEND_ACCENTS.get(route.backend, "violet"),
            }
            for route in self.plan.ordered
        ]

    def execute(self) -> PhaseExecutionResult:
        """Run all incomplete phases in architecture, middle, verification order."""
        step = self._run_serial_window(self.plan.serial_first, step=1, accent="aqua")
        step = self._run_middle_window(step)
        self._run_serial_window(self.plan.serial_last, step=step, accent="plum")
        return PhaseExecutionResult(
            agent_stats=self.agent_stats.as_dict() if self.ran_orchestrated_phase else None
        )

    def _run_serial_window(
        self,
        routes: tuple[PhaseRoute, ...],
        *,
        step: int,
        accent: str,
    ) -> int:
        for route in routes:
            if self._preserve_completed(route):
                step += 1
                continue
            self._render_step(route, step, accent)
            self._run_single_phase(route)
            self._render_project_tree()
            step += 1
        return step

    def _run_middle_window(self, step: int) -> int:
        if self.settings.use_agents:
            return self._run_serial_window(self.plan.parallel_middle, step=step, accent="violet")

        remaining: list[PhaseRoute] = []
        for route in self.plan.parallel_middle:
            if self._preserve_completed(route):
                step += 1
            else:
                remaining.append(route)

        if len(remaining) > 1:
            self._render_parallel_step(remaining, step)
            self._run_parallel_phases(remaining)
            self._render_project_tree()
            return step + len(remaining)
        if remaining:
            return self._run_serial_window(tuple(remaining), step=step, accent="violet")
        return step

    def _preserve_completed(self, route: PhaseRoute) -> bool:
        if route.phase not in self.completed_phases:
            return False
        self.console.print(status_line(f"Preserved completed phase: {route.label}", accent="aqua"))
        return True

    def _render_step(self, route: PhaseRoute, step: int, accent: str) -> None:
        self.console.print()
        self.console.print(
            make_step_panel(
                step,
                len(self.plan.ordered),
                route.label,
                detail=f"backend: {route.backend}",
                accent=accent,
            )
        )

    def _render_parallel_step(self, routes: list[PhaseRoute], step: int) -> None:
        labels = " + ".join(f"{route.label} ({route.backend})" for route in routes)
        self.console.print()
        self.console.print(
            make_step_panel(
                step,
                len(self.plan.ordered),
                "Parallel execution window",
                detail=labels,
                accent="amber",
            )
        )

    def _timeline_item(self, phase: str) -> PhaseTimelineItem:
        phase_index = next(
            index for index, route in enumerate(self.plan.ordered) if route.phase == phase
        )
        return self.timeline[phase_index]

    def _model_for(self, backend: str) -> str | None:
        return self.settings.model_override or self.settings.backend_models.get(backend)

    def _run_single_phase(self, route: PhaseRoute) -> None:
        timeline_item = self._timeline_item(route.phase)
        timeline_item["status"] = "active"
        phase_start = time.monotonic()
        self.dependencies.mark_phase(
            self.settings.project_dir,
            route.phase,
            status="running",
        )

        if self.settings.use_agents:
            returncode = self._run_orchestrated_phase(route)
        else:
            returncode = self.dependencies.run_phase(
                route.backend,
                self.prompts[route.phase],
                self.settings.project_dir,
                model=self._model_for(route.backend),
                verbose=self.settings.verbose,
                label=route.label,
                phase_context=self.timeline,
                approval_mode=self.settings.approval_mode,
                allow_unsafe=self.settings.allow_unsafe,
            )

        phase_elapsed = time.monotonic() - phase_start
        timeline_item["elapsed"] = phase_elapsed
        if returncode != 0:
            self._record_failure(route, returncode, phase_elapsed)
            raise PhaseExecutionError((FailedPhase(route.backend, route.label, returncode),))

        timeline_item["status"] = "completed"
        self.dependencies.mark_phase(
            self.settings.project_dir,
            route.phase,
            status="completed",
            duration_seconds=phase_elapsed,
            exit_code=0,
        )

    def _run_orchestrated_phase(self, route: PhaseRoute) -> int:
        if self.dependencies.run_orchestrated is None:
            raise ValueError("Agent execution requires an orchestrated phase runner")
        returncode, phase_stats = self.dependencies.run_orchestrated(
            phase=route.phase,
            backend=route.backend,
            prompt=self.prompts[route.phase],
            project_dir=self.settings.project_dir,
            stack=self.settings.stack,
            conventions=self.settings.conventions,
            model=self._model_for(route.backend),
            verbose=self.settings.verbose,
            approval_mode=self.settings.approval_mode,
            allow_unsafe=self.settings.allow_unsafe,
        )
        self.ran_orchestrated_phase = True
        self.agent_stats.add(phase_stats)
        return returncode

    def _run_parallel_phases(self, routes: list[PhaseRoute]) -> None:
        requests: list[ParallelPhaseRequest] = []
        route_by_label: dict[str, PhaseRoute] = {}
        for route in routes:
            route_by_label[route.label] = route
            self._timeline_item(route.phase)["status"] = "active"
            self.dependencies.mark_phase(
                self.settings.project_dir,
                route.phase,
                status="running",
            )
            requests.append(
                {
                    "label": route.label,
                    "backend": route.backend,
                    "prompt": self.prompts[route.phase],
                    "model": self._model_for(route.backend),
                    "approval_mode": self.settings.approval_mode,
                    "allow_unsafe": self.settings.allow_unsafe,
                }
            )

        parallel_started = time.monotonic()
        results = self.dependencies.run_parallel(
            requests,
            self.settings.project_dir,
            verbose=self.settings.verbose,
        )
        parallel_elapsed = time.monotonic() - parallel_started
        failures: list[FailedPhase] = []
        for label, returncode in results:
            route = route_by_label[label]
            if returncode != 0:
                self._record_failure(route, returncode, parallel_elapsed)
                failures.append(FailedPhase(route.backend, label, returncode))
                continue
            self._timeline_item(route.phase)["status"] = "completed"
            self.dependencies.mark_phase(
                self.settings.project_dir,
                route.phase,
                status="completed",
                duration_seconds=parallel_elapsed,
                exit_code=0,
            )

        if failures:
            raise PhaseExecutionError(tuple(failures))

    def _record_failure(self, route: PhaseRoute, returncode: int, elapsed: float) -> None:
        self._timeline_item(route.phase)["status"] = "failed"
        self.dependencies.mark_phase(
            self.settings.project_dir,
            route.phase,
            status="failed",
            duration_seconds=elapsed,
            exit_code=returncode,
            failure_category=getattr(returncode, "failure_category", "unknown"),
        )

    def _render_project_tree(self) -> None:
        self.console.print()
        self.console.print(make_file_tree(self.settings.project_dir))
