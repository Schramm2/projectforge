"""Orchestrator — plan/execute/reconcile/report for multi-agent scaffolding."""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ubundiforge.adapters import get_adapter
from ubundiforge.protocol import (
    AgentResult,
    AgentTask,
    DecompositionPlan,
    ProgressEvent,
)

log = logging.getLogger(__name__)

CONTEXT_CAP = 12_000  # characters

# File extensions whose contents are inlined into context summaries
_CODE_EXTENSIONS = {".py", ".ts", ".json"}
_MAX_INLINE_FILES = 10
_MAX_INLINE_LINES = 200


def snapshot_directory(project_dir: Path) -> dict[str, float]:
    """Snapshot all files under *project_dir* with their modification times.

    Returns a mapping of ``{relative_path_str: mtime}`` for every regular file
    found recursively under the directory.
    """
    result: dict[str, float] = {}
    for root, _dirs, files in os.walk(project_dir):
        for name in files:
            abs_path = Path(root) / name
            rel = abs_path.relative_to(project_dir)
            result[str(rel)] = abs_path.stat().st_mtime
    return result


def diff_snapshots(
    before: dict[str, float],
    after: dict[str, float],
) -> tuple[list[str], list[str]]:
    """Compare two snapshots.

    Returns ``(files_created, files_modified)`` where:
    - *files_created* — keys present in *after* but not *before*.
    - *files_modified* — keys present in both but whose mtime increased.
    """
    files_created: list[str] = []
    files_modified: list[str] = []

    for path, mtime in after.items():
        if path not in before:
            files_created.append(path)
        elif mtime > before[path]:
            files_modified.append(path)

    return files_created, files_modified


def build_context_summary(
    task: AgentTask,
    files_created: list[str],
    files_modified: list[str],
    project_dir: Path,
) -> str:
    """Build a context string for *task* after it ran.

    Includes:
    - Task description
    - Lists of files created and modified
    - Inline content (first ``_MAX_INLINE_LINES`` lines) of up to
      ``_MAX_INLINE_FILES`` ``.py`` / ``.ts`` / ``.json`` files.
    """
    lines: list[str] = []
    lines.append(f"## Task: {task.description}")
    lines.append("")

    if files_created:
        lines.append("Files created:")
        for f in files_created:
            lines.append(f"  {f}")

    if files_modified:
        lines.append("Files modified:")
        for f in files_modified:
            lines.append(f"  {f}")

    # Inline code content for up to _MAX_INLINE_FILES eligible files
    all_changed = files_created + files_modified
    eligible = [f for f in all_changed if Path(f).suffix in _CODE_EXTENSIONS][:_MAX_INLINE_FILES]

    for rel in eligible:
        abs_path = project_dir / rel
        if not abs_path.is_file():
            continue
        try:
            content_lines = abs_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        snippet = "\n".join(content_lines[:_MAX_INLINE_LINES])
        lines.append("")
        lines.append(f"### {rel}")
        lines.append("```")
        lines.append(snippet)
        lines.append("```")

    return "\n".join(lines)


def accumulate_context(existing: str, new_summary: str) -> str:
    """Append *new_summary* to *existing* context.

    When the combined length exceeds ``CONTEXT_CAP``:

    1. Split *existing* into double-newline-separated sections (oldest first).
    2. Compress oldest sections: keep only lines starting with
       ``"Completed:"`` or ``"Files created:"`` or ``"Files modified:"``.
    3. If still over cap, drop oldest sections entirely until under cap.

    The most-recent summary always retains its full content.
    """
    separator = "\n\n"
    if existing.strip():
        combined = existing.rstrip() + separator + new_summary.strip()
    else:
        combined = new_summary.strip()

    if len(combined) <= CONTEXT_CAP:
        return combined

    # Split into sections (oldest first)
    sections = combined.split(separator)

    # --- Pass 1: compress older sections (all except the last) ---
    def _compress(section: str) -> str:
        keep_prefixes = ("Completed:", "Files created:", "Files modified:", "## Task:")
        compressed_lines = [
            line for line in section.splitlines() if any(line.startswith(p) for p in keep_prefixes)
        ]
        return "\n".join(compressed_lines)

    compressed: list[str] = []
    for i, section in enumerate(sections):
        if i < len(sections) - 1:
            compressed.append(_compress(section))
        else:
            compressed.append(section)

    combined = separator.join(s for s in compressed if s.strip())
    if len(combined) <= CONTEXT_CAP:
        return combined

    # --- Pass 2: drop oldest sections until within cap ---
    while len(sections) > 1 and len(combined) > CONTEXT_CAP:
        sections.pop(0)
        compressed.pop(0)
        combined = separator.join(s for s in compressed if s.strip())

    # Hard truncate as a last resort (should rarely trigger)
    return combined[:CONTEXT_CAP]


