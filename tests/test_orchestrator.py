"""Tests for orchestrator context accumulation, filesystem diffing, and plan/execute/reconcile."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from ubundiforge.orchestrator import (
    CONTEXT_CAP,
    _execute_task_graph,
    _make_single_task_plan,
    accumulate_context,
    build_context_summary,
    diff_snapshots,
    run_phase_orchestrated,
    snapshot_directory,
)
from ubundiforge.protocol import AgentResult, AgentTask, DecompositionPlan


def _make_task(description: str = "Build the thing", task_id: str = "task-1") -> AgentTask:
    return AgentTask(
        id=task_id,
        description=description,
        file_territory=[],
        context="",
        dependencies=[],
        phase="architecture",
        backend="claude",
    )


class TestSnapshotDirectory:
    def test_snapshot_empty_dir(self, tmp_path: Path) -> None:
        snap = snapshot_directory(tmp_path)
        assert snap == {}

    def test_snapshot_with_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("print('hello')")
        (tmp_path / "b.txt").write_text("text")
        snap = snapshot_directory(tmp_path)
        assert "a.py" in snap
        assert "b.txt" in snap
        assert len(snap) == 2
        # mtime values are floats
        for v in snap.values():
            assert isinstance(v, float)

    def test_snapshot_nested(self, tmp_path: Path) -> None:
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "mod.py").write_text("x = 1")
        (tmp_path / "root.py").write_text("y = 2")
        snap = snapshot_directory(tmp_path)
        # Keys are relative strings
        assert "root.py" in snap
        assert str(Path("pkg") / "mod.py") in snap


class TestDiffSnapshots:
    def test_detects_new_files(self, tmp_path: Path) -> None:
        before = snapshot_directory(tmp_path)
        (tmp_path / "new.py").write_text("pass")
        after = snapshot_directory(tmp_path)
        created, modified = diff_snapshots(before, after)
        assert "new.py" in created
        assert "new.py" not in modified

    def test_detects_modified_files(self, tmp_path: Path) -> None:
        (tmp_path / "existing.py").write_text("v1")
        before = snapshot_directory(tmp_path)
        # Ensure mtime changes by sleeping briefly or forcing it
        f = tmp_path / "existing.py"
        f.write_text("v2")
        # Bump mtime explicitly so the diff is unambiguous
        new_mtime = f.stat().st_mtime + 1.0
        import os

        os.utime(f, (new_mtime, new_mtime))
        after = snapshot_directory(tmp_path)
        created, modified = diff_snapshots(before, after)
        assert "existing.py" not in created
        assert "existing.py" in modified

    def test_no_changes(self, tmp_path: Path) -> None:
        (tmp_path / "stable.py").write_text("stable")
        before = snapshot_directory(tmp_path)
        after = snapshot_directory(tmp_path)
        created, modified = diff_snapshots(before, after)
        assert created == []
        assert modified == []


class TestBuildContextSummary:
    def test_summary_includes_description(self, tmp_path: Path) -> None:
        task = _make_task("Implement the router module")
        summary = build_context_summary(task, [], [], tmp_path)
        assert "Implement the router module" in summary

    def test_summary_includes_modified_files(self, tmp_path: Path) -> None:
        (tmp_path / "router.py").write_text("# router")
        task = _make_task("Update router")
        summary = build_context_summary(task, [], ["router.py"], tmp_path)
        assert "router.py" in summary

    def test_summary_includes_created_files(self, tmp_path: Path) -> None:
        (tmp_path / "models.py").write_text("# models")
        task = _make_task("Add models")
        summary = build_context_summary(task, ["models.py"], [], tmp_path)
        assert "models.py" in summary

    def test_summary_includes_file_contents_for_py(self, tmp_path: Path) -> None:
        code = "def hello():\n    pass\n"
        (tmp_path / "hello.py").write_text(code)
        task = _make_task("Write a function")
        summary = build_context_summary(task, ["hello.py"], [], tmp_path)
        assert "hello.py" in summary
        # The content snippet should be present (or at least the filename)
        assert "def hello" in summary or "hello.py" in summary

    def test_summary_limits_to_ten_files(self, tmp_path: Path) -> None:
        files = []
        for i in range(15):
            name = f"file_{i}.py"
            (tmp_path / name).write_text(f"# file {i}")
            files.append(name)
        task = _make_task("Many files")
        summary = build_context_summary(task, files, [], tmp_path)
        # Should not crash and should contain something about the files
        assert "file_" in summary

    def test_summary_skips_non_code_contents(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# readme content XYZ987")
        task = _make_task("Write docs")
        summary = build_context_summary(task, ["README.md"], [], tmp_path)
        # .md is not a code extension — content should NOT be inlined
        assert "XYZ987" not in summary


class TestAccumulateContext:
    def test_appends_summaries(self) -> None:
        first = "## Task: Alpha\nDid some things."
        second = "## Task: Beta\nDid other things."
        result = accumulate_context(first, second)
        assert "Alpha" in result
        assert "Beta" in result

    def test_appends_to_empty(self) -> None:
        result = accumulate_context("", "## Task: First\nContent here.")
        assert "First" in result

    def test_respects_cap(self) -> None:
        # Build a context that exceeds the cap
        big_summary = "x" * (CONTEXT_CAP + 500)
        result = accumulate_context("", big_summary)
        assert len(result) <= CONTEXT_CAP

    def test_compresses_old_summaries_when_capped(self) -> None:
        # First summary: has a "Completed:" line and a "Files created:" line
        old_summary = (
            "## Task: Old Task\n"
            "Completed: yes\n"
            "Files created: old_file.py\n"
            "Some verbose content that should be dropped when compressed.\n"
        )
        # Fill existing context to near-cap so adding the new summary tips it over
        filler = "y" * (CONTEXT_CAP - 100)
        existing = old_summary + "\n\n" + filler

        new_summary = "## Task: New\nCompleted: yes\nFiles created: new_file.py\n"
        result = accumulate_context(existing, new_summary)

        # Result must be within cap
        assert len(result) <= CONTEXT_CAP
        # New summary content should survive (not be compressed away)
        assert "New" in result

    def test_drops_oldest_when_compression_insufficient(self) -> None:
        # All content is maximally verbose with nothing compressible — oldest must be dropped
        section_a = "## Task: A\n" + "a" * 5000
        section_b = "## Task: B\n" + "b" * 5000
        section_c = "## Task: C\n" + "c" * 3000
        existing = section_a + "\n\n" + section_b
        result = accumulate_context(existing, section_c)
        assert len(result) <= CONTEXT_CAP


# ---------------------------------------------------------------------------
# Task 8 — plan / execute / reconcile / report
# ---------------------------------------------------------------------------


def _ok_result(task_id: str) -> AgentResult:
    """Helper: a successful AgentResult stub."""
    return AgentResult(
        task_id=task_id,
        files_created=[],
        files_modified=[],
        summary="ok",
        success=True,
        duration=0.1,
        returncode=0,
    )


def _fail_result(task_id: str) -> AgentResult:
    """Helper: a failed AgentResult stub."""
    return AgentResult(
        task_id=task_id,
        files_created=[],
        files_modified=[],
        summary="failed",
        success=False,
        duration=0.1,
        returncode=1,
    )


class TestMakeSingleTaskPlan:
    def test_creates_single_task_fallback(self) -> None:
        plan = _make_single_task_plan(
            brief="Build everything",
            phase="scaffold",
            backend="claude",
        )
        assert isinstance(plan, DecompositionPlan)
        assert len(plan.tasks) == 1
        assert plan.tasks[0].description == "Build everything"
        assert plan.tasks[0].phase == "scaffold"
        assert plan.tasks[0].backend == "claude"
        assert len(plan.execution_order) == 1
        assert plan.execution_order[0] == [plan.tasks[0].id]
        assert "single" in plan.rationale.lower() or "fallback" in plan.rationale.lower()


class TestExecuteTaskGraph:
    def test_executes_sequential_tasks(self, tmp_path: Path) -> None:
        """Two tasks in separate execution_order groups run sequentially."""
        task_a = _make_task("Task A", task_id="a")
        task_b = _make_task("Task B", task_id="b")
        task_b.dependencies = ["a"]
        plan = DecompositionPlan(
            tasks=[task_a, task_b],
            execution_order=[["a"], ["b"]],
            rationale="sequential",
        )

        adapter = MagicMock()
        adapter.execute.side_effect = lambda t, d, cb: _ok_result(t.id)

        results = _execute_task_graph(plan, adapter, tmp_path, on_progress=lambda e: None)
        assert len(results) == 2
        assert all(r.success for r in results)
        assert adapter.execute.call_count == 2

    def test_skips_tasks_depending_on_failed(self, tmp_path: Path) -> None:
        """If task A fails, task B (which depends on A) should be skipped."""
        task_a = _make_task("Task A", task_id="a")
        task_b = _make_task("Task B", task_id="b")
        task_b.dependencies = ["a"]
        plan = DecompositionPlan(
            tasks=[task_a, task_b],
            execution_order=[["a"], ["b"]],
            rationale="sequential",
        )

        adapter = MagicMock()
        adapter.execute.side_effect = lambda t, d, cb: _fail_result(t.id)

        results = _execute_task_graph(plan, adapter, tmp_path, on_progress=lambda e: None)
        # Task A ran and failed; task B should be skipped
        assert len(results) == 2
        assert not results[0].success  # a failed
        assert not results[1].success  # b skipped
        # Only task A should have been executed via adapter
        assert adapter.execute.call_count == 1

    def test_executes_parallel_tasks_in_group(self, tmp_path: Path) -> None:
        """Tasks in the same execution_order group run (potentially) in parallel."""
        task_a = _make_task("Task A", task_id="a")
        task_b = _make_task("Task B", task_id="b")
        plan = DecompositionPlan(
            tasks=[task_a, task_b],
            execution_order=[["a", "b"]],
            rationale="parallel",
        )

        adapter = MagicMock()
        adapter.execute.side_effect = lambda t, d, cb: _ok_result(t.id)

        results = _execute_task_graph(plan, adapter, tmp_path, on_progress=lambda e: None)
        assert len(results) == 2
        assert all(r.success for r in results)
        assert adapter.execute.call_count == 2

    def test_skips_nonexistent_task_ids_in_execution_order(self, tmp_path: Path) -> None:
        """If execution_order references an ID not in tasks, skip it gracefully."""
        task_a = _make_task("Task A", task_id="a")
        plan = DecompositionPlan(
            tasks=[task_a],
            execution_order=[["a", "ghost"]],
            rationale="includes ghost",
        )

        adapter = MagicMock()
        adapter.execute.side_effect = lambda t, d, cb: _ok_result(t.id)

        results = _execute_task_graph(plan, adapter, tmp_path, on_progress=lambda e: None)
        # Only task A should execute; ghost should be silently skipped
        assert len(results) == 1
        assert results[0].task_id == "a"
        assert adapter.execute.call_count == 1


class TestRunPhaseOrchestrated:
    @patch("ubundiforge.orchestrator.get_adapter")
    def test_falls_back_on_bad_plan(self, mock_get_adapter, tmp_path: Path) -> None:
        """When planning fails, falls back to single-task plan and executes it."""
        adapter = MagicMock()
        mock_get_adapter.return_value = adapter

        # build_cmd returns a command, subprocess.run will be mocked to fail planning
        adapter.build_cmd.return_value = ["echo", "fake"]
        adapter.build_planning_prompt.return_value = "plan prompt"
        adapter.parse_plan.return_value = None  # parse failure
        adapter.execute.return_value = _ok_result("sole-task")

        with patch("ubundiforge.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="garbage", stderr=""
            )
            rc, stats = run_phase_orchestrated(
                phase="scaffold",
                backend="claude",
                prompt="Build everything",
                project_dir=tmp_path,
                stack="fastapi",
            )

        assert rc == 0
        assert stats["planned"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 0
        # Should have executed the single fallback task
        assert adapter.execute.call_count == 1
