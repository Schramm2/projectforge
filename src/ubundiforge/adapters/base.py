"""CLIAdapterBase — shared subprocess execution for all backend adapters."""

from __future__ import annotations

import subprocess
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from queue import Empty, Queue
from threading import Thread

from ubundiforge.protocol import AgentResult, AgentTask, DecompositionPlan, ProgressEvent
from ubundiforge.subprocess_utils import PHASE_TIMEOUT, sanitize_progress_line


class CLIAdapterBase:
    """Shared subprocess execution — implements ForgeAgent.execute.

    Subclasses override build_prompt, build_planning_prompt, parse_plan, and
    build_cmd to customise prompt construction and command assembly.  This base
    class owns the full subprocess lifecycle: spawn, stream, timeout, and emit
    ProgressEvents.
    """

    def __init__(self, conventions: str = "") -> None:
        self.conventions = conventions

    # ------------------------------------------------------------------
    # ForgeAgent.execute
    # ------------------------------------------------------------------

    def execute(
        self,
        task: AgentTask,
        project_dir: Path,
        on_progress: Callable[[ProgressEvent], None],
    ) -> AgentResult:
        """Run the backend CLI as a subprocess and stream progress events."""
        prompt = self.build_prompt(task)
        cmd = self.build_cmd(prompt, model=task.model)
        label = f"{task.backend}:{task.id}"

        def emit(event_type: str, message: str) -> None:
            on_progress(
                ProgressEvent(
                    task_id=task.id,
                    agent_label=label,
                    event_type=event_type,
                    message=message,
                    timestamp=time.time(),
                )
            )

        emit("started", f"Starting {label}")

        start = time.monotonic()
        last_lines: deque[str] = deque(maxlen=20)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(project_dir),
                text=True,
            )
        except FileNotFoundError:
            duration = time.monotonic() - start
            emit("failed", f"Command not found: {cmd[0]!r}")
            return AgentResult(
                task_id=task.id,
                files_created=[],
                files_modified=[],
                summary=f"Command not found: {cmd[0]!r}",
                success=False,
                duration=duration,
                returncode=-1,
            )

        # Stream stdout on a reader thread so we can enforce PHASE_TIMEOUT.
        line_queue: Queue[str | None] = Queue()

        def _reader() -> None:
            assert proc.stdout is not None
            for raw in proc.stdout:
                line_queue.put(raw)
            line_queue.put(None)  # sentinel

        reader = Thread(target=_reader, daemon=True)
        reader.start()

        timed_out = False
        deadline = start + PHASE_TIMEOUT

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                proc.kill()
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
                emit("progress", clean)

        reader.join(timeout=5)
        returncode = proc.wait()
        duration = time.monotonic() - start

        if timed_out:
            summary = f"Timed out after {PHASE_TIMEOUT}s"
            emit("failed", summary)
            return AgentResult(
                task_id=task.id,
                files_created=[],
                files_modified=[],
                summary=summary,
                success=False,
                duration=duration,
                returncode=returncode,
            )

        success = returncode == 0
        if success:
            summary = last_lines[-1] if last_lines else "Completed"
            emit("completed", summary)
        else:
            summary = "; ".join(last_lines) if last_lines else f"Exited with code {returncode}"
            emit("failed", summary)

        return AgentResult(
            task_id=task.id,
            files_created=[],
            files_modified=[],
            summary=summary,
            success=success,
            duration=duration,
            returncode=returncode,
        )

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    def build_prompt(self, task: AgentTask) -> str:
        raise NotImplementedError

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str:
        raise NotImplementedError

    def parse_plan(self, raw_output: str, phase: str, backend: str) -> DecompositionPlan:
        raise NotImplementedError

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]:
        raise NotImplementedError
