"""Orchestrator — plan/execute/reconcile/report for multi-agent scaffolding."""

from __future__ import annotations

import logging
import os
import subprocess
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from rich.live import Live
from rich.text import Text

from ubundiforge import ui
from ubundiforge.adapters import get_adapter
from ubundiforge.agent_quality import append_agent_quality_signal
from ubundiforge.protocol import (
    AgentResult,
    AgentTask,
    DecompositionPlan,
    ProgressEvent,
)
from ubundiforge.quality import QUALITY_LOG_PATH
from ubundiforge.subprocess_utils import spinner_frame, spinner_style

log = logging.getLogger(__name__)
_console = ui.create_console()

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


def _make_spinner_line(label: str, detail: str, elapsed: float, accent: str = "violet") -> Text:
    """Build a single spinner line for Rich Live displays."""
    frame = spinner_frame(elapsed)
    style = spinner_style(accent, elapsed)
    line = Text()
    line.append(f"  {frame} ", style=f"bold {style}")
    line.append(label, style=f"bold {ui.TEXT_PRIMARY}")
    line.append("  ", style="")
    line.append(detail, style=ui.TEXT_SECONDARY)
    line.append(f"  {elapsed:.0f}s", style=ui.TEXT_MUTED)
    return line


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

    _console.print(ui.status_line(f"Planning decomposition for {phase}...", accent="violet"))
    start = time.monotonic()

    import threading

    plan_result = {"plan": None, "error": None, "done": False}

    def _run_planning():
        for attempt in range(2):
            try:
                result = subprocess.run(
                    cmd if attempt == 0 else adapter.build_cmd(
                        planning_prompt + "\n\nRespond with JSON only.", model=model
                    ),
                    capture_output=True,
                    text=True,
                    timeout=_PLANNING_TIMEOUT,
                    cwd=str(project_dir),
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
                log.warning("Planning subprocess error (attempt %d): %s", attempt + 1, exc)
                continue

            if result.returncode != 0:
                log.warning("Planning call returned %d (attempt %d)", result.returncode, attempt + 1)
                continue

            parsed = adapter.parse_plan(result.stdout, phase=phase, backend=backend)
            if parsed is not None:
                plan_result["plan"] = parsed
                plan_result["done"] = True
                return

            log.warning("Could not parse plan from output (attempt %d)", attempt + 1)

        plan_result["done"] = True

    worker = threading.Thread(target=_run_planning, daemon=True)
    worker.start()

    with Live(console=_console, refresh_per_second=10) as live:
        while not plan_result["done"]:
            elapsed = time.monotonic() - start
            live.update(_make_spinner_line(
                "Planning", f"Asking {backend} to decompose {phase}", elapsed, accent="violet"
            ))
            time.sleep(0.1)

    worker.join(timeout=5)
    elapsed = time.monotonic() - start

    if plan_result["plan"] is not None:
        plan = plan_result["plan"]
        _console.print(ui.status_line(
            f"Plan ready: {len(plan.tasks)} tasks in {elapsed:.0f}s", accent="aqua"
        ))
        return plan

    _console.print(ui.status_line(
        f"Planning failed — falling back to standard mode ({elapsed:.0f}s)", accent="amber"
    ))
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
                    build_context_summary(task_map[res.task_id], created, modified, project_dir)
                )
                _task = task_map[res.task_id]
                append_agent_quality_signal(
                    log_path=QUALITY_LOG_PATH,
                    phase=_task.phase,
                    backend=_task.backend,
                    task_id=res.task_id,
                    task_description=_task.description,
                    success=res.success,
                    duration=res.duration,
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

                append_agent_quality_signal(
                    log_path=QUALITY_LOG_PATH,
                    phase=task.phase,
                    backend=task.backend,
                    task_id=tid,
                    task_description=task.description,
                    success=result.success,
                    duration=result.duration,
                )

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
    import threading

    prompt = (
        "Review the project directory for any conflicts, duplicated code, "
        "or inconsistencies introduced by parallel agents. Fix them."
    )
    cmd = adapter.build_cmd(prompt, model=model)
    start = time.monotonic()
    reconcile_result = {"returncode": 1, "done": False}

    def _run():
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_PLANNING_TIMEOUT,
                cwd=str(project_dir),
            )
            reconcile_result["returncode"] = result.returncode
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            log.warning("Reconciliation failed: %s", exc)
        reconcile_result["done"] = True

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()

    with Live(console=_console, refresh_per_second=10) as live:
        while not reconcile_result["done"]:
            elapsed = time.monotonic() - start
            live.update(_make_spinner_line(
                "Reconciling", "Checking for conflicts and fixing imports", elapsed, accent="plum"
            ))
            time.sleep(0.1)

    worker.join(timeout=5)
    elapsed = time.monotonic() - start

    rc = reconcile_result["returncode"]
    if rc == 0:
        _console.print(ui.status_line(f"Reconciliation complete ({elapsed:.0f}s)", accent="aqua"))
    else:
        _console.print(ui.status_line(f"Reconciliation had issues ({elapsed:.0f}s) — non-fatal", accent="amber"))
    return rc


def map_progress_to_activity(event: ProgressEvent) -> str:
    """Convert a ProgressEvent into a single activity feed string.

    - "started"   -> "{agent_label}: {message}"
    - "progress"  -> "{agent_label}: {message}"
    - "completed" -> "{agent_label}: Done"
    - "failed"    -> "{agent_label}: Failed — {message}"
    """
    if event.event_type == "completed":
        return f"{event.agent_label}: Done"
    if event.event_type == "failed":
        return f"{event.agent_label}: Failed \u2014 {event.message}"
    # "started" and "progress" both forward the message
    return f"{event.agent_label}: {event.message}"


