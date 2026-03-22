"""Tests for CLIAdapterBase subprocess execution."""

import sys
from pathlib import Path  # noqa: E402

from ubundiforge.adapters.base import CLIAdapterBase
from ubundiforge.protocol import AgentTask, ProgressEvent

# ---------------------------------------------------------------------------
# Stub concrete adapter using echo / false for testing
# ---------------------------------------------------------------------------


class StubAdapter(CLIAdapterBase):
    """Concrete adapter that uses shell commands for testing."""

    def build_prompt(self, task: AgentTask) -> str:
        return f"Do: {task.description}"

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str:
        return f"Plan: {brief}"

    def parse_plan(self, raw_output: str, phase: str, backend: str):
        raise NotImplementedError

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]:
        return ["echo", prompt]


class FailingAdapter(CLIAdapterBase):
    """Concrete adapter whose command always exits non-zero."""

    def build_prompt(self, task: AgentTask) -> str:
        return "fail"

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str:
        return "fail plan"

    def parse_plan(self, raw_output: str, phase: str, backend: str):
        raise NotImplementedError

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]:
        # 'false' exits with code 1 on all POSIX systems
        return [sys.executable, "-c", "import sys; sys.exit(1)"]


class MissingCmdAdapter(CLIAdapterBase):
    """Concrete adapter that names a command that does not exist."""

    def build_prompt(self, task: AgentTask) -> str:
        return "missing"

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str:
        return "missing plan"

    def parse_plan(self, raw_output: str, phase: str, backend: str):
        raise NotImplementedError

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]:
        return ["__forge_nonexistent_cmd_xyz__", prompt]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(description: str = "Scaffold the project") -> AgentTask:
    return AgentTask(
        id="task-1",
        description=description,
        file_territory=["src/"],
        context="",
        dependencies=[],
        phase="architecture",
        backend="claude",
    )


# ---------------------------------------------------------------------------
# TestCLIAdapterBaseInit
# ---------------------------------------------------------------------------


class TestCLIAdapterBaseInit:
    def test_stores_conventions(self):
        adapter = StubAdapter(conventions="## My conventions\n")
        assert adapter.conventions == "## My conventions\n"

    def test_empty_conventions(self):
        adapter = StubAdapter()
        assert adapter.conventions == ""


# ---------------------------------------------------------------------------
# TestCLIAdapterBaseExecute
# ---------------------------------------------------------------------------


class TestCLIAdapterBaseExecute:
    def test_execute_successful_task(self, tmp_path: Path):
        adapter = StubAdapter()
        task = _make_task()
        events: list[ProgressEvent] = []

        result = adapter.execute(task, tmp_path, events.append)

        assert result.success is True
        assert result.returncode == 0
        assert result.task_id == "task-1"
        assert isinstance(result.duration, float)
        assert result.duration >= 0.0

    def test_execute_emits_started_event(self, tmp_path: Path):
        adapter = StubAdapter()
        task = _make_task()
        events: list[ProgressEvent] = []

        adapter.execute(task, tmp_path, events.append)

        event_types = [e.event_type for e in events]
        assert "started" in event_types

    def test_execute_started_event_has_correct_task_id(self, tmp_path: Path):
        adapter = StubAdapter()
        task = _make_task()
        events: list[ProgressEvent] = []

        adapter.execute(task, tmp_path, events.append)

        started = next(e for e in events if e.event_type == "started")
        assert started.task_id == "task-1"

    def test_execute_emits_completed_event(self, tmp_path: Path):
        adapter = StubAdapter()
        task = _make_task()
        events: list[ProgressEvent] = []

        adapter.execute(task, tmp_path, events.append)

        event_types = [e.event_type for e in events]
        assert "completed" in event_types

    def test_execute_completed_event_has_correct_task_id(self, tmp_path: Path):
        adapter = StubAdapter()
        task = _make_task()
        events: list[ProgressEvent] = []

        adapter.execute(task, tmp_path, events.append)

        completed = next(e for e in events if e.event_type == "completed")
        assert completed.task_id == "task-1"

    def test_execute_captures_last_lines_on_failure(self, tmp_path: Path):
        adapter = FailingAdapter()
        task = _make_task()
        events: list[ProgressEvent] = []

        result = adapter.execute(task, tmp_path, events.append)

        assert result.success is False
        assert result.returncode != 0
        event_types = [e.event_type for e in events]
        assert "failed" in event_types

    def test_execute_failed_event_has_correct_task_id(self, tmp_path: Path):
        adapter = FailingAdapter()
        task = _make_task()
        events: list[ProgressEvent] = []

        adapter.execute(task, tmp_path, events.append)

        failed = next(e for e in events if e.event_type == "failed")
        assert failed.task_id == "task-1"

    def test_execute_files_created_empty(self, tmp_path: Path):
        """Orchestrator fills files_created — adapter leaves them empty."""
        adapter = StubAdapter()
        task = _make_task()

        result = adapter.execute(task, tmp_path, lambda e: None)

        assert result.files_created == []
        assert result.files_modified == []

    def test_execute_missing_command_returns_failure(self, tmp_path: Path):
        adapter = MissingCmdAdapter()
        task = _make_task()
        events: list[ProgressEvent] = []

        result = adapter.execute(task, tmp_path, events.append)

        assert result.success is False
        event_types = [e.event_type for e in events]
        assert "failed" in event_types

    def test_execute_events_ordered_started_first(self, tmp_path: Path):
        adapter = StubAdapter()
        task = _make_task()
        events: list[ProgressEvent] = []

        adapter.execute(task, tmp_path, events.append)

        assert events[0].event_type == "started"

    def test_execute_events_end_with_terminal_event(self, tmp_path: Path):
        adapter = StubAdapter()
        task = _make_task()
        events: list[ProgressEvent] = []

        adapter.execute(task, tmp_path, events.append)

        assert events[-1].event_type in ("completed", "failed")

    def test_execute_summary_non_empty_on_success(self, tmp_path: Path):
        adapter = StubAdapter()
        task = _make_task()

        result = adapter.execute(task, tmp_path, lambda e: None)

        assert isinstance(result.summary, str)
        assert len(result.summary) > 0

    def test_execute_progress_events_have_timestamps(self, tmp_path: Path):
        adapter = StubAdapter()
        task = _make_task()
        events: list[ProgressEvent] = []

        adapter.execute(task, tmp_path, events.append)

        for event in events:
            assert isinstance(event.timestamp, float)
            assert event.timestamp > 0
