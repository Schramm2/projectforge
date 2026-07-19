"""CLIAdapterBase — shared subprocess execution for all backend adapters."""

from __future__ import annotations

import subprocess
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Thread

from projectforge.execution_policy import build_provider_command
from projectforge.failure_taxonomy import (
    classify_provider_failure,
    is_headless_permission_failure,
)
from projectforge.protocol import (
    AgentResult,
    AgentTask,
    DecompositionPlan,
    ProgressEvent,
    ProgressEventType,
)
from projectforge.provider_permissions import workspace_write_permission
from projectforge.subprocess_utils import PHASE_TIMEOUT, sanitize_progress_line


@dataclass(frozen=True)
class _TaskProgressReporter:
    """Emit timestamped lifecycle events for one agent task."""

    task_id: str
    agent_label: str
    callback: Callable[[ProgressEvent], None]

    @classmethod
    def for_task(
        cls,
        task: AgentTask,
        callback: Callable[[ProgressEvent], None],
    ) -> _TaskProgressReporter:
        description = task.description
        if len(description) > 60:
            description = description[:57].rstrip() + "..."
        return cls(task.id, f"{task.id}: {description}", callback)

    def emit(self, event_type: ProgressEventType, message: str) -> None:
        self.callback(
            ProgressEvent(
                task_id=self.task_id,
                agent_label=self.agent_label,
                event_type=event_type,
                message=message,
                timestamp=time.time(),
            )
        )


@dataclass(frozen=True)
class _ProcessOutcome:
    """Terminal state collected from one streamed provider subprocess."""

    returncode: int
    duration: float
    timed_out: bool
    last_lines: tuple[str, ...]


def _stream_process(
    process: subprocess.Popen,
    *,
    started_at: float,
    reporter: _TaskProgressReporter,
) -> _ProcessOutcome:
    line_queue: Queue[str | None] = Queue()

    def read_stdout() -> None:
        assert process.stdout is not None
        for raw in process.stdout:
            line_queue.put(raw)
        line_queue.put(None)

    reader = Thread(target=read_stdout, daemon=True)
    reader.start()
    last_lines: deque[str] = deque(maxlen=20)
    timed_out = False
    deadline = started_at + PHASE_TIMEOUT

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            process.kill()
            break
        try:
            item = line_queue.get(timeout=min(remaining, 1.0))
        except Empty:
            continue
        if item is None:
            break
        clean = sanitize_progress_line(item)
        if clean:
            last_lines.append(clean)
            reporter.emit("progress", clean)

    reader.join(timeout=5)
    return _ProcessOutcome(
        returncode=process.wait(),
        duration=time.monotonic() - started_at,
        timed_out=timed_out,
        last_lines=tuple(last_lines),
    )


def _agent_result(
    task: AgentTask,
    *,
    summary: str,
    success: bool,
    duration: float,
    returncode: int,
) -> AgentResult:
    return AgentResult(
        task_id=task.id,
        files_created=[],
        files_modified=[],
        summary=summary,
        success=success,
        duration=duration,
        returncode=returncode,
    )


class CLIAdapterBase:
    """Shared subprocess execution — implements ForgeAgent.execute.

    Subclasses override build_prompt, build_planning_prompt, parse_plan, and
    build_cmd to customise prompt construction and command assembly.  This base
    class owns the full subprocess lifecycle: spawn, stream, timeout, and emit
    ProgressEvents.
    """

    backend: str = ""

    def __init__(
        self,
        conventions: str = "",
        *,
        approval_mode: str = "safe",
        allow_unsafe: bool = False,
    ) -> None:
        self.conventions = conventions
        self.approval_mode = approval_mode
        self.allow_unsafe = allow_unsafe
        self.phase_brief: str = ""  # Full phase prompt — set by orchestrator
        self.project_dir: Path | None = None

    def execute(
        self,
        task: AgentTask,
        project_dir: Path,
        on_progress: Callable[[ProgressEvent], None],
    ) -> AgentResult:
        """Run the backend CLI as a subprocess and stream progress events."""
        self.project_dir = project_dir
        command = self.build_cmd(self.build_prompt(task), model=task.model)
        reporter = _TaskProgressReporter.for_task(task, on_progress)
        reporter.emit("started", "Working...")
        started_at = time.monotonic()

        with workspace_write_permission(self.backend, self.approval_mode, project_dir):
            try:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(project_dir),
                    text=True,
                )
            except FileNotFoundError:
                summary = (
                    "The selected AI tool could not start. Run `forge doctor`, fix the reported "
                    "setup issue, then retry with `--resume`."
                )
                reporter.emit("failed", summary)
                return _agent_result(
                    task,
                    summary=summary,
                    success=False,
                    duration=time.monotonic() - started_at,
                    returncode=-1,
                )

            outcome = _stream_process(process, started_at=started_at, reporter=reporter)
        if outcome.timed_out:
            summary = (
                "This task took longer than allowed. Your completed work is safe; "
                "retry with `--resume`."
            )
            reporter.emit("failed", summary)
            return _agent_result(
                task,
                summary=summary,
                success=False,
                duration=outcome.duration,
                returncode=outcome.returncode,
            )

        failure_input = "\n".join(outcome.last_lines)
        success = outcome.returncode == 0
        failure = classify_provider_failure(failure_input, returncode=outcome.returncode)
        if (
            success
            and self.backend == "antigravity"
            and is_headless_permission_failure(failure_input)
        ):
            # Antigravity print mode can report a denied tool as exit 0 because
            # the assistant turn itself completed. Forge must not advance the
            # phase when the requested workspace action was denied.
            success = False
            returncode = 1
            summary = failure.summary
            reporter.emit("failed", summary)
        elif success:
            returncode = outcome.returncode
            summary = outcome.last_lines[-1] if outcome.last_lines else "Completed"
            reporter.emit("completed", summary)
        else:
            returncode = outcome.returncode
            summary = (
                "This task stopped before it finished. Your completed work is safe; "
                "run `forge doctor`, then retry with `--resume`."
            )
            reporter.emit("failed", summary)

        return _agent_result(
            task,
            summary=summary,
            success=success,
            duration=outcome.duration,
            returncode=returncode,
        )

    def build_prompt(self, task: AgentTask) -> str:
        raise NotImplementedError

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str:
        raise NotImplementedError

    def parse_plan(self, raw_output: str, phase: str, backend: str) -> DecompositionPlan:
        raise NotImplementedError

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]:
        return build_provider_command(
            self.backend,
            prompt,
            model,
            approval_mode=self.approval_mode,
            allow_unsafe=self.allow_unsafe,
            project_dir=self.project_dir,
        )