# ---------------------------------------------------------------------------
# Plan / Execute / Reconcile / Report  (Task 8)
# ---------------------------------------------------------------------------

_PLANNING_TIMEOUT = 300  # seconds


def _make_single_task_plan(
    brief: str,
    phase: str,
    backend: str,
) -> DecompositionPlan:
    """Fallback: wrap the entire brief in one task."""
    task = AgentTask(
        id="sole-task",
        description=brief,
        file_territory=[],
        context="",
        dependencies=[],
        phase=phase,
        backend=backend,
    )
    return DecompositionPlan(
        tasks=[task],
        execution_order=[[task.id]],
        rationale="Single-task fallback — planning was skipped or failed.",
    )


def _get_plan(
    adapter,
    brief: str,
    phase: str,
    stack: str,
    backend: str,
    project_dir: Path,
    model: str | None = None,
) -> DecompositionPlan:
    """Ask the adapter CLI for a decomposition plan.

    On failure or un-parseable output, retries once with a
    "respond with JSON only" suffix.  Falls back to a single-task plan.
    """
    planning_prompt = adapter.build_planning_prompt(brief, phase, stack)
    cmd = adapter.build_cmd(planning_prompt, model=model)

    for attempt in range(2):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_PLANNING_TIMEOUT,
                cwd=str(project_dir),
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            log.warning("Planning subprocess error (attempt %d): %s", attempt + 1, exc)
            continue

        if result.returncode != 0:
            log.warning(
                "Planning call returned %d (attempt %d)", result.returncode, attempt + 1
            )
            # Retry with JSON-only suffix
            if attempt == 0:
                cmd = adapter.build_cmd(
                    planning_prompt + "\n\nRespond with JSON only.", model=model
                )
            continue

        plan = adapter.parse_plan(result.stdout, phase=phase, backend=backend)
        if plan is not None:
            return plan

        log.warning("Could not parse plan from output (attempt %d)", attempt + 1)
        if attempt == 0:
            cmd = adapter.build_cmd(
                planning_prompt + "\n\nRespond with JSON only.", model=model
            )

    log.warning("Planning failed after retries — falling back to single task.")
    return _make_single_task_plan(brief, phase, backend)


