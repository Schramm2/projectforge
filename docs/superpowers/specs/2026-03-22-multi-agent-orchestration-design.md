# Multi-Agent Orchestration Framework — Design Spec

**Date:** 2026-03-22
**Status:** Draft
**Scope:** Forge scaffolding phases decomposed into multi-agent workflows

---

## Problem

Today, each scaffold phase sends one monolithic prompt to a single CLI subprocess. The backend receives a large brief and must handle everything — project structure, data layer, API routes, config, CI — in one pass. This limits quality because:

- A single agent can't specialize on each concern
- No opportunity for agents to build on each other's work incrementally
- One failure in a complex brief can derail the entire phase
- No visibility into what the backend is actually working on at a granular level

## Solution

Introduce a multi-agent orchestration layer that decomposes each scaffold phase into focused subagent tasks. An orchestrator plans the decomposition, executes tasks through focused CLI calls, and passes context between subagents so each builds on prior work.

**Key constraint:** No SDK dependencies, no API keys, no pay-per-token billing. Everything works through the existing free CLI tools (Claude Code, Gemini CLI, Codex CLI).

---

## Architecture

### New Modules

```
src/ubundiforge/
  orchestrator.py          # Plan, execute, reconcile, report
  protocol.py              # ForgeAgent protocol, data structures
  subprocess_utils.py      # Shared subprocess patterns (extracted from runner.py)
  adapters/
    __init__.py
    base.py                # CLIAdapterBase — ForgeAgent implementation using subprocess_utils
    claude_adapter.py      # Prompt formatting for claude -p
    gemini_adapter.py      # Prompt formatting for gemini -p
    codex_adapter.py       # Prompt formatting for codex exec
```

### Integration Point

```
cli.py (orchestration)
  |
  v
router.py (picks backends per phase — unchanged)
  |
  v
orchestrator.py — receives phase + backend assignment
  |               makes a planning CLI call to decompose the phase
  |               walks the task graph with focused CLI calls per subagent
  |               accumulates context between tasks via filesystem reads
  |
  v
protocol.py — ForgeAgent protocol, AgentTask, AgentResult, ProgressEvent
  |
  v
adapters/ — one per backend, thin prompt formatting + CLI command building
```

The existing `runner.py` stays untouched. Without `--agents`, forge works exactly as today. With `--agents`, `cli.py` routes through the orchestrator instead of calling `run_ai()` directly.

---

## Protocol

### Data Structures

```python
@dataclass
class AgentTask:
    """A unit of work assigned to a subagent."""
    id: str                          # unique task identifier
    description: str                 # what this subagent should accomplish
    file_territory: list[str]        # suggested files/directories to own
    context: str                     # cumulative context from prior subagents
    dependencies: list[str]          # task IDs that must complete first
    phase: str                       # which scaffold phase this belongs to
    backend: str                     # which backend to route to
    model: str | None = None         # optional model override for this task

@dataclass
class AgentResult:
    """What a subagent produces."""
    task_id: str
    files_created: list[str]         # paths written
    files_modified: list[str]        # paths changed
    summary: str                     # natural language summary of what was done
    success: bool
    duration: float
    returncode: int                  # subprocess exit code

@dataclass
class ProgressEvent:
    """Emitted by adapters, consumed by the UI layer."""
    task_id: str
    agent_label: str                 # e.g. "Data layer agent"
    event_type: str                  # "started" | "progress" | "completed" | "failed"
    message: str                     # human-readable activity line
    timestamp: float

@dataclass
class DecompositionPlan:
    """Output of the planning call."""
    tasks: list[AgentTask]
    execution_order: list[list[str]] # groups of task IDs — each group runs in parallel,
                                     # groups execute sequentially
    rationale: str                   # why this decomposition was chosen
```

### ForgeAgent Protocol

```python
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
```

