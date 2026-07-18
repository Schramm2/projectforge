"""Multi-agent orchestration protocol — data structures and ForgeAgent contract."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class AgentTask:
    """A unit of work assigned to a subagent."""

    id: str
    description: str
    file_territory: list[str]
    context: str
    dependencies: list[str]
    phase: str
    backend: str
    model: str | None = None


@dataclass
class AgentResult:
    """What a subagent produces."""

    task_id: str
    files_created: list[str]
    files_modified: list[str]
    summary: str
    success: bool
    duration: float
    returncode: int


@dataclass
class ProgressEvent:
    """Emitted by adapters, consumed by the UI layer."""

    task_id: str
    agent_label: str
    event_type: str  # "started" | "progress" | "completed" | "failed"
    message: str
    timestamp: float


@dataclass
class DecompositionPlan:
    """Output of the planning call."""

    tasks: list[AgentTask]
    execution_order: list[list[str]]
    rationale: str


class ForgeAgent(Protocol):
    """Contract that every backend adapter implements."""

    def build_prompt(self, task: AgentTask) -> str: ...

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str: ...

    def parse_plan(self, raw_output: str, phase: str, backend: str) -> DecompositionPlan: ...

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]: ...

    def execute(
        self,
        task: AgentTask,
        project_dir: Path,
        on_progress: Callable[[ProgressEvent], None],
    ) -> AgentResult: ...
