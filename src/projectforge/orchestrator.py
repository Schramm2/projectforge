"""Orchestrator — plan/execute/reconcile/report for multi-agent scaffolding."""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict

from rich.live import Live
from rich.text import Text

from projectforge import ui
from projectforge.adapters import get_adapter
from projectforge.agent_quality import append_agent_quality_signal
from projectforge.protocol import (
    AgentResult,
    AgentTask,
    DecompositionPlan,
    ProgressEvent,
)
from projectforge.quality import QUALITY_LOG_PATH
from projectforge.subprocess_utils import spinner_frame, spinner_style

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
        rationale=(
            "Forge is continuing with the standard workflow because task planning was unavailable."
        ),
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

    plan_result = {"plan": None, "error": None, "done": False}

    def _run_planning():
        for attempt in range(2):
            try:
                result = subprocess.run(
                    cmd
                    if attempt == 0
                    else adapter.build_cmd(
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
                log.warning(
                    "Planning call returned %d (attempt %d)",
                    result.returncode,
                    attempt + 1,
                )
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
            live.update(
                _make_spinner_line(
                    "Planning", f"Asking {backend} to decompose {phase}", elapsed, accent="violet"
                )
            )
            time.sleep(0.1)

    worker.join(timeout=5)
    elapsed = time.monotonic() - start

    if plan_result["plan"] is not None:
        plan = plan_result["plan"]
        _console.print(
            ui.status_line(f"Plan ready: {len(plan.tasks)} tasks in {elapsed:.0f}s", accent="aqua")
        )
        return plan

    _console.print(
        ui.status_line(
            "Forge could not create a task plan, so it will continue with the standard workflow.",
            accent="amber",
        )
    )
    return _make_single_task_plan(brief, phase, backend)


_DEPENDENCY_FAILURE_SUMMARY = (
    "Not run because an earlier task did not finish. Fix the earlier "
    "issue, then retry with `--resume`."
)


@dataclass
class _TaskGraphExecution:
    """Own task dependency, filesystem attribution, and context bookkeeping."""

    plan: DecompositionPlan
    adapter: object
    project_dir: Path
    on_progress: Callable[[ProgressEvent], None]
    task_map: dict[str, AgentTask] = field(init=False)
    results: list[AgentResult] = field(default_factory=list)
    failed_task_ids: set[str] = field(default_factory=set)
    accumulated_context: str = ""

    def __post_init__(self) -> None:
        self.task_map = {task.id: task for task in self.plan.tasks}

    def run(self) -> list[AgentResult]:
        for planned_group in self.plan.execution_order:
            task_ids = [task_id for task_id in planned_group if task_id in self.task_map]
            if not task_ids:
                continue
            self._share_completed_work_with(task_ids)
            if len(task_ids) == 1:
                self._run_sequential_task(task_ids[0])
            else:
                self._run_parallel_group(task_ids)
        return self.results

    def _share_completed_work_with(self, task_ids: list[str]) -> None:
        for task_id in task_ids:
            self.task_map[task_id].context = self.accumulated_context

    def _dependency_failed(self, task: AgentTask) -> bool:
        return any(dependency in self.failed_task_ids for dependency in task.dependencies)

    def _skipped_result(self, task_id: str) -> AgentResult:
        return AgentResult(
            task_id=task_id,
            files_created=[],
            files_modified=[],
            summary=_DEPENDENCY_FAILURE_SUMMARY,
            success=False,
            duration=0.0,
            returncode=-1,
        )

    def _execute_or_skip(self, task_id: str) -> AgentResult:
        task = self.task_map[task_id]
        if self._dependency_failed(task):
            return self._skipped_result(task_id)
        return self.adapter.execute(task, self.project_dir, self.on_progress)

    def _record_quality_signal(self, result: AgentResult) -> None:
        task = self.task_map[result.task_id]
        append_agent_quality_signal(
            log_path=QUALITY_LOG_PATH,
            phase=task.phase,
            backend=task.backend,
            task_id=result.task_id,
            task_description=task.description,
            success=result.success,
            duration=result.duration,
        )

    def _record_failure(self, result: AgentResult) -> None:
        if not result.success:
            self.failed_task_ids.add(result.task_id)

    def _context_summary_for(
        self,
        result: AgentResult,
        files_created: list[str],
        files_modified: list[str],
    ) -> str:
        return build_context_summary(
            self.task_map[result.task_id],
            files_created,
            files_modified,
            self.project_dir,
        )

    def _run_sequential_task(self, task_id: str) -> None:
        task = self.task_map[task_id]
        if self._dependency_failed(task):
            result = self._skipped_result(task_id)
            self.results.append(result)
            self.failed_task_ids.add(task_id)
            return

        before = snapshot_directory(self.project_dir)
        result = self.adapter.execute(task, self.project_dir, self.on_progress)
        created, modified = diff_snapshots(before, snapshot_directory(self.project_dir))
        result.files_created = created
        result.files_modified = modified

        self._record_failure(result)
        self._record_quality_signal(result)
        summary = self._context_summary_for(result, created, modified)
        self.accumulated_context = accumulate_context(self.accumulated_context, summary)
        self.results.append(result)

    def _run_parallel_group(self, task_ids: list[str]) -> None:
        before = snapshot_directory(self.project_dir)
        with ThreadPoolExecutor(max_workers=len(task_ids)) as pool:
            group_results = list(pool.map(self._execute_or_skip, task_ids))
        created, modified = diff_snapshots(before, snapshot_directory(self.project_dir))

        summaries: list[str] = []
        for result in group_results:
            result.files_created = created
            result.files_modified = modified
            self._record_failure(result)
            self._record_quality_signal(result)
            summaries.append(self._context_summary_for(result, created, modified))

        combined_summary = "\n\n".join(summaries)
        self.accumulated_context = accumulate_context(
            self.accumulated_context,
            combined_summary,
        )
        self.results.extend(group_results)


def _execute_task_graph(
    plan: DecompositionPlan,
    adapter,
    project_dir: Path,
    on_progress: Callable[[ProgressEvent], None],
) -> list[AgentResult]:
    """Execute valid task groups, preserving group-level parallel attribution."""
    return _TaskGraphExecution(plan, adapter, project_dir, on_progress).run()


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
            live.update(
                _make_spinner_line(
                    "Reconciling",
                    "Checking for conflicts and fixing imports",
                    elapsed,
                    accent="plum",
                )
            )
            time.sleep(0.1)

    worker.join(timeout=5)
    elapsed = time.monotonic() - start

    rc = reconcile_result["returncode"]
    if rc == 0:
        _console.print(ui.status_line(f"Reconciliation complete ({elapsed:.0f}s)", accent="aqua"))
    else:
        msg = (
            "Forge could not run the final consistency pass. Review the generated project "
            "before using it."
        )
        _console.print(ui.status_line(msg, accent="amber"))
    return rc


def map_progress_to_activity(event: ProgressEvent) -> str:
    """Convert a ProgressEvent into a single activity feed string.

    - "started"   -> "{agent_label}: {message}"
    - "progress"  -> "{agent_label}: {message}"
    - "completed" -> "{agent_label}: Done"
    - "failed"    -> a stable recovery-safe failure summary
    """
    if event.event_type == "completed":
        return f"{event.agent_label}: Done"
    if event.event_type == "failed":
        return "A planned task stopped before it finished. Forge will preserve completed work."
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


class _Activity(TypedDict):
    summary: str
    completed: bool


class _AgentStats(TypedDict):
    planned: int
    completed: int
    failed: int


@dataclass
class _ActivityFeed:
    """Translate protocol events into the compact live activity history."""

    activities: list[_Activity] = field(default_factory=list)
    current: str = ""

    def record(self, event: ProgressEvent) -> None:
        text = map_progress_to_activity(event)
        if event.event_type == "started":
            if self.activities:
                self.activities[-1]["completed"] = True
            self.activities.append({"summary": text, "completed": False})
        elif event.event_type in ("completed", "failed") and self.activities:
            self.activities[-1]["completed"] = True
            self.activities[-1]["summary"] = text
        self.current = text

    @property
    def visible_activities(self) -> list[_Activity] | None:
        return self.activities[-6:] or None


def _stats_for(results: list[AgentResult]) -> _AgentStats:
    completed = sum(1 for result in results if result.success)
    return {
        "planned": len(results),
        "completed": completed,
        "failed": len(results) - completed,
    }


def _run_single_planned_task(
    task: AgentTask,
    adapter,
    project_dir: Path,
    activity_feed: _ActivityFeed,
    phase_context: str | None,
) -> tuple[int, _AgentStats]:
    if phase_context:
        task.context = phase_context
    result = adapter.execute(task, project_dir, activity_feed.record)
    stats = _stats_for([result])
    return (0 if result.success else 1, stats)


def _run_task_graph_with_live_progress(
    plan: DecompositionPlan,
    adapter,
    project_dir: Path,
    phase: str,
    activity_feed: _ActivityFeed,
) -> tuple[list[AgentResult], float]:
    execution_done = {"done": False}
    results: list[AgentResult] = []

    def _run_graph() -> None:
        results.extend(
            _execute_task_graph(
                plan,
                adapter,
                project_dir,
                on_progress=activity_feed.record,
            )
        )
        execution_done["done"] = True

    started_at = time.monotonic()
    worker = threading.Thread(target=_run_graph, daemon=True)
    worker.start()

    with Live(console=_console, refresh_per_second=10) as live:
        while not execution_done["done"]:
            elapsed = time.monotonic() - started_at
            live.update(
                ui.make_loader_panel(
                    f"{phase} agents",
                    activity_feed.current or "Starting subagent tasks...",
                    elapsed=elapsed,
                    spinner_frame=spinner_frame(elapsed),
                    spinner_style=spinner_style("violet", elapsed),
                    accent="violet",
                    activities=activity_feed.visible_activities,
                )
            )
            time.sleep(0.1)

    worker.join(timeout=5)
    return results, time.monotonic() - started_at


def _task_description(result: AgentResult, task_map: dict[str, AgentTask]) -> str:
    task = task_map.get(result.task_id)
    description = task.description if task else result.task_id
    if len(description) <= 60:
        return description
    return description[:60].rstrip() + "..."


def _render_agent_results(
    plan: DecompositionPlan,
    results: list[AgentResult],
    elapsed: float,
) -> _AgentStats:
    stats = _stats_for(results)
    task_map = {task.id: task for task in plan.tasks}
    summary_lines: list[Text] = []

    for result in results:
        line = Text("  ")
        description = _task_description(result, task_map)
        if result.success:
            line.append("✓ ", style=ui.ACCENTS["aqua"])
            line.append(description, style=ui.TEXT_SECONDARY)
            line.append(f"  {result.duration:.0f}s", style=ui.TEXT_MUTED)
        else:
            line.append("✗ ", style=ui.ACCENTS["plum"])
            line.append(description, style=ui.TEXT_SECONDARY)
            line.append(f"  {result.summary[:40]}", style=ui.TEXT_MUTED)
        summary_lines.append(line)

    header = Text()
    header.append(f"  {stats['completed']}", style=f"bold {ui.ACCENTS['aqua']}")
    header.append(" completed", style=ui.TEXT_SECONDARY)
    if stats["failed"]:
        header.append(f"  {stats['failed']}", style=f"bold {ui.ACCENTS['plum']}")
        header.append(" failed", style=ui.TEXT_SECONDARY)
    header.append(f"  ({elapsed:.0f}s total)", style=ui.TEXT_MUTED)

    _console.print(
        ui.make_panel(
            ui.grouped_lines([header, Text()] + summary_lines),
            title="Subagent Results",
            accent="aqua" if stats["failed"] == 0 else "amber",
        )
    )
    return stats


def run_phase_orchestrated(
    phase: str,
    backend: str,
    prompt: str,
    project_dir: Path,
    stack: str,
    conventions: str = "",
    model: str | None = None,
    verbose: bool = True,
    phase_context: str | None = None,
    approval_mode: str = "safe",
    allow_unsafe: bool = False,
) -> tuple[int, dict]:
    """Main entry point for orchestrated phase execution.

    Returns ``(returncode, agent_stats)`` where *returncode* is 0 if all tasks
    succeeded (1 otherwise) and *agent_stats* is a dict with keys:
    ``planned``, ``completed``, ``failed``.
    """
    adapter = get_adapter(
        backend,
        conventions,
        approval_mode=approval_mode,
        allow_unsafe=allow_unsafe,
    )
    adapter.project_dir = project_dir
    adapter.phase_brief = prompt
    plan = _get_plan(adapter, prompt, phase, stack, backend, project_dir, model)

    if len(plan.tasks) > 1:
        _render_decomposition_plan(plan)

    activity_feed = _ActivityFeed()
    if len(plan.tasks) == 1:
        return _run_single_planned_task(
            plan.tasks[0],
            adapter,
            project_dir,
            activity_feed,
            phase_context,
        )

    if phase_context:
        for task in plan.tasks:
            task.context = phase_context

    results, elapsed = _run_task_graph_with_live_progress(
        plan,
        adapter,
        project_dir,
        phase,
        activity_feed,
    )
    stats = _render_agent_results(plan, results, elapsed)

    # Reconcile (non-fatal)
    rc = _reconcile(adapter, project_dir, model)
    if rc != 0:
        log.warning("Reconciliation exited with code %d (non-fatal)", rc)

    return (0 if all(r.success for r in results) else 1, stats)