def _render_decomposition_plan(plan: DecompositionPlan) -> None:
    """Render a DecompositionPlan to the console using Rich primitives."""
    console = ui.create_console()
    task_map = {t.id: t for t in plan.tasks}

    lines: list = []

    if plan.rationale:
        lines.append(ui.subtle(plan.rationale))

    for step_idx, group in enumerate(plan.execution_order, start=1):
        valid_ids = [tid for tid in group if tid in task_map]
        if not valid_ids:
            continue

        is_parallel = len(valid_ids) > 1
        label_suffix = " (parallel)" if is_parallel else ""

        header = ui.highlight(
            f"Step {step_idx}{label_suffix}",
            accent="violet",
            bold=True,
        )
        lines.append(header)

        for tid in valid_ids:
            task = task_map[tid]
            lines.append(ui.bullet(task.description))
            if task.file_territory:
                territory = ", ".join(task.file_territory)
                lines.append(ui.muted(f"  files: {territory}"))

    panel = ui.make_panel(
        ui.grouped_lines(lines),
        title="Decomposition Plan",
        accent="violet",
    )
    console.print(panel)


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
) -> tuple[int, dict]:
    """Main entry point for orchestrated phase execution.

    Returns ``(returncode, agent_stats)`` where *returncode* is 0 if all tasks
    succeeded (1 otherwise) and *agent_stats* is a dict with keys:
    ``planned``, ``completed``, ``failed``.
    """
    adapter = get_adapter(backend, conventions)
    plan = _get_plan(adapter, prompt, phase, stack, backend, project_dir, model)

    if len(plan.tasks) > 1:
        _render_decomposition_plan(plan)

    # Activity tracking for subagent progress
    _activities: list[dict] = []
    _current_activity = ""

    def _on_progress(event: ProgressEvent) -> None:
        nonlocal _current_activity
        text = map_progress_to_activity(event)
        if event.event_type == "started":
            # Mark previous as done, add new active entry
            if _activities:
                _activities[-1]["completed"] = True
            _activities.append({"summary": text, "completed": False})
        elif event.event_type in ("completed", "failed"):
            # Mark current task as done
            if _activities:
                _activities[-1]["completed"] = True
                _activities[-1]["summary"] = text
        _current_activity = text

    # Single task: execute directly (skip orchestration overhead)
    if len(plan.tasks) == 1:
        task = plan.tasks[0]
        if phase_context:
            task.context = phase_context
        result = adapter.execute(task, project_dir, _on_progress)
        success = result.success
        stats = {"planned": 1, "completed": 1 if success else 0, "failed": 0 if success else 1}
        return (0 if success else 1, stats)

    # Multi-task: execute the full task graph with live progress display
    if phase_context:
        for t in plan.tasks:
            t.context = phase_context

    import threading

    exec_done = {"done": False}
    exec_results: list[AgentResult] = []

    def _run_graph():
        result = _execute_task_graph(plan, adapter, project_dir, on_progress=_on_progress)
        exec_results.extend(result)
        exec_done["done"] = True

    exec_start = time.monotonic()
    worker = threading.Thread(target=_run_graph, daemon=True)
    worker.start()

    with Live(console=_console, refresh_per_second=10) as live:
        while not exec_done["done"]:
            elapsed = time.monotonic() - exec_start
            visible = _activities[-6:] if _activities else []
            loader = ui.make_loader_panel(
                f"{phase} agents",
                _current_activity or "Starting subagent tasks...",
                elapsed=elapsed,
                spinner_frame=spinner_frame(elapsed),
                spinner_style=spinner_style("violet", elapsed),
                accent="violet",
                activities=visible if visible else None,
            )
            live.update(loader)
            time.sleep(0.1)

    worker.join(timeout=5)
    elapsed = time.monotonic() - exec_start
    results = exec_results

    # Render subagent results panel
    completed_count = sum(1 for r in results if r.success)
    failed_count = len(results) - completed_count
    task_map = {t.id: t for t in plan.tasks}

    summary_lines: list[Text] = []
    for r in results:
        task = task_map.get(r.task_id)
        desc = task.description[:60] if task else r.task_id
        if len(desc) < len(task.description if task else r.task_id):
            desc = desc.rstrip() + "..."
        line = Text("  ")
        if r.success:
            line.append("✓ ", style=ui.ACCENTS["aqua"])
            line.append(desc, style=ui.TEXT_SECONDARY)
            line.append(f"  {r.duration:.0f}s", style=ui.TEXT_MUTED)
        else:
            line.append("✗ ", style=ui.ACCENTS["plum"])
            line.append(desc, style=ui.TEXT_SECONDARY)
            line.append(f"  {r.summary[:40]}", style=ui.TEXT_MUTED)
        summary_lines.append(line)

    # Header line
    header = Text()
    header.append(f"  {completed_count}", style=f"bold {ui.ACCENTS['aqua']}")
    header.append(" completed", style=ui.TEXT_SECONDARY)
    if failed_count:
        header.append(f"  {failed_count}", style=f"bold {ui.ACCENTS['plum']}")
        header.append(" failed", style=ui.TEXT_SECONDARY)
    header.append(f"  ({elapsed:.0f}s total)", style=ui.TEXT_MUTED)

    accent = "aqua" if failed_count == 0 else "amber"
    _console.print(ui.make_panel(
        ui.grouped_lines([header, Text()] + summary_lines),
        title="Subagent Results",
        accent=accent,
    ))

    # Reconcile (non-fatal)
    rc = _reconcile(adapter, project_dir, model)
    if rc != 0:
        log.warning("Reconciliation exited with code %d (non-fatal)", rc)

    planned = len(results)
    stats = {"planned": planned, "completed": completed_count, "failed": failed_count}
    return (0 if all(r.success for r in results) else 1, stats)
