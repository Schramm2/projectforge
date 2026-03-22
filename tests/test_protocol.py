"""Tests for multi-agent orchestration protocol data structures."""

from ubundiforge.protocol import AgentResult, AgentTask, DecompositionPlan, ProgressEvent


class TestAgentTask:
    def test_create_with_required_fields(self):
        task = AgentTask(
            id="task-1",
            description="Set up project skeleton",
            file_territory=["pyproject.toml", "src/"],
            context="",
            dependencies=[],
            phase="architecture",
            backend="claude",
        )
        assert task.id == "task-1"
        assert task.model is None

    def test_create_with_model_override(self):
        task = AgentTask(
            id="task-2",
            description="Write models",
            file_territory=["models/"],
            context="Prior work context",
            dependencies=["task-1"],
            phase="architecture",
            backend="claude",
            model="opus",
        )
        assert task.model == "opus"
        assert task.dependencies == ["task-1"]

    def test_context_defaults_empty(self):
        task = AgentTask(
            id="t",
            description="d",
            file_territory=[],
            context="",
            dependencies=[],
            phase="p",
            backend="b",
        )
        assert task.context == ""


class TestAgentResult:
    def test_create_success(self):
        result = AgentResult(
            task_id="task-1",
            files_created=["src/main.py", "pyproject.toml"],
            files_modified=[],
            summary="Created project skeleton",
            success=True,
            duration=12.5,
            returncode=0,
        )
        assert result.success is True
        assert result.returncode == 0

    def test_create_failure(self):
        result = AgentResult(
            task_id="task-2",
            files_created=[],
            files_modified=[],
            summary="Backend not found",
            success=False,
            duration=0.1,
            returncode=1,
        )
        assert result.success is False


class TestProgressEvent:
    def test_create_started_event(self):
        event = ProgressEvent(
            task_id="task-1",
            agent_label="Project skeleton agent",
            event_type="started",
            message="Setting up project structure",
            timestamp=1000.0,
        )
        assert event.event_type == "started"

    def test_event_types(self):
        for event_type in ("started", "progress", "completed", "failed"):
            event = ProgressEvent(
                task_id="t",
                agent_label="a",
                event_type=event_type,
                message="m",
                timestamp=0.0,
            )
            assert event.event_type == event_type


class TestDecompositionPlan:
    def test_create_plan(self):
        task1 = AgentTask(
            id="task-1",
            description="Skeleton",
            file_territory=["pyproject.toml"],
            context="",
            dependencies=[],
            phase="architecture",
            backend="claude",
        )
        task2 = AgentTask(
            id="task-2",
            description="Models",
            file_territory=["models/"],
            context="",
            dependencies=["task-1"],
            phase="architecture",
            backend="claude",
        )
        plan = DecompositionPlan(
            tasks=[task1, task2],
            execution_order=[["task-1"], ["task-2"]],
            rationale="Skeleton first, then models",
        )
        assert len(plan.tasks) == 2
        assert plan.execution_order == [["task-1"], ["task-2"]]

    def test_single_task_plan(self):
        task = AgentTask(
            id="task-1",
            description="Do everything",
            file_territory=[],
            context="",
            dependencies=[],
            phase="architecture",
            backend="claude",
        )
        plan = DecompositionPlan(
            tasks=[task],
            execution_order=[["task-1"]],
            rationale="Single task fallback",
        )
        assert len(plan.tasks) == 1

    def test_task_lookup(self):
        task1 = AgentTask(
            id="task-1",
            description="A",
            file_territory=[],
            context="",
            dependencies=[],
            phase="p",
            backend="b",
        )
        task2 = AgentTask(
            id="task-2",
            description="B",
            file_territory=[],
            context="",
            dependencies=[],
            phase="p",
            backend="b",
        )
        plan = DecompositionPlan(
            tasks=[task1, task2],
            execution_order=[["task-1", "task-2"]],
            rationale="Parallel",
        )
        task_map = {t.id: t for t in plan.tasks}
        assert task_map["task-1"].description == "A"
        assert task_map["task-2"].description == "B"