def _execute_task_graph(
    plan: DecompositionPlan,
    adapter,
    project_dir: Path,
    on_progress: Callable[[ProgressEvent], None],
) -> list[AgentResult]:
    """Walk execution_order groups, executing tasks via *adapter*.

    - Groups with a single task: snapshot per task (accurate attribution).
    - Groups with multiple tasks: one snapshot before the group, one diff
      after all complete. Each task gets the combined diff (known limitation).
    - Tasks whose dependencies failed are skipped.
    """
    task_map: dict[str, AgentTask] = {t.id: t for t in plan.tasks}
    results: list[AgentResult] = []
    failed_ids: set[str] = set()
    accumulated_context = ""

    for group in plan.execution_order:
        # Filter to valid task IDs only
        group_ids = [tid for tid in group if tid in task_map]
        if not group_ids:
            continue

        # Inject accumulated context into each task
        for tid in group_ids:
            task_map[tid].context = accumulated_context

        is_parallel = len(group_ids) > 1

        if is_parallel:
            # --- parallel group: one snapshot for the whole group ---
            before = snapshot_directory(project_dir)

            def _run_task(tid: str) -> AgentResult:
                task = task_map[tid]
                # Check dependencies
                if any(dep in failed_ids for dep in task.dependencies):
                    return AgentResult(
                        task_id=tid,
                        files_created=[],
                        files_modified=[],
                        summary="Skipped: dependency failed",
                        success=False,
                        duration=0.0,
                        returncode=-1,
                    )
                return adapter.execute(task, project_dir, on_progress)

            with ThreadPoolExecutor(max_workers=len(group_ids)) as pool:
                group_results = list(pool.map(_run_task, group_ids))

            # Diff once for the whole group
            after = snapshot_directory(project_dir)
            created, modified = diff_snapshots(before, after)

            # Build ONE combined summary for the group
            group_summaries: list[str] = []
            for res in group_results:
                res.files_created = created
                res.files_modified = modified
                if not res.success:
                    failed_ids.add(res.task_id)
                group_summaries.append(
                    build_context_summary(
                        task_map[res.task_id], created, modified, project_dir
                    )
                )
            combined_summary = "\n\n".join(group_summaries)
            accumulated_context = accumulate_context(accumulated_context, combined_summary)
            results.extend(group_results)

        else:
            # --- sequential (single-task) group: snapshot per task ---
            for tid in group_ids:
                task = task_map[tid]

                # Check dependencies
                if any(dep in failed_ids for dep in task.dependencies):
                    skip_result = AgentResult(
                        task_id=tid,
                        files_created=[],
                        files_modified=[],
                        summary="Skipped: dependency failed",
                        success=False,
                        duration=0.0,
                        returncode=-1,
                    )
                    results.append(skip_result)
                    failed_ids.add(tid)
                    continue

                before = snapshot_directory(project_dir)
                result = adapter.execute(task, project_dir, on_progress)
                after = snapshot_directory(project_dir)
                created, modified = diff_snapshots(before, after)

                result.files_created = created
                result.files_modified = modified

                if not result.success:
                    failed_ids.add(tid)

                summary = build_context_summary(task, created, modified, project_dir)
                accumulated_context = accumulate_context(accumulated_context, summary)
                results.append(result)

    return results


def _reconcile(
    adapter,
    project_dir: Path,
    model: str | None = None,
) -> int:
    """Lightweight cleanup CLI call after all tasks have finished."""
    prompt = (
        "Review the project directory for any conflicts, duplicated code, "
        "or inconsistencies introduced by parallel agents. Fix them."
    )
    cmd = adapter.build_cmd(prompt, model=model)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_PLANNING_TIMEOUT,
            cwd=str(project_dir),
        )
        return result.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        log.warning("Reconciliation failed: %s", exc)
        return 1


def run_phase_orchestrated(
    phase: str,
    backend: str,
    prompt: str,
    project_dir: Path,
    stack: str,
    conventions: str = "",
    model: str | None = None,
    verbose: bool = False,
    phase_context: str | None = None,
) -> int:
    """Main entry point for orchestrated phase execution.

    Returns 0 if all tasks succeeded, 1 if any failed.
    """
    adapter = get_adapter(backend, conventions)
    plan = _get_plan(adapter, prompt, phase, stack, backend, project_dir, model)

    if verbose and len(plan.tasks) > 1:
        log.info(
            "Decomposition plan: %d tasks, %d groups — %s",
            len(plan.tasks),
            len(plan.execution_order),
            plan.rationale,
        )

    def _noop_progress(event: ProgressEvent) -> None:
        pass

    # Single task: execute directly (skip orchestration overhead)
    if len(plan.tasks) == 1:
        task = plan.tasks[0]
        if phase_context:
            task.context = phase_context
        result = adapter.execute(task, project_dir, _noop_progress)
        return 0 if result.success else 1

    # Multi-task: execute the full task graph
    if phase_context:
        for t in plan.tasks:
            t.context = phase_context

    results = _execute_task_graph(plan, adapter, project_dir, on_progress=_noop_progress)

    # Reconcile (non-fatal)
    rc = _reconcile(adapter, project_dir, model)
    if rc != 0:
        log.warning("Reconciliation exited with code %d (non-fatal)", rc)

    return 0 if all(r.success for r in results) else 1