`CLIAdapterBase` (in `adapters/base.py`) provides the shared subprocess execution logic — stdout streaming, progress event extraction, timeout handling. Each backend adapter (e.g., `ClaudeAdapter`) subclasses `CLIAdapterBase` and implements the `ForgeAgent` protocol. The base class provides `execute`; subclasses override `build_prompt`, `build_planning_prompt`, `parse_plan`, and `build_cmd`.

Execution is synchronous. Concurrency comes from `ThreadPoolExecutor`, consistent with the existing `run_ai_parallel` pattern.

### Shared Subprocess Infrastructure

Common subprocess patterns are extracted from `runner.py` into `subprocess_utils.py`: ANSI stripping (`_ANSI_RE`, `_sanitize_progress_line`), progress line classification (`_is_noisy_progress_line`, `_summarize_output_line`), spinner animation, and timeout constants. Both `runner.py` and `adapters/base.py` import from this shared module.

**Stderr handling:** Adapters merge stderr into stdout (`stderr=subprocess.STDOUT`), matching the existing `runner.py` pattern. For failed subagent tasks, the orchestrator captures the last N lines of output (from the adapter's stdout stream) and includes them in the `AgentResult.summary` field to aid debugging. No separate stderr capture is needed.

---

## Orchestrator

The orchestrator is pure Python — no agent intelligence of its own. It gets a plan from a CLI call, then mechanically executes it.

### Flow Per Phase

**1. Plan**
- Build a planning prompt via `adapter.build_planning_prompt(brief, phase, stack)`
- Make one CLI call to the phase's assigned backend
- Parse the JSON response via `adapter.parse_plan(raw_output, phase, backend)` (see JSON Parsing Strategy below)
- Stamp `phase`, `backend`, and `model` onto each `AgentTask` — the planning call only returns `id`, `description`, `file_territory`, and `dependencies`; the orchestrator fills in routing fields and model override from the current phase context

**2. Execute**
- Walk `execution_order` groups sequentially
- Within each group, run tasks in parallel via `ThreadPoolExecutor`
- For each completed task:
  - Scan filesystem for new/changed files
  - Build a context summary of what was produced
  - Append summary to cumulative context for downstream tasks
- Stream `ProgressEvent`s to the UI throughout

**3. Reconcile**
- After all tasks complete, make one final CLI call to the phase's assigned backend (same backend that did the planning call — it has the best understanding of the intended structure):
  "Review the project directory. Check for missing imports, inconsistent naming, broken references, incomplete `__init__.py` files. Fix any issues."
- Lightweight cleanup pass, not a re-scaffold
- If the reconciliation call fails (non-zero exit), log a warning and continue — reconciliation is non-fatal. The scaffold is likely usable even without cleanup.

**4. Report**
- Aggregate all `AgentResult`s into a phase summary
- Feed into existing dashboard and file tree rendering

### Example Decomposition

For an Architecture phase on a `fastapi` stack:

```
Orchestrator receives: "Scaffold a FastAPI service for customer operations
                        with auth, Postgres, Docker, CI"

Planning call returns:
  Task 1: "Project skeleton agent"
           Files: pyproject.toml, directory structure, .env.example,
                  Dockerfile, docker-compose.yml
           Dependencies: none

  Task 2: "Data layer agent"
           Files: models/, schemas/, core/database.py, alembic/
           Dependencies: [task-1]

  Task 3: "API routes agent"
           Files: api/routes/, api/middleware/, api/deps.py
           Dependencies: [task-2]

  Task 4: "DevOps agent"
           Files: .github/workflows/, .pre-commit-config.yaml, Makefile
           Dependencies: [task-1]

Execution order: [[task-1], [task-2, task-4], [task-3]]
  - Task 1 runs first (skeleton)
  - Tasks 2 and 4 run in parallel (independent)
  - Task 3 runs last (needs models from task 2)
```

### Context Accumulation

The orchestrator owns context accumulation — not the adapters. After each task completes:

1. **Filesystem snapshot diff:** The orchestrator snapshots the project directory (file list + mtimes) before each task and diffs after. This produces `AgentResult.files_created` and `AgentResult.files_modified` — the adapter does not need to track these.
2. **Template-based summary:** The orchestrator generates a context string from a template:
   ```
   Completed: {task.description}
   Files created: {files_created}
   Files modified: {files_modified}
   Key file contents: {first 200 lines of each new .py/.ts/.json file}
   ```
   The "key file contents" section reads the actual created files so downstream subagents can see interfaces, models, and config — not just filenames.
3. **Context cap:** Accumulated context is capped at 12,000 characters. When the cap is reached, older task summaries are compressed to filename-only lists while recent summaries retain full content. This prevents prompt bloat, especially for Codex which works better with concise prompts.

Example flow:

```
Task 1 completes ->
  "Project skeleton created. Structure: src/atlas_api/ with __init__.py,
   main.py. Dependencies: fastapi, uvicorn, sqlalchemy, alembic.
   Docker: Dockerfile + compose with postgres service."

Task 2 receives that context, completes ->
  Context grows: "...Data layer added: models/user.py,
   models/subscription.py with SQLAlchemy models. Schemas: schemas/user.py,
   schemas/subscription.py with Pydantic v2. Database config in
   core/database.py with async session."

Task 3 receives the full accumulated context.
```

### Fallback Behavior

- Planning call fails to return valid JSON -> retry once with an explicit "respond with JSON only, no markdown fences" instruction, then fall back to single-task plan (today's behavior)
- Subagent task fails -> log it, continue with remaining tasks that don't depend on it. Tasks that depend on the failed task are skipped with a warning.
- `--agents` used but no backend can produce a valid plan after 2 retries -> warn and fall back to standard mode
- Simple phases (e.g., verify) may not benefit from decomposition. If the planning call returns only 1 task, the orchestrator skips the overhead and runs it directly.

### JSON Parsing Strategy

Reliable JSON extraction from CLI output is critical — this is the most likely failure point. The `parse_plan` method in each adapter implements a multi-step extraction pipeline:

1. **Strip markdown fences:** Regex to remove ````json ... ```` wrappers (common in Claude output)
2. **Find JSON object:** Scan for the first `{` and match to its closing `}`, ignoring preamble text (common in Gemini output)
3. **Schema validation:** Verify required keys exist (`tasks`, `execution_order`, `rationale`), each task has `id`, `description`, `file_territory`, `dependencies`
4. **Repair common issues:** Strip trailing commas, fix unquoted keys, handle single-quoted strings
5. **Fallback:** If extraction fails after repair attempts, return a single-task `DecompositionPlan` that wraps the entire phase brief — effectively today's behavior

Each adapter can tune this pipeline for its backend's output patterns (e.g., Claude adapter may skip step 2 since Claude rarely adds preamble, Gemini adapter may be more aggressive on step 2).

### Parallel Execution and File Conflicts

Parallel subagents within an execution group share the same `project_dir`. File territory assignments are advisory — two parallel tasks could theoretically write to the same file. Mitigations:

1. **Planning prompt guidance:** The planning prompt explicitly instructs: "Assign non-overlapping file territories to parallel tasks"
2. **Reconciliation pass:** Detects and resolves conflicts that slip through
3. **Known limitation:** True race conditions (two processes writing the same file simultaneously) are possible but unlikely given that file territories are designed to be disjoint. This is accepted as a known risk, consistent with the existing `run_ai_parallel` behavior.

### Performance Expectations

Multi-agent mode adds CLI calls compared to standard mode. For a 3-phase `fastapi` scaffold with each phase decomposed into ~4 tasks:

- **Standard mode:** 3 CLI calls (one per phase), ~2-5 min total
- **Agent mode:** 3 planning calls + ~12 task calls + 3 reconciliation calls = ~18 CLI calls

Each CLI call takes 15-90 seconds depending on task complexity. Total time will be longer than standard mode, but quality should be higher because each subagent has a focused scope. Parallel execution within groups partially offsets the overhead.

The `--agents` flag documentation should set this expectation: "Multi-agent mode produces higher quality scaffolds but takes longer."

---

## Adapters

Each adapter is thin — prompt formatting for its backend's CLI. Subprocess execution is shared in `base.py`.

### Base Adapter

```python
class CLIAdapterBase:
    """Shared subprocess execution — implements ForgeAgent.execute.

    Subclasses override build_prompt, build_planning_prompt,
    parse_plan, and build_cmd to customize per backend.
    """

    def execute(
        self,
        task: AgentTask,
        project_dir: Path,
        on_progress: Callable[[ProgressEvent], None],
    ) -> AgentResult:
        prompt = self.build_prompt(task)
        cmd = self.build_cmd(prompt, task.model)
        # Subprocess execution, stdout streaming, ProgressEvent extraction
        # Uses shared subprocess utilities (extracted from runner.py patterns)
        ...

    def build_prompt(self, task: AgentTask) -> str:
        raise NotImplementedError

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str:
        raise NotImplementedError

    def parse_plan(self, raw_output: str, phase: str, backend: str) -> DecompositionPlan:
        raise NotImplementedError

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]:
        raise NotImplementedError
```

**Conventions:** Each adapter instance is initialized with the conventions string. The `build_prompt` method injects conventions into the subagent prompt template — conventions are adapter state, not part of `AgentTask`. This keeps the task data structure focused on the work assignment while conventions are a cross-cutting concern handled at the adapter level.

**Phase context for UI:** The orchestrator accepts `phase_context` (the same list of phase dicts used by `runner.py` for the timeline) and passes it through to the UI rendering layer. The phase timeline continues to show phase-level progress; the activity feed within each phase shows subagent-level detail.

### Backend Differences

| Concern | Claude | Gemini | Codex |
|---------|--------|--------|-------|
| CLI command | `claude -p` | `gemini -p` | `codex exec` |
| Planning prompt style | Structured system prompts, strong JSON output | Needs explicit JSON schema in prompt | Best with concrete examples |
| Prompt size | Large context | Large context | Smaller, concise prompts preferred |
| Strengths | Reasoning, architecture, reconciliation | Frontend/UI, aesthetics | Tests, refactors, mechanical tasks |

### Planning Prompt Template

Each adapter wraps this core structure for its backend:

```
You are a scaffold planning agent. Given this project brief and phase,
decompose the work into focused subagent tasks.

Brief: {assembled_prompt}
Phase: {phase_name}
Stack: {stack}

Return a JSON object with this exact structure:
{
  "tasks": [
    {
      "id": "task-1",
      "description": "what this subagent should build",
      "file_territory": ["paths/to/own"],
      "dependencies": []
    }
  ],
  "execution_order": [["task-1"], ["task-2", "task-3"], ["task-4"]],
  "rationale": "why this decomposition"
}
```

### Subagent Task Prompt Template

```
You are a specialist subagent working on a scaffold project.

Your assignment: {task.description}

Files you own: {task.file_territory}

Context from completed work:
{task.context}

Project directory: {project_dir}
Stack: {stack}

Rules:
- Only create/modify files in your territory unless absolutely necessary
- Follow the conventions provided
- Build on what previous agents created — do not overwrite their files

{conventions}
```

---

## UI Integration

The existing UI primitives stay. `ProgressEvent`s map into the activity feed and timeline users already know.

### Default View (with `--agents`)

Phase timeline at top, unchanged. Activity feed shows subagent work:

```
Architecture & Core                   ━━━━━━━━━━●━━━━━━━━━

  ✓ Planning scaffold decomposition                    3s
  ✓ Project skeleton agent: Created project structure  12s
  ● Data layer agent: Writing models and schemas
    DevOps agent: Setting up CI workflow
```

Concurrent subagents show simultaneously. Active tasks get the pulsing dot. Parallel peers are indented under the same group. Completed subagents get checkmarks.

### Progress Event Mapping

```python
def _map_progress_to_activity(event: ProgressEvent, tracker: ActivityTracker):
    if event.event_type == "started":
        tracker.update(f"{event.agent_label}: {event.message}")
    elif event.event_type == "progress":
        tracker.update(f"{event.agent_label}: {event.message}")
    elif event.event_type == "completed":
        tracker.update(f"{event.agent_label}: Done")
    elif event.event_type == "failed":
        tracker.update(f"{event.agent_label}: Failed — {event.message}")
```

### Verbose Mode Additions

`--verbose` adds on top of the normal activity feed:
- Full decomposition plan (task graph with dependencies)
- Per-subagent prompt length and backend
- File territory assignments
- Context summaries passed between tasks
- Reconciliation pass output

### Post-Scaffold Dashboard

Existing dashboard gains one new row when `--agents` was used:
- "Agent tasks: 4 planned, 4 completed, 0 failed"
- Everything else (health checks, file counts, next steps) unchanged

---

## CLI Changes

### New Flag

```
--agents / --no-agents    Enable multi-agent orchestration (default: off)
```

### Integration in cli.py

```python
if agents_mode:
    from ubundiforge.orchestrator import run_phase_orchestrated

    returncode = run_phase_orchestrated(
        phase=phase,
        backend=backend,
        prompt=assembled_prompt,
        project_dir=project_dir,
        stack=stack,
        conventions=conventions,
        model=model,
        verbose=verbose,
        phase_context=phase_context,
    )
else:
    returncode = run_ai(
        backend=backend,
        prompt=assembled_prompt,
        project_dir=project_dir,
        model=model,
        verbose=verbose,
        label=label,
        phase_context=phase_context,
    )
```

### Interaction with --dry-run and --export

- `--dry-run --agents`: Makes the planning call and displays the decomposition plan (task graph, file territories, execution order) but does not execute any subagent tasks. This lets users preview how the phase would be decomposed.
- `--export --agents`: Exports the assembled brief as today, plus appends the decomposition plan as a "## Agent Decomposition" section in the exported file.
- `--dry-run` without `--agents`: Unchanged behavior.

### Config Addition

`~/.forge/config.json` gets optional `"agents": true` to make multi-agent the default.

---

## Quality Signal Enhancement

`quality.py` currently records one signal per phase. With `--agents`, it additionally records per-subagent signals:
- Which backend handled which task type
- Whether it succeeded
- Duration

This feeds back into smarter planning over time — e.g., the orchestrator can learn that Gemini fails at database schema tasks and prefer Claude for those.

---

## What Stays Untouched

- `router.py` — still picks backends per phase
- `prompt_builder.py` — still assembles the brief
- `prompts.py` — interactive flow unchanged
- `runner.py` — refactored to import from `subprocess_utils.py` but behavior unchanged; shared subprocess patterns (ANSI stripping, progress summarization) move to the shared module
- `quality.py` — extended, not replaced
- All existing tests pass without modification

---

## Rollout Phases

### Phase 1: Foundation
- `protocol.py` with all data structures
- `adapters/base.py` with shared subprocess logic
- `adapters/claude_adapter.py` as first implementation
- Unit tests for protocol and adapter

### Phase 2: Orchestrator
- `orchestrator.py` with plan/execute/reconcile/report flow
- Planning prompt templates that reliably produce valid JSON
- Fallback behavior (bad JSON -> single-task plan)
- Integration test: orchestrated scaffold with `--dry-run`

### Phase 3: Remaining Adapters + UI
- `adapters/gemini_adapter.py` and `adapters/codex_adapter.py`
- Progress event -> activity feed mapping
- `--agents` flag in `cli.py`
- `--verbose` agent graph output

### Phase 4: Intelligence
- Per-subagent quality signals in `quality.py`
- Orchestrator learns from history
- Config option to make agents the default
