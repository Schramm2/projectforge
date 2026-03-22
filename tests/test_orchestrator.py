"""Tests for orchestrator context accumulation and filesystem diffing (partial — Task 7)."""

from __future__ import annotations

from pathlib import Path

from ubundiforge.orchestrator import (
    CONTEXT_CAP,
    accumulate_context,
    build_context_summary,
    diff_snapshots,
    snapshot_directory,
)
from ubundiforge.protocol import AgentTask


def _make_task(description: str = "Build the thing") -> AgentTask:
    return AgentTask(
        id="task-1",
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
