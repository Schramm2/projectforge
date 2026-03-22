# Multi-Agent Orchestration Framework — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decompose scaffold phases into focused subagent tasks coordinated by a CLI-native orchestrator, producing higher quality scaffolds through divide-and-conquer multi-agent workflows.

**Architecture:** An orchestrator module makes a CLI call to get a JSON decomposition plan, then executes focused subagent tasks through backend-specific adapters. Shared subprocess logic is extracted from `runner.py` into a utility module. Everything runs through existing free CLI tools — no SDK dependencies or API keys.

**Tech Stack:** Python 3.12+, Typer, Rich, ThreadPoolExecutor, subprocess, JSON parsing

**Spec:** `docs/superpowers/specs/2026-03-22-multi-agent-orchestration-design.md`

**Important:** Another plan may have been implemented between spec writing and this plan's execution. Read the current state of files before modifying them — do not assume line numbers or exact code matches from this plan. The spec is the source of truth for *what* to build; the codebase at implementation time is the source of truth for *where* things currently are.

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `src/ubundiforge/protocol.py` | Data structures (`AgentTask`, `AgentResult`, `ProgressEvent`, `DecompositionPlan`) and `ForgeAgent` protocol |
| `src/ubundiforge/subprocess_utils.py` | Shared subprocess patterns extracted from `runner.py` (ANSI stripping, progress summarization, timeouts) |
| `src/ubundiforge/adapters/__init__.py` | Adapter registry — maps backend name to adapter class |
| `src/ubundiforge/adapters/base.py` | `CLIAdapterBase` — implements `ForgeAgent.execute` using `subprocess_utils` |
| `src/ubundiforge/adapters/claude_adapter.py` | Claude-specific prompt formatting and JSON parsing |
| `src/ubundiforge/adapters/gemini_adapter.py` | Gemini-specific prompt formatting and JSON parsing |
| `src/ubundiforge/adapters/codex_adapter.py` | Codex-specific prompt formatting and JSON parsing |
| `src/ubundiforge/orchestrator.py` | Plan/execute/reconcile/report flow per phase |
| `tests/test_protocol.py` | Protocol data structure tests |
| `tests/test_subprocess_utils.py` | Tests for extracted subprocess utilities |
| `tests/test_adapter_base.py` | Tests for `CLIAdapterBase` execution |
| `tests/test_claude_adapter.py` | Tests for Claude adapter prompt formatting and JSON parsing |
| `tests/test_gemini_adapter.py` | Tests for Gemini adapter |
| `tests/test_codex_adapter.py` | Tests for Codex adapter |
| `tests/test_orchestrator.py` | Tests for orchestrator plan/execute/reconcile flow |

### Modified Files

| File | Change |
|------|--------|
| `src/ubundiforge/runner.py` | Import shared patterns from `subprocess_utils.py` instead of defining them inline |
| `src/ubundiforge/cli.py` | Add `--agents` flag, route through orchestrator when enabled |

---

## Task 1: Protocol Data Structures

**Files:**
- Create: `src/ubundiforge/protocol.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: Write tests for AgentTask**

```python
# tests/test_protocol.py
"""Tests for multi-agent orchestration protocol data structures."""

from ubundiforge.protocol import AgentTask, AgentResult, DecompositionPlan, ProgressEvent


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_protocol.py -v`
Expected: ImportError — `ubundiforge.protocol` does not exist yet

- [ ] **Step 3: Write tests for AgentResult, ProgressEvent, DecompositionPlan**

Add to `tests/test_protocol.py`:

```python
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
            id="task-1", description="A", file_territory=[], context="",
            dependencies=[], phase="p", backend="b",
        )
        task2 = AgentTask(
            id="task-2", description="B", file_territory=[], context="",
            dependencies=[], phase="p", backend="b",
        )
        plan = DecompositionPlan(
            tasks=[task1, task2],
            execution_order=[["task-1", "task-2"]],
            rationale="Parallel",
        )
        task_map = {t.id: t for t in plan.tasks}
        assert task_map["task-1"].description == "A"
        assert task_map["task-2"].description == "B"
```

- [ ] **Step 4: Write protocol.py with all data structures and the ForgeAgent protocol**

```python
# src/ubundiforge/protocol.py
"""Multi-agent orchestration protocol — data structures and ForgeAgent contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol


@dataclass
class AgentTask:
    """A unit of work assigned to a subagent."""

    id: str
    description: str
    file_territory: list[str]
    context: str
    dependencies: list[str]
    phase: str
    backend: str
    model: str | None = None


@dataclass
class AgentResult:
    """What a subagent produces."""

    task_id: str
    files_created: list[str]
    files_modified: list[str]
    summary: str
    success: bool
    duration: float
    returncode: int


@dataclass
class ProgressEvent:
    """Emitted by adapters, consumed by the UI layer."""

    task_id: str
    agent_label: str
    event_type: str  # "started" | "progress" | "completed" | "failed"
    message: str
    timestamp: float


@dataclass
class DecompositionPlan:
    """Output of the planning call."""

    tasks: list[AgentTask]
    execution_order: list[list[str]]
    rationale: str


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

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_protocol.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/ubundiforge/protocol.py tests/test_protocol.py
git commit -m "feat(agents): add protocol data structures and ForgeAgent contract"
```

---

## Task 2: Extract Subprocess Utilities from runner.py

**Files:**
- Create: `src/ubundiforge/subprocess_utils.py`
- Modify: `src/ubundiforge/runner.py`
- Create: `tests/test_subprocess_utils.py`

**Note:** Read `runner.py` at implementation time to find the exact functions to extract. The functions named below are based on the spec — actual names may differ.

- [ ] **Step 1: Write tests for subprocess utilities**

```python
# tests/test_subprocess_utils.py
"""Tests for shared subprocess utilities."""

from ubundiforge.subprocess_utils import (
    ANSI_RE,
    PHASE_TIMEOUT,
    sanitize_progress_line,
    is_noisy_progress_line,
    summarize_output_line,
    spinner_frame,
)


class TestSanitizeProgressLine:
    def test_strips_ansi_codes(self):
        line = "\x1b[32mSuccess\x1b[0m"
        assert sanitize_progress_line(line) == "Success"

    def test_collapses_whitespace(self):
        line = "foo   bar   baz"
        assert sanitize_progress_line(line) == "foo bar baz"

    def test_truncates_long_lines(self):
        line = "x" * 200
        result = sanitize_progress_line(line)
        assert len(result) <= 120

    def test_strips_leading_trailing_whitespace(self):
        line = "   hello   "
        assert sanitize_progress_line(line) == "hello"


class TestIsNoisyProgressLine:
    def test_empty_is_noisy(self):
        assert is_noisy_progress_line("") is True

    def test_diff_header_is_noisy(self):
        assert is_noisy_progress_line("diff --git a/foo b/foo") is True

    def test_shell_prompt_is_noisy(self):
        assert is_noisy_progress_line("$ npm install") is True

    def test_normal_text_is_not_noisy(self):
        assert is_noisy_progress_line("Creating project structure") is False


class TestSummarizeOutputLine:
    def test_lint_keyword(self):
        assert summarize_output_line("Running ruff check") == "Running lint checks"

    def test_test_keyword(self):
        assert summarize_output_line("pytest tests/") == "Running tests and checks"

    def test_create_keyword(self):
        assert summarize_output_line("Creating main.py") == "Writing and refining project files"

    def test_unknown_line_returns_none(self):
        assert summarize_output_line("some random line") is None


class TestSpinnerFrame:
    def test_returns_string(self):
        frame = spinner_frame(0.0)
        assert isinstance(frame, str)
        assert len(frame) == 1

    def test_cycles(self):
        frames = [spinner_frame(i * 0.1) for i in range(20)]
        assert len(set(frames)) > 1


class TestConstants:
    def test_phase_timeout_is_reasonable(self):
        assert PHASE_TIMEOUT == 1800

    def test_ansi_regex_compiles(self):
        assert ANSI_RE.pattern
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_subprocess_utils.py -v`
Expected: ImportError — `ubundiforge.subprocess_utils` does not exist

- [ ] **Step 3: Create subprocess_utils.py by extracting from runner.py**

Read `runner.py` at implementation time. Extract these functions/constants (names may vary — find the equivalents):

- `_ANSI_RE` -> `ANSI_RE`
- `_PHASE_TIMEOUT` -> `PHASE_TIMEOUT`
- `_SPINNER_FRAMES` -> `SPINNER_FRAMES`
- `_PULSE_STYLES` -> `PULSE_STYLES`
- `_sanitize_progress_line` -> `sanitize_progress_line`
- `_is_noisy_progress_line` -> `is_noisy_progress_line`
- `_summarize_output_line` -> `summarize_output_line`
- `_progress_summary_for_line` -> `progress_summary_for_line`
- `_spinner_frame` -> `spinner_frame`
- `_spinner_style` -> `spinner_style`
- `_format_activity` -> `format_activity`

The module should export these as public functions (no leading underscore). Keep the implementations identical — this is a pure extraction refactor.

```python
# src/ubundiforge/subprocess_utils.py
"""Shared subprocess utilities for AI CLI execution.

Extracted from runner.py so both runner.py and the multi-agent adapters
can reuse ANSI stripping, progress summarization, and spinner logic
without duplication.
"""

import re

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
PHASE_TIMEOUT = 1800  # 30 minutes per phase
PULSE_STYLES = {
    "aqua": ("#4D6A84", "#75DCE6", "#C6CEE6", "#75DCE6"),
    "amber": ("#77603A", "#F3BB58", "#F7D99C", "#F3BB58"),
    "violet": ("#5F4A87", "#A16EFA", "#D3BCFF", "#A16EFA"),
    "plum": ("#7B4A79", "#D768D2", "#F0B6ED", "#D768D2"),
}

# Copy the keyword_groups and all function bodies from runner.py.
# Keep implementations identical — this is a pure extraction.
# (Implementer: read runner.py at implementation time for exact code.)


def sanitize_progress_line(line: str) -> str:
    """Normalize backend output into compact text suitable for a loader."""
    clean = ANSI_RE.sub("", line).strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean[:120]


def is_noisy_progress_line(line: str) -> bool:
    """Filter out raw lines that are too noisy to show in the loader."""
    if not line:
        return True
    noisy_prefixes = (
        "$", ">", "```", "diff --git", "@@", "+++", "---", "{", "[{",
    )
    if line.startswith(noisy_prefixes):
        return True
    if line.count("/") > 6:
        return True
    return False


# ... (copy remaining functions from runner.py verbatim)


def summarize_output_line(line: str) -> str | None:
    """Translate backend output into a clean user-facing progress summary."""
    # Copy keyword_groups and logic from runner.py
    ...


def progress_summary_for_line(line: str, current: str) -> str:
    """Pick the best loader summary for a new backend output line."""
    summary = summarize_output_line(line)
    if summary:
        return summary
    if not is_noisy_progress_line(line):
        return line
    return current


def spinner_frame(elapsed: float) -> str:
    """Return the current spinner frame."""
    return SPINNER_FRAMES[int(elapsed * 10) % len(SPINNER_FRAMES)]


def spinner_style(accent: str, elapsed: float) -> str:
    """Return a pulsing spinner color."""
    palette = PULSE_STYLES.get(accent, PULSE_STYLES["violet"])
    return palette[int(elapsed * 6) % len(palette)]


def format_activity(text: str, limit: int = 54) -> str:
    """Clamp activity text so loader surfaces stay compact."""
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"
```

- [ ] **Step 4: Run new tests to verify they pass**

Run: `uv run pytest tests/test_subprocess_utils.py -v`
Expected: All PASS

- [ ] **Step 5: Update runner.py to import from subprocess_utils**

In `runner.py`, replace the inline definitions with imports:

```python
# At the top of runner.py, replace the local definitions with:
from ubundiforge.subprocess_utils import (
    ANSI_RE,
    PHASE_TIMEOUT,
    SPINNER_FRAMES,
    PULSE_STYLES,
    sanitize_progress_line,
    is_noisy_progress_line,
    summarize_output_line,
    progress_summary_for_line,
    spinner_frame,
    spinner_style,
    format_activity,
)
```

Remove the old inline definitions. Keep all function references as-is (the names match, callers just now import from the shared module).

- [ ] **Step 6: Run full existing test suite to verify no regressions**

Run: `uv run pytest -v`
Expected: All existing tests PASS — behavior is identical, only the import source changed.

- [ ] **Step 7: Commit**

```bash
git add src/ubundiforge/subprocess_utils.py src/ubundiforge/runner.py tests/test_subprocess_utils.py
git commit -m "refactor: extract shared subprocess utilities from runner.py"
```

---

## Task 3: CLI Adapter Base

**Files:**
- Create: `src/ubundiforge/adapters/__init__.py`
- Create: `src/ubundiforge/adapters/base.py`
- Create: `tests/test_adapter_base.py`

- [ ] **Step 1: Write tests for CLIAdapterBase**

```python
# tests/test_adapter_base.py
"""Tests for CLIAdapterBase shared execution logic."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from ubundiforge.adapters.base import CLIAdapterBase
from ubundiforge.protocol import AgentResult, AgentTask, ProgressEvent


class StubAdapter(CLIAdapterBase):
    """Concrete adapter for testing the base class."""

    def build_prompt(self, task):
        return f"Do: {task.description}"

    def build_planning_prompt(self, brief, phase, stack):
        return f"Plan: {brief}"

    def parse_plan(self, raw_output, phase, backend):
        raise NotImplementedError

    def build_cmd(self, prompt, model=None):
        cmd = ["echo", prompt]
        return cmd


class TestCLIAdapterBaseExecute:
    def test_execute_successful_task(self, tmp_path):
        adapter = StubAdapter(conventions="test conventions")
        task = AgentTask(
            id="task-1",
            description="create a file",
            file_territory=["test.txt"],
            context="",
            dependencies=[],
            phase="architecture",
            backend="echo",
        )
        events = []
        result = adapter.execute(task, tmp_path, on_progress=events.append)

        assert isinstance(result, AgentResult)
        assert result.task_id == "task-1"
        assert result.success is True
        assert result.returncode == 0
        assert result.duration > 0

    def test_execute_emits_started_event(self, tmp_path):
        adapter = StubAdapter(conventions="")
        task = AgentTask(
            id="task-1", description="test", file_territory=[], context="",
            dependencies=[], phase="p", backend="echo",
        )
        events = []
        adapter.execute(task, tmp_path, on_progress=events.append)

        started_events = [e for e in events if e.event_type == "started"]
        assert len(started_events) >= 1

    def test_execute_emits_completed_event(self, tmp_path):
        adapter = StubAdapter(conventions="")
        task = AgentTask(
            id="task-1", description="test", file_territory=[], context="",
            dependencies=[], phase="p", backend="echo",
        )
        events = []
        adapter.execute(task, tmp_path, on_progress=events.append)

        completed_events = [e for e in events if e.event_type == "completed"]
        assert len(completed_events) == 1

    def test_execute_captures_last_lines_on_failure(self, tmp_path):
        adapter = StubAdapter(conventions="")
        adapter.build_cmd = lambda prompt, model=None: ["false"]  # exit code 1
        task = AgentTask(
            id="task-1", description="fail", file_territory=[], context="",
            dependencies=[], phase="p", backend="false",
        )
        events = []
        result = adapter.execute(task, tmp_path, on_progress=events.append)

        assert result.success is False
        assert result.returncode != 0


class TestCLIAdapterBaseInit:
    def test_stores_conventions(self):
        adapter = StubAdapter(conventions="Follow Ubundi standards")
        assert adapter.conventions == "Follow Ubundi standards"

    def test_empty_conventions(self):
        adapter = StubAdapter(conventions="")
        assert adapter.conventions == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_adapter_base.py -v`
Expected: ImportError

- [ ] **Step 3: Create adapters package and base.py**

```python
# src/ubundiforge/adapters/__init__.py
"""Multi-agent backend adapters."""
```

```python
# src/ubundiforge/adapters/base.py
"""CLIAdapterBase — shared subprocess execution for all backend adapters."""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

from ubundiforge.protocol import AgentResult, AgentTask, DecompositionPlan, ProgressEvent
from ubundiforge.subprocess_utils import (
    PHASE_TIMEOUT,
    sanitize_progress_line,
    summarize_output_line,
)


class CLIAdapterBase:
    """Shared subprocess execution — implements ForgeAgent.execute.

    Subclasses override build_prompt, build_planning_prompt,
    parse_plan, and build_cmd to customize per backend.
    """

    def __init__(self, conventions: str = "") -> None:
        self.conventions = conventions

    def execute(
        self,
        task: AgentTask,
        project_dir: Path,
        on_progress: Callable[[ProgressEvent], None],
    ) -> AgentResult:
        prompt = self.build_prompt(task)
        cmd = self.build_cmd(prompt, task.model)
        project_dir.mkdir(parents=True, exist_ok=True)

        on_progress(ProgressEvent(
            task_id=task.id,
            agent_label=task.description,
            event_type="started",
            message=f"Starting: {task.description}",
            timestamp=time.monotonic(),
        ))

        start = time.monotonic()
        last_lines: list[str] = []
        lock = threading.Lock()

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except FileNotFoundError:
            duration = time.monotonic() - start
            on_progress(ProgressEvent(
                task_id=task.id,
                agent_label=task.description,
                event_type="failed",
                message="Command not found",
                timestamp=time.monotonic(),
            ))
            return AgentResult(
                task_id=task.id,
                files_created=[],
                files_modified=[],
                summary="Command not found",
                success=False,
                duration=duration,
                returncode=1,
            )

        def _read_stdout():
            try:
                for raw_line in iter(proc.stdout.readline, b""):
                    line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                    if line:
                        clean = sanitize_progress_line(line)
                        if clean:
                            with lock:
                                last_lines.append(clean)
                                if len(last_lines) > 20:
                                    last_lines.pop(0)
                            summary = summarize_output_line(clean)
                            if summary:
                                on_progress(ProgressEvent(
                                    task_id=task.id,
                                    agent_label=task.description,
                                    event_type="progress",
                                    message=summary,
                                    timestamp=time.monotonic(),
                                ))
            except ValueError:
                pass

        reader = threading.Thread(target=_read_stdout, daemon=True)
        reader.start()

        while proc.poll() is None:
            elapsed = time.monotonic() - start
            if elapsed > PHASE_TIMEOUT:
                proc.kill()
                proc.wait()
                reader.join(timeout=5)
                on_progress(ProgressEvent(
                    task_id=task.id,
                    agent_label=task.description,
                    event_type="failed",
                    message=f"Timed out after {elapsed:.0f}s",
                    timestamp=time.monotonic(),
                ))
                return AgentResult(
                    task_id=task.id,
                    files_created=[],
                    files_modified=[],
                    summary=f"Timed out after {elapsed:.0f}s",
                    success=False,
                    duration=elapsed,
                    returncode=1,
                )
            time.sleep(0.5)

        reader.join(timeout=5)
        duration = time.monotonic() - start
        success = proc.returncode == 0

        summary_text = "Completed" if success else "\n".join(last_lines[-5:])

        event_type = "completed" if success else "failed"
        on_progress(ProgressEvent(
            task_id=task.id,
            agent_label=task.description,
            event_type=event_type,
            message="Done" if success else f"Exit {proc.returncode}",
            timestamp=time.monotonic(),
        ))

        return AgentResult(
            task_id=task.id,
            files_created=[],   # orchestrator fills these via filesystem diff
            files_modified=[],  # orchestrator fills these via filesystem diff
            summary=summary_text,
            success=success,
            duration=duration,
            returncode=proc.returncode,
        )

    def build_prompt(self, task: AgentTask) -> str:
        raise NotImplementedError

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str:
        raise NotImplementedError

    def parse_plan(self, raw_output: str, phase: str, backend: str) -> DecompositionPlan:
        raise NotImplementedError

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]:
        raise NotImplementedError
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_adapter_base.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/ubundiforge/adapters/__init__.py src/ubundiforge/adapters/base.py tests/test_adapter_base.py
git commit -m "feat(agents): add CLIAdapterBase with subprocess execution"
```

---

## Task 4: JSON Parsing Utilities

**Files:**
- Create: `src/ubundiforge/adapters/json_parsing.py`
- Create: `tests/test_json_parsing.py`

This is the most critical reliability piece — extracted into its own module so all adapters share robust JSON extraction.

- [ ] **Step 1: Write comprehensive JSON parsing tests**

```python
# tests/test_json_parsing.py
"""Tests for JSON extraction from CLI output."""

import pytest

from ubundiforge.adapters.json_parsing import extract_json, validate_plan_schema, parse_decomposition_plan
from ubundiforge.protocol import DecompositionPlan


class TestExtractJson:
    def test_clean_json(self):
        raw = '{"tasks": [], "execution_order": [], "rationale": "simple"}'
        result = extract_json(raw)
        assert result["rationale"] == "simple"

    def test_json_in_markdown_fences(self):
        raw = 'Here is the plan:\n```json\n{"tasks": [], "execution_order": [], "rationale": "fenced"}\n```'
        result = extract_json(raw)
        assert result["rationale"] == "fenced"

    def test_json_with_preamble_text(self):
        raw = 'I will decompose this into tasks.\n\n{"tasks": [], "execution_order": [], "rationale": "preamble"}'
        result = extract_json(raw)
        assert result["rationale"] == "preamble"

    def test_json_with_trailing_text(self):
        raw = '{"tasks": [], "execution_order": [], "rationale": "trailing"}\n\nLet me know if you need changes.'
        result = extract_json(raw)
        assert result["rationale"] == "trailing"

    def test_json_with_trailing_commas(self):
        raw = '{"tasks": [], "execution_order": [], "rationale": "commas",}'
        result = extract_json(raw)
        assert result["rationale"] == "commas"

    def test_returns_none_for_no_json(self):
        raw = "This is just text with no JSON at all."
        result = extract_json(raw)
        assert result is None

    def test_returns_none_for_malformed_json(self):
        raw = '{"tasks": [incomplete'
        result = extract_json(raw)
        assert result is None

    def test_nested_json_objects(self):
        raw = '{"tasks": [{"id": "t1", "description": "d", "file_territory": [], "dependencies": []}], "execution_order": [["t1"]], "rationale": "nested"}'
        result = extract_json(raw)
        assert len(result["tasks"]) == 1

    def test_triple_backtick_without_json_label(self):
        raw = '```\n{"tasks": [], "execution_order": [], "rationale": "no label"}\n```'
        result = extract_json(raw)
        assert result["rationale"] == "no label"


class TestValidatePlanSchema:
    def test_valid_plan(self):
        data = {
            "tasks": [
                {"id": "t1", "description": "d", "file_territory": ["f"], "dependencies": []},
            ],
            "execution_order": [["t1"]],
            "rationale": "reason",
        }
        assert validate_plan_schema(data) is True

    def test_missing_tasks_key(self):
        data = {"execution_order": [[]], "rationale": "r"}
        assert validate_plan_schema(data) is False

    def test_missing_execution_order(self):
        data = {"tasks": [], "rationale": "r"}
        assert validate_plan_schema(data) is False

    def test_missing_rationale(self):
        data = {"tasks": [], "execution_order": []}
        assert validate_plan_schema(data) is False

    def test_task_missing_id(self):
        data = {
            "tasks": [{"description": "d", "file_territory": [], "dependencies": []}],
            "execution_order": [["t1"]],
            "rationale": "r",
        }
        assert validate_plan_schema(data) is False

    def test_task_missing_description(self):
        data = {
            "tasks": [{"id": "t1", "file_territory": [], "dependencies": []}],
            "execution_order": [["t1"]],
            "rationale": "r",
        }
        assert validate_plan_schema(data) is False


class TestParseDecompositionPlan:
    def test_parses_valid_output(self):
        raw = '{"tasks": [{"id": "t1", "description": "skeleton", "file_territory": ["src/"], "dependencies": []}], "execution_order": [["t1"]], "rationale": "simple"}'
        plan = parse_decomposition_plan(raw, phase="architecture", backend="claude")
        assert isinstance(plan, DecompositionPlan)
        assert len(plan.tasks) == 1
        assert plan.tasks[0].phase == "architecture"
        assert plan.tasks[0].backend == "claude"

    def test_stamps_phase_and_backend(self):
        raw = '{"tasks": [{"id": "t1", "description": "d", "file_territory": [], "dependencies": []}], "execution_order": [["t1"]], "rationale": "r"}'
        plan = parse_decomposition_plan(raw, phase="tests", backend="codex")
        assert plan.tasks[0].phase == "tests"
        assert plan.tasks[0].backend == "codex"

    def test_returns_none_for_unparseable(self):
        plan = parse_decomposition_plan("garbage text", phase="p", backend="b")
        assert plan is None

    def test_returns_none_for_invalid_schema(self):
        raw = '{"not_tasks": []}'
        plan = parse_decomposition_plan(raw, phase="p", backend="b")
        assert plan is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_json_parsing.py -v`
Expected: ImportError

- [ ] **Step 3: Implement json_parsing.py**

```python
# src/ubundiforge/adapters/json_parsing.py
"""Robust JSON extraction from CLI output.

CLI tools wrap JSON in markdown fences, add preamble text, and sometimes
produce slightly malformed JSON. This module handles all of that.
"""

from __future__ import annotations

import json
import re

from ubundiforge.protocol import AgentTask, DecompositionPlan

_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def extract_json(raw: str) -> dict | None:
    """Extract a JSON object from CLI output, handling common wrapping patterns.

    Strategy:
    1. Strip markdown fences
    2. Find first { and match to closing }
    3. Repair trailing commas
    4. Parse
    """
    # Step 1: Try to extract from markdown fences
    fence_match = _FENCE_RE.search(raw)
    if fence_match:
        candidate = fence_match.group(1).strip()
        parsed = _try_parse(candidate)
        if parsed is not None:
            return parsed

    # Step 2: Find first { and match to closing }
    first_brace = raw.find("{")
    if first_brace == -1:
        return None

    depth = 0
    end = -1
    for i in range(first_brace, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end == -1:
        return None

    candidate = raw[first_brace:end]
    return _try_parse(candidate)


def _try_parse(text: str) -> dict | None:
    """Attempt to parse JSON, with repair for common issues."""
    # Direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
        return None
    except json.JSONDecodeError:
        pass

    # Repair: strip trailing commas
    repaired = _TRAILING_COMMA_RE.sub(r"\1", text)
    try:
        result = json.loads(repaired)
        if isinstance(result, dict):
            return result
        return None
    except json.JSONDecodeError:
        return None


_REQUIRED_PLAN_KEYS = {"tasks", "execution_order", "rationale"}
_REQUIRED_TASK_KEYS = {"id", "description", "file_territory", "dependencies"}


def validate_plan_schema(data: dict) -> bool:
    """Validate that a parsed JSON object has the expected plan structure."""
    if not _REQUIRED_PLAN_KEYS.issubset(data.keys()):
        return False

    for task in data.get("tasks", []):
        if not isinstance(task, dict):
            return False
        if not _REQUIRED_TASK_KEYS.issubset(task.keys()):
            return False

    return True


def parse_decomposition_plan(
    raw_output: str, phase: str, backend: str
) -> DecompositionPlan | None:
    """Parse raw CLI output into a DecompositionPlan.

    Returns None if parsing or validation fails.
    """
    data = extract_json(raw_output)
    if data is None:
        return None

    if not validate_plan_schema(data):
        return None

    tasks = []
    for t in data["tasks"]:
        tasks.append(AgentTask(
            id=t["id"],
            description=t["description"],
            file_territory=t.get("file_territory", []),
            context="",
            dependencies=t.get("dependencies", []),
            phase=phase,
            backend=backend,
        ))

    return DecompositionPlan(
        tasks=tasks,
        execution_order=data["execution_order"],
        rationale=data.get("rationale", ""),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_json_parsing.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/ubundiforge/adapters/json_parsing.py tests/test_json_parsing.py
git commit -m "feat(agents): add robust JSON extraction for plan parsing"
```

---

## Task 5: Claude Adapter

**Files:**
- Create: `src/ubundiforge/adapters/claude_adapter.py`
- Create: `tests/test_claude_adapter.py`

- [ ] **Step 1: Write tests for Claude adapter**

```python
# tests/test_claude_adapter.py
"""Tests for Claude backend adapter."""

from ubundiforge.adapters.claude_adapter import ClaudeAdapter
from ubundiforge.protocol import AgentTask


class TestClaudeAdapterBuildCmd:
    def test_basic_command(self):
        adapter = ClaudeAdapter(conventions="")
        cmd = adapter.build_cmd("do something")
        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert "--dangerously-skip-permissions" in cmd
        assert "do something" in cmd

    def test_command_with_model(self):
        adapter = ClaudeAdapter(conventions="")
        cmd = adapter.build_cmd("do something", model="opus")
        assert "--model" in cmd
        assert "opus" in cmd

    def test_command_without_model(self):
        adapter = ClaudeAdapter(conventions="")
        cmd = adapter.build_cmd("do something")
        assert "--model" not in cmd


class TestClaudeAdapterBuildPrompt:
    def test_includes_task_description(self):
        adapter = ClaudeAdapter(conventions="Use Ruff")
        task = AgentTask(
            id="t1", description="Set up project skeleton",
            file_territory=["pyproject.toml", "src/"],
            context="", dependencies=[], phase="architecture", backend="claude",
        )
        prompt = adapter.build_prompt(task)
        assert "Set up project skeleton" in prompt
        assert "pyproject.toml" in prompt

    def test_includes_conventions(self):
        adapter = ClaudeAdapter(conventions="Always use Ruff for linting")
        task = AgentTask(
            id="t1", description="test", file_territory=[], context="",
            dependencies=[], phase="p", backend="claude",
        )
        prompt = adapter.build_prompt(task)
        assert "Always use Ruff for linting" in prompt

    def test_includes_context_when_present(self):
        adapter = ClaudeAdapter(conventions="")
        task = AgentTask(
            id="t2", description="Write API routes",
            file_territory=["api/"],
            context="Previously created: models/user.py with User model",
            dependencies=["t1"], phase="architecture", backend="claude",
        )
        prompt = adapter.build_prompt(task)
        assert "Previously created: models/user.py" in prompt

    def test_omits_context_section_when_empty(self):
        adapter = ClaudeAdapter(conventions="")
        task = AgentTask(
            id="t1", description="First task", file_territory=[], context="",
            dependencies=[], phase="p", backend="claude",
        )
        prompt = adapter.build_prompt(task)
        assert "Context from completed work" not in prompt


class TestClaudeAdapterPlanningPrompt:
    def test_includes_brief_and_phase(self):
        adapter = ClaudeAdapter(conventions="")
        prompt = adapter.build_planning_prompt(
            brief="Build a FastAPI service",
            phase="architecture",
            stack="fastapi",
        )
        assert "Build a FastAPI service" in prompt
        assert "architecture" in prompt
        assert "fastapi" in prompt

    def test_includes_json_schema(self):
        adapter = ClaudeAdapter(conventions="")
        prompt = adapter.build_planning_prompt("brief", "phase", "stack")
        assert '"tasks"' in prompt
        assert '"execution_order"' in prompt
        assert '"rationale"' in prompt


class TestClaudeAdapterParsePlan:
    def test_parses_valid_plan(self):
        adapter = ClaudeAdapter(conventions="")
        raw = '```json\n{"tasks": [{"id": "t1", "description": "d", "file_territory": [], "dependencies": []}], "execution_order": [["t1"]], "rationale": "r"}\n```'
        plan = adapter.parse_plan(raw, phase="architecture", backend="claude")
        assert plan is not None
        assert len(plan.tasks) == 1

    def test_returns_none_for_garbage(self):
        adapter = ClaudeAdapter(conventions="")
        plan = adapter.parse_plan("not json", phase="p", backend="b")
        assert plan is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_claude_adapter.py -v`
Expected: ImportError

- [ ] **Step 3: Implement ClaudeAdapter**

```python
# src/ubundiforge/adapters/claude_adapter.py
"""Claude Code backend adapter."""

from __future__ import annotations

from ubundiforge.adapters.base import CLIAdapterBase
from ubundiforge.adapters.json_parsing import parse_decomposition_plan
from ubundiforge.protocol import AgentTask, DecompositionPlan

_PLANNING_PROMPT_TEMPLATE = """\
You are a scaffold planning agent. Given this project brief and phase, \
decompose the work into focused subagent tasks.

Brief:
{brief}

Phase: {phase}
Stack: {stack}

Decompose this phase into 2-6 focused tasks. Each task should own a \
distinct set of files. Assign non-overlapping file territories to tasks \
that can run in parallel.

Return ONLY a JSON object — no markdown fences, no explanation — with \
this exact structure:
{{
  "tasks": [
    {{
      "id": "task-1",
      "description": "what this subagent should build",
      "file_territory": ["paths/to/own"],
      "dependencies": []
    }}
  ],
  "execution_order": [["task-1"], ["task-2", "task-3"], ["task-4"]],
  "rationale": "why this decomposition"
}}
"""

_SUBAGENT_PROMPT_TEMPLATE = """\
You are a specialist subagent working on a scaffold project.

Your assignment: {description}

Files you own: {file_territory}
{context_section}
Rules:
- Only create/modify files in your territory unless absolutely necessary
- Follow the conventions provided
- Build on what previous agents created — do not overwrite their files
{conventions_section}
"""


class ClaudeAdapter(CLIAdapterBase):
    """Adapter for Claude Code CLI."""

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]:
        cmd = ["claude", "-p", "--dangerously-skip-permissions"]
        if model:
            cmd.extend(["--model", model])
        cmd.append(prompt)
        return cmd

    def build_prompt(self, task: AgentTask) -> str:
        context_section = ""
        if task.context:
            context_section = f"\nContext from completed work:\n{task.context}\n"

        conventions_section = ""
        if self.conventions:
            conventions_section = f"\nConventions:\n{self.conventions}\n"

        return _SUBAGENT_PROMPT_TEMPLATE.format(
            description=task.description,
            file_territory=", ".join(task.file_territory) if task.file_territory else "(no specific files)",
            context_section=context_section,
            conventions_section=conventions_section,
        )

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str:
        return _PLANNING_PROMPT_TEMPLATE.format(
            brief=brief,
            phase=phase,
            stack=stack,
        )

    def parse_plan(self, raw_output: str, phase: str, backend: str) -> DecompositionPlan | None:
        return parse_decomposition_plan(raw_output, phase, backend)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_claude_adapter.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/ubundiforge/adapters/claude_adapter.py tests/test_claude_adapter.py
git commit -m "feat(agents): add Claude Code backend adapter"
```

---

## Task 6: Gemini and Codex Adapters

**Files:**
- Create: `src/ubundiforge/adapters/gemini_adapter.py`
- Create: `src/ubundiforge/adapters/codex_adapter.py`
- Create: `tests/test_gemini_adapter.py`
- Create: `tests/test_codex_adapter.py`

- [ ] **Step 1: Write tests for Gemini adapter**

```python
# tests/test_gemini_adapter.py
"""Tests for Gemini CLI backend adapter."""

from ubundiforge.adapters.gemini_adapter import GeminiAdapter
from ubundiforge.protocol import AgentTask


class TestGeminiAdapterBuildCmd:
    def test_basic_command(self):
        adapter = GeminiAdapter(conventions="")
        cmd = adapter.build_cmd("do something")
        assert cmd[0] == "gemini"
        assert "-p" in cmd
        assert "do something" in cmd

    def test_command_with_model(self):
        adapter = GeminiAdapter(conventions="")
        cmd = adapter.build_cmd("do something", model="gemini-2.5-pro")
        assert "--model" in cmd

    def test_auto_approve_flag(self):
        adapter = GeminiAdapter(conventions="")
        cmd = adapter.build_cmd("do something")
        assert "-y" in cmd


class TestGeminiAdapterPrompts:
    def test_planning_prompt_includes_explicit_json_schema(self):
        adapter = GeminiAdapter(conventions="")
        prompt = adapter.build_planning_prompt("brief", "architecture", "fastapi")
        # Gemini needs more explicit JSON guidance
        assert "JSON" in prompt
        assert '"tasks"' in prompt

    def test_build_prompt_includes_description(self):
        adapter = GeminiAdapter(conventions="")
        task = AgentTask(
            id="t1", description="Build UI components", file_territory=["src/components/"],
            context="", dependencies=[], phase="frontend", backend="gemini",
        )
        prompt = adapter.build_prompt(task)
        assert "Build UI components" in prompt
```

- [ ] **Step 2: Write tests for Codex adapter**

```python
# tests/test_codex_adapter.py
"""Tests for Codex CLI backend adapter."""

from ubundiforge.adapters.codex_adapter import CodexAdapter
from ubundiforge.protocol import AgentTask


class TestCodexAdapterBuildCmd:
    def test_basic_command(self):
        adapter = CodexAdapter(conventions="")
        cmd = adapter.build_cmd("do something")
        assert cmd[0] == "codex"
        assert "exec" in cmd
        assert "do something" in cmd

    def test_command_with_model(self):
        adapter = CodexAdapter(conventions="")
        cmd = adapter.build_cmd("do something", model="gpt-5.4")
        assert "--model" in cmd

    def test_bypass_approvals_flag(self):
        adapter = CodexAdapter(conventions="")
        cmd = adapter.build_cmd("do something")
        assert "--dangerously-bypass-approvals-and-sandbox" in cmd


class TestCodexAdapterPrompts:
    def test_planning_prompt_uses_examples(self):
        adapter = CodexAdapter(conventions="")
        prompt = adapter.build_planning_prompt("brief", "tests", "fastapi")
        # Codex works best with concrete examples
        assert "JSON" in prompt

    def test_build_prompt_is_concise(self):
        adapter = CodexAdapter(conventions="c" * 5000)
        task = AgentTask(
            id="t1", description="Write unit tests", file_territory=["tests/"],
            context="", dependencies=[], phase="tests", backend="codex",
        )
        prompt = adapter.build_prompt(task)
        # Codex prefers concise prompts — adapter should not bloat
        assert "Write unit tests" in prompt
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_gemini_adapter.py tests/test_codex_adapter.py -v`
Expected: ImportError

- [ ] **Step 4: Implement GeminiAdapter**

```python
# src/ubundiforge/adapters/gemini_adapter.py
"""Gemini CLI backend adapter."""

from __future__ import annotations

from ubundiforge.adapters.base import CLIAdapterBase
from ubundiforge.adapters.json_parsing import parse_decomposition_plan
from ubundiforge.protocol import AgentTask, DecompositionPlan

_PLANNING_PROMPT_TEMPLATE = """\
You are a scaffold planning agent. Decompose the following project phase \
into focused subagent tasks.

Brief:
{brief}

Phase: {phase}
Stack: {stack}

Create 2-6 tasks with non-overlapping file territories for parallel tasks.

You MUST respond with ONLY a valid JSON object. No text before or after. \
No markdown fences. The JSON must have this exact schema:

{{
  "tasks": [
    {{
      "id": "task-1",
      "description": "string — what this subagent should build",
      "file_territory": ["string — paths this task owns"],
      "dependencies": ["string — task IDs that must complete first"]
    }}
  ],
  "execution_order": [["task-1"], ["task-2", "task-3"]],
  "rationale": "string — why this decomposition"
}}

Respond with ONLY the JSON object. Nothing else.
"""

_SUBAGENT_PROMPT_TEMPLATE = """\
You are a specialist subagent working on a scaffold project.

Your assignment: {description}

Files you own: {file_territory}
{context_section}
Rules:
- Only create/modify files in your territory unless absolutely necessary
- Follow the conventions provided
- Build on what previous agents created — do not overwrite their files
{conventions_section}
"""


class GeminiAdapter(CLIAdapterBase):
    """Adapter for Gemini CLI."""

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]:
        cmd = ["gemini", "-p", prompt, "-y"]
        if model:
            cmd.extend(["--model", model])
        return cmd

    def build_prompt(self, task: AgentTask) -> str:
        context_section = ""
        if task.context:
            context_section = f"\nContext from completed work:\n{task.context}\n"

        conventions_section = ""
        if self.conventions:
            conventions_section = f"\nConventions:\n{self.conventions}\n"

        return _SUBAGENT_PROMPT_TEMPLATE.format(
            description=task.description,
            file_territory=", ".join(task.file_territory) if task.file_territory else "(no specific files)",
            context_section=context_section,
            conventions_section=conventions_section,
        )

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str:
        return _PLANNING_PROMPT_TEMPLATE.format(brief=brief, phase=phase, stack=stack)

    def parse_plan(self, raw_output: str, phase: str, backend: str) -> DecompositionPlan | None:
        return parse_decomposition_plan(raw_output, phase, backend)
```

- [ ] **Step 5: Implement CodexAdapter**

```python
# src/ubundiforge/adapters/codex_adapter.py
"""Codex CLI backend adapter."""

from __future__ import annotations

from ubundiforge.adapters.base import CLIAdapterBase
from ubundiforge.adapters.json_parsing import parse_decomposition_plan
from ubundiforge.protocol import AgentTask, DecompositionPlan

_PLANNING_PROMPT_TEMPLATE = """\
Decompose this scaffold phase into subagent tasks. Return JSON only.

Brief: {brief}
Phase: {phase}
Stack: {stack}

Example response:
{{
  "tasks": [
    {{"id": "task-1", "description": "Create project skeleton", "file_territory": ["pyproject.toml", "src/"], "dependencies": []}},
    {{"id": "task-2", "description": "Write data models", "file_territory": ["models/"], "dependencies": ["task-1"]}}
  ],
  "execution_order": [["task-1"], ["task-2"]],
  "rationale": "Skeleton first so models have a package to live in"
}}

Now decompose the above brief into 2-6 tasks. Return ONLY JSON.
"""

_SUBAGENT_PROMPT_TEMPLATE = """\
Assignment: {description}
Files you own: {file_territory}
{context_section}
Rules:
- Only create/modify files in your territory
- Build on previous agents' work — do not overwrite
{conventions_section}
"""


class CodexAdapter(CLIAdapterBase):
    """Adapter for Codex CLI."""

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]:
        cmd = ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox"]
        if model:
            cmd.extend(["--model", model])
        cmd.append(prompt)
        return cmd

    def build_prompt(self, task: AgentTask) -> str:
        context_section = ""
        if task.context:
            context_section = f"\nContext:\n{task.context}\n"

        conventions_section = ""
        if self.conventions:
            conventions_section = f"\nConventions:\n{self.conventions}\n"

        return _SUBAGENT_PROMPT_TEMPLATE.format(
            description=task.description,
            file_territory=", ".join(task.file_territory) if task.file_territory else "(none)",
            context_section=context_section,
            conventions_section=conventions_section,
        )

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str:
        return _PLANNING_PROMPT_TEMPLATE.format(brief=brief, phase=phase, stack=stack)

    def parse_plan(self, raw_output: str, phase: str, backend: str) -> DecompositionPlan | None:
        return parse_decomposition_plan(raw_output, phase, backend)
```

- [ ] **Step 6: Run all adapter tests**

Run: `uv run pytest tests/test_gemini_adapter.py tests/test_codex_adapter.py -v`
Expected: All PASS

- [ ] **Step 7: Update adapters/__init__.py with registry**

```python
# src/ubundiforge/adapters/__init__.py
"""Multi-agent backend adapters."""

from __future__ import annotations

from ubundiforge.adapters.claude_adapter import ClaudeAdapter
from ubundiforge.adapters.codex_adapter import CodexAdapter
from ubundiforge.adapters.gemini_adapter import GeminiAdapter

ADAPTER_REGISTRY: dict[str, type] = {
    "claude": ClaudeAdapter,
    "gemini": GeminiAdapter,
    "codex": CodexAdapter,
}


def get_adapter(backend: str, conventions: str = "") -> ClaudeAdapter | GeminiAdapter | CodexAdapter:
    """Get the adapter instance for a backend name."""
    adapter_cls = ADAPTER_REGISTRY.get(backend)
    if adapter_cls is None:
        raise ValueError(f"No adapter for backend: {backend}")
    return adapter_cls(conventions=conventions)
```

- [ ] **Step 8: Commit**

```bash
git add src/ubundiforge/adapters/ tests/test_gemini_adapter.py tests/test_codex_adapter.py
git commit -m "feat(agents): add Gemini and Codex adapters with adapter registry"
```

---

## Task 7: Orchestrator — Context Accumulation

**Files:**
- Create: `src/ubundiforge/orchestrator.py` (partial — context logic only)
- Create: `tests/test_orchestrator.py` (partial — context tests only)

Build the orchestrator incrementally. Start with the filesystem snapshot and context accumulation logic.

- [ ] **Step 1: Write tests for filesystem snapshot and context building**

```python
# tests/test_orchestrator.py
"""Tests for multi-agent orchestrator."""

from pathlib import Path

from ubundiforge.orchestrator import (
    snapshot_directory,
    diff_snapshots,
    build_context_summary,
    accumulate_context,
    CONTEXT_CAP,
)
from ubundiforge.protocol import AgentTask


class TestSnapshotDirectory:
    def test_snapshot_empty_dir(self, tmp_path):
        snap = snapshot_directory(tmp_path)
        assert snap == {}

    def test_snapshot_with_files(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "config.json").write_text("{}")
        snap = snapshot_directory(tmp_path)
        assert "main.py" in snap
        assert "config.json" in snap

    def test_snapshot_nested(self, tmp_path):
        sub = tmp_path / "src" / "app"
        sub.mkdir(parents=True)
        (sub / "main.py").write_text("app")
        snap = snapshot_directory(tmp_path)
        assert "src/app/main.py" in snap


class TestDiffSnapshots:
    def test_detects_new_files(self, tmp_path):
        before = {}
        (tmp_path / "new.py").write_text("new")
        after = snapshot_directory(tmp_path)
        created, modified = diff_snapshots(before, after)
        assert "new.py" in created
        assert modified == []

    def test_detects_modified_files(self, tmp_path):
        (tmp_path / "existing.py").write_text("v1")
        before = snapshot_directory(tmp_path)
        (tmp_path / "existing.py").write_text("v2")
        after = snapshot_directory(tmp_path)
        created, modified = diff_snapshots(before, after)
        assert created == []
        assert "existing.py" in modified

    def test_no_changes(self, tmp_path):
        (tmp_path / "stable.py").write_text("stable")
        snap = snapshot_directory(tmp_path)
        created, modified = diff_snapshots(snap, snap)
        assert created == []
        assert modified == []


class TestBuildContextSummary:
    def test_summary_includes_description(self):
        task = AgentTask(
            id="t1", description="Create project skeleton",
            file_territory=[], context="", dependencies=[],
            phase="p", backend="b",
        )
        summary = build_context_summary(
            task, files_created=["main.py", "config.json"],
            files_modified=[], project_dir=Path("/tmp/test"),
        )
        assert "Create project skeleton" in summary
        assert "main.py" in summary

    def test_summary_includes_modified_files(self):
        task = AgentTask(
            id="t1", description="Update routes",
            file_territory=[], context="", dependencies=[],
            phase="p", backend="b",
        )
        summary = build_context_summary(
            task, files_created=[], files_modified=["routes.py"],
            project_dir=Path("/tmp/test"),
        )
        assert "routes.py" in summary


class TestAccumulateContext:
    def test_appends_summaries(self):
        ctx = ""
        ctx = accumulate_context(ctx, "First task done: created main.py")
        ctx = accumulate_context(ctx, "Second task done: created models.py")
        assert "First task" in ctx
        assert "Second task" in ctx

    def test_respects_cap(self):
        ctx = ""
        for i in range(200):
            ctx = accumulate_context(ctx, f"Task {i}: " + "x" * 100)
        assert len(ctx) <= CONTEXT_CAP + 200  # some tolerance for the compression step

    def test_compresses_old_summaries_when_capped(self):
        ctx = ""
        # Add a long early summary
        ctx = accumulate_context(ctx, "Early task: " + "detail " * 500)
        # Add recent summaries
        for i in range(20):
            ctx = accumulate_context(ctx, f"Recent task {i}: created file_{i}.py")
        # Recent content should survive; early detail may be compressed
        assert "Recent task 19" in ctx
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_orchestrator.py -v`
Expected: ImportError

- [ ] **Step 3: Implement context accumulation in orchestrator.py**

```python
# src/ubundiforge/orchestrator.py
"""Multi-agent orchestrator — plan, execute, reconcile, report."""

from __future__ import annotations

import os
from pathlib import Path

from ubundiforge.protocol import AgentTask

CONTEXT_CAP = 12_000  # characters


def snapshot_directory(project_dir: Path) -> dict[str, float]:
    """Snapshot all files in a directory with their modification times.

    Returns a dict mapping relative path -> mtime.
    """
    result: dict[str, float] = {}
    for root, _dirs, files in os.walk(project_dir):
        for fname in files:
            full = Path(root) / fname
            rel = str(full.relative_to(project_dir))
            try:
                result[rel] = full.stat().st_mtime
            except OSError:
                pass
    return result


def diff_snapshots(
    before: dict[str, float], after: dict[str, float]
) -> tuple[list[str], list[str]]:
    """Compare two directory snapshots.

    Returns (files_created, files_modified).
    """
    created = [f for f in after if f not in before]
    modified = [
        f for f in after
        if f in before and after[f] != before[f]
    ]
    return sorted(created), sorted(modified)


def build_context_summary(
    task: AgentTask,
    files_created: list[str],
    files_modified: list[str],
    project_dir: Path,
) -> str:
    """Build a context summary for downstream tasks.

    Includes task description, files created/modified, and key file
    contents (first 200 lines of .py/.ts/.json files).
    """
    lines = [f"Completed: {task.description}"]

    if files_created:
        lines.append(f"Files created: {', '.join(files_created)}")
    if files_modified:
        lines.append(f"Files modified: {', '.join(files_modified)}")

    # Include key file contents for downstream context
    content_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".json"}
    for fname in files_created[:10]:  # cap to avoid bloat
        ext = Path(fname).suffix
        if ext in content_extensions:
            full_path = project_dir / fname
            if full_path.exists():
                try:
                    content = full_path.read_text(errors="replace")
                    content_lines = content.splitlines()[:200]
                    if content_lines:
                        lines.append(f"\n--- {fname} ---")
                        lines.extend(content_lines)
                except OSError:
                    pass

    return "\n".join(lines)


def accumulate_context(existing: str, new_summary: str) -> str:
    """Append a new task summary to the accumulated context.

    When total exceeds CONTEXT_CAP, older summaries are compressed
    to filename-only lists while recent summaries retain full content.
    """
    if not existing:
        return new_summary

    combined = existing + "\n\n" + new_summary

    if len(combined) <= CONTEXT_CAP:
        return combined

    # Split into sections (double newline separated)
    sections = combined.split("\n\n")
    if len(sections) <= 2:
        return combined[:CONTEXT_CAP]

    # Keep recent sections full, compress older ones
    # Start compressing from the oldest until we're under cap
    while len("\n\n".join(sections)) > CONTEXT_CAP and len(sections) > 2:
        oldest = sections[0]
        # Compress: keep only the "Completed:" and "Files created:" lines
        compressed_lines = []
        for line in oldest.splitlines():
            if line.startswith(("Completed:", "Files created:", "Files modified:")):
                compressed_lines.append(line)
        sections[0] = "\n".join(compressed_lines) if compressed_lines else sections[0][:100]

        if len("\n\n".join(sections)) > CONTEXT_CAP:
            sections.pop(0)  # drop oldest entirely if still too big

    return "\n\n".join(sections)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_orchestrator.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/ubundiforge/orchestrator.py tests/test_orchestrator.py
git commit -m "feat(agents): add orchestrator context accumulation and filesystem diffing"
```

---

## Task 8: Orchestrator — Plan, Execute, Reconcile, Report

**Files:**
- Modify: `src/ubundiforge/orchestrator.py`
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Write tests for the full orchestration flow**

Add to `tests/test_orchestrator.py`:

```python
from unittest.mock import MagicMock, patch, call
from concurrent.futures import ThreadPoolExecutor

from ubundiforge.orchestrator import run_phase_orchestrated, _execute_task_graph, _make_single_task_plan
from ubundiforge.protocol import AgentResult, AgentTask, DecompositionPlan, ProgressEvent


class TestMakeSingleTaskPlan:
    def test_creates_single_task_fallback(self):
        plan = _make_single_task_plan(
            brief="Build everything",
            phase="architecture",
            backend="claude",
        )
        assert len(plan.tasks) == 1
        assert plan.execution_order == [[plan.tasks[0].id]]
        assert plan.tasks[0].phase == "architecture"
        assert plan.tasks[0].backend == "claude"
        assert "Build everything" in plan.tasks[0].description


class TestExecuteTaskGraph:
    def test_executes_sequential_tasks(self, tmp_path):
        task1 = AgentTask(
            id="t1", description="first", file_territory=[], context="",
            dependencies=[], phase="p", backend="b",
        )
        task2 = AgentTask(
            id="t2", description="second", file_territory=[], context="",
            dependencies=["t1"], phase="p", backend="b",
        )
        plan = DecompositionPlan(
            tasks=[task1, task2],
            execution_order=[["t1"], ["t2"]],
            rationale="sequential",
        )

        mock_adapter = MagicMock()
        mock_adapter.execute.return_value = AgentResult(
            task_id="", files_created=[], files_modified=[],
            summary="Done", success=True, duration=1.0, returncode=0,
        )

        results = _execute_task_graph(
            plan=plan,
            adapter=mock_adapter,
            project_dir=tmp_path,
            on_progress=lambda e: None,
        )
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_skips_tasks_depending_on_failed(self, tmp_path):
        task1 = AgentTask(
            id="t1", description="fails", file_territory=[], context="",
            dependencies=[], phase="p", backend="b",
        )
        task2 = AgentTask(
            id="t2", description="depends on t1", file_territory=[], context="",
            dependencies=["t1"], phase="p", backend="b",
        )
        plan = DecompositionPlan(
            tasks=[task1, task2],
            execution_order=[["t1"], ["t2"]],
            rationale="sequential",
        )

        def mock_execute(task, project_dir, on_progress):
            if task.id == "t1":
                return AgentResult(
                    task_id="t1", files_created=[], files_modified=[],
                    summary="Failed", success=False, duration=1.0, returncode=1,
                )
            return AgentResult(
                task_id=task.id, files_created=[], files_modified=[],
                summary="Done", success=True, duration=1.0, returncode=0,
            )

        mock_adapter = MagicMock()
        mock_adapter.execute.side_effect = mock_execute

        results = _execute_task_graph(
            plan=plan,
            adapter=mock_adapter,
            project_dir=tmp_path,
            on_progress=lambda e: None,
        )
        # t2 should be skipped because t1 failed
        assert len(results) == 2
        skipped = [r for r in results if r.task_id == "t2"]
        assert len(skipped) == 1
        assert skipped[0].success is False


    def test_executes_parallel_tasks_in_group(self, tmp_path):
        task1 = AgentTask(
            id="t1", description="first", file_territory=[], context="",
            dependencies=[], phase="p", backend="b",
        )
        task2 = AgentTask(
            id="t2", description="second", file_territory=[], context="",
            dependencies=[], phase="p", backend="b",
        )
        plan = DecompositionPlan(
            tasks=[task1, task2],
            execution_order=[["t1", "t2"]],  # parallel group
            rationale="parallel",
        )

        call_order = []

        def mock_execute(task, project_dir, on_progress):
            call_order.append(task.id)
            return AgentResult(
                task_id=task.id, files_created=[], files_modified=[],
                summary="Done", success=True, duration=1.0, returncode=0,
            )

        mock_adapter = MagicMock()
        mock_adapter.execute.side_effect = mock_execute

        results = _execute_task_graph(
            plan=plan,
            adapter=mock_adapter,
            project_dir=tmp_path,
            on_progress=lambda e: None,
        )
        assert len(results) == 2
        assert all(r.success for r in results)
        # Both tasks should have been called
        assert set(call_order) == {"t1", "t2"}

    def test_skips_nonexistent_task_ids_in_execution_order(self, tmp_path):
        task1 = AgentTask(
            id="t1", description="real task", file_territory=[], context="",
            dependencies=[], phase="p", backend="b",
        )
        plan = DecompositionPlan(
            tasks=[task1],
            execution_order=[["t1", "t-nonexistent"]],  # t-nonexistent not in tasks
            rationale="with ghost",
        )

        mock_adapter = MagicMock()
        mock_adapter.execute.return_value = AgentResult(
            task_id="t1", files_created=[], files_modified=[],
            summary="Done", success=True, duration=1.0, returncode=0,
        )

        results = _execute_task_graph(
            plan=plan,
            adapter=mock_adapter,
            project_dir=tmp_path,
            on_progress=lambda e: None,
        )
        # Should complete with just t1, ignoring the nonexistent task
        assert len(results) == 1
        assert results[0].task_id == "t1"


class TestRunPhaseOrchestrated:
    @patch("ubundiforge.orchestrator.get_adapter")
    def test_falls_back_on_bad_plan(self, mock_get_adapter, tmp_path):
        mock_adapter = MagicMock()
        mock_adapter.build_planning_prompt.return_value = "plan prompt"
        mock_adapter.build_cmd.return_value = ["echo", "not json"]
        mock_adapter.parse_plan.return_value = None  # parse fails
        mock_adapter.execute.return_value = AgentResult(
            task_id="fallback", files_created=[], files_modified=[],
            summary="Done", success=True, duration=1.0, returncode=0,
        )
        mock_get_adapter.return_value = mock_adapter

        returncode = run_phase_orchestrated(
            phase="architecture",
            backend="claude",
            prompt="Build a FastAPI app",
            project_dir=tmp_path,
            stack="fastapi",
            conventions="",
        )
        # Should still complete via fallback
        assert returncode == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_orchestrator.py::TestMakeSingleTaskPlan tests/test_orchestrator.py::TestExecuteTaskGraph tests/test_orchestrator.py::TestRunPhaseOrchestrated -v`
Expected: ImportError for new functions

- [ ] **Step 3: Implement the full orchestrator flow**

Add to `src/ubundiforge/orchestrator.py`:

```python
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from ubundiforge.adapters import get_adapter
from ubundiforge.protocol import AgentResult, DecompositionPlan, ProgressEvent


def _make_single_task_plan(brief: str, phase: str, backend: str) -> DecompositionPlan:
    """Create a single-task fallback plan (equivalent to standard mode)."""
    task = AgentTask(
        id="fallback-1",
        description=brief,
        file_territory=[],
        context="",
        dependencies=[],
        phase=phase,
        backend=backend,
    )
    return DecompositionPlan(
        tasks=[task],
        execution_order=[["fallback-1"]],
        rationale="Single-task fallback",
    )


def _get_plan(
    adapter,
    brief: str,
    phase: str,
    stack: str,
    backend: str,
    project_dir: Path,
    model: str | None,
) -> DecompositionPlan:
    """Make a planning CLI call and parse the result. Falls back to single-task."""
    planning_prompt = adapter.build_planning_prompt(brief, phase, stack)
    cmd = adapter.build_cmd(planning_prompt, model)

    for attempt in range(2):
        try:
            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5 min for planning
            )
            if result.returncode == 0 and result.stdout.strip():
                plan = adapter.parse_plan(result.stdout, phase, backend)
                if plan is not None:
                    return plan
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Second attempt: ask for JSON only
        if attempt == 0:
            planning_prompt = planning_prompt + "\n\nRespond with ONLY valid JSON. No markdown fences. No explanation."
            cmd = adapter.build_cmd(planning_prompt, model)

    return _make_single_task_plan(brief, phase, backend)


def _execute_task_graph(
    plan: DecompositionPlan,
    adapter,
    project_dir: Path,
    on_progress: Callable[[ProgressEvent], None],
) -> list[AgentResult]:
    """Walk the execution order, running tasks with context accumulation."""
    task_map = {t.id: t for t in plan.tasks}
    results: list[AgentResult] = []
    failed_ids: set[str] = set()
    context = ""

    for group in plan.execution_order:
        # Filter out tasks whose dependencies failed
        runnable = []
        for task_id in group:
            task = task_map.get(task_id)
            if task is None:
                continue
            blocked_by = set(task.dependencies) & failed_ids
            if blocked_by:
                results.append(AgentResult(
                    task_id=task_id,
                    files_created=[],
                    files_modified=[],
                    summary=f"Skipped — depends on failed: {', '.join(blocked_by)}",
                    success=False,
                    duration=0.0,
                    returncode=-1,
                ))
                failed_ids.add(task_id)
                continue
            # Inject accumulated context
            task.context = context
            runnable.append(task)

        if not runnable:
            continue

        # Execute group — snapshot per task for accurate file attribution
        if len(runnable) == 1:
            task = runnable[0]
            before_snap = snapshot_directory(project_dir)
            result = adapter.execute(task, project_dir, on_progress)
            after_snap = snapshot_directory(project_dir)
            created, modified = diff_snapshots(before_snap, after_snap)
            result.files_created = created
            result.files_modified = modified
            results.append(result)

            if not result.success:
                failed_ids.add(result.task_id)
            else:
                summary = build_context_summary(task, created, modified, project_dir)
                context = accumulate_context(context, summary)
        else:
            # Parallel group: snapshot before, run all, snapshot after.
            # Per-task file attribution is approximate for parallel tasks
            # (each task gets the combined diff). This is a known limitation
            # documented in the spec. Context accumulation uses the combined
            # diff since all parallel tasks' output is available to the next group.
            before_snap = snapshot_directory(project_dir)
            group_results = []
            with ThreadPoolExecutor(max_workers=len(runnable)) as pool:
                futures = {
                    pool.submit(adapter.execute, task, project_dir, on_progress): task
                    for task in runnable
                }
                for future in futures:
                    group_results.append(future.result())

            after_snap = snapshot_directory(project_dir)
            created, modified = diff_snapshots(before_snap, after_snap)

            for result in group_results:
                result.files_created = created
                result.files_modified = modified
                results.append(result)

                if not result.success:
                    failed_ids.add(result.task_id)

            # Build one combined context summary for the whole parallel group
            successful_tasks = [
                task_map[r.task_id] for r in group_results if r.success
            ]
            if successful_tasks:
                descriptions = [t.description for t in successful_tasks]
                combined_summary = build_context_summary(
                    AgentTask(
                        id="group", description="; ".join(descriptions),
                        file_territory=[], context="", dependencies=[],
                        phase="", backend="",
                    ),
                    created, modified, project_dir,
                )
                context = accumulate_context(context, combined_summary)

    return results


def _reconcile(
    adapter,
    project_dir: Path,
    model: str | None,
) -> int:
    """Run a lightweight cleanup pass over the project directory."""
    reconcile_prompt = (
        "Review the project directory. Check for: missing imports between modules, "
        "inconsistent naming, broken references, incomplete __init__.py files. "
        "Fix any issues you find. Be concise."
    )
    cmd = adapter.build_cmd(reconcile_prompt, model)
    try:
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError):
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
    phase_context: list[dict] | None = None,
) -> int:
    """Run a scaffold phase using multi-agent orchestration.

    1. Get decomposition plan via CLI call
    2. Execute task graph with context accumulation
    3. Reconcile (cleanup pass)
    4. Return 0 if all critical tasks succeeded, 1 otherwise
    """
    adapter = get_adapter(backend, conventions)
    project_dir.mkdir(parents=True, exist_ok=True)

    events: list[ProgressEvent] = []

    def on_progress(event: ProgressEvent) -> None:
        events.append(event)
        # UI wiring: print activity line to console
        activity_text = map_progress_to_activity(event)
        if verbose:
            # Verbose: show full event details
            from ubundiforge.ui import create_console, subtle
            console = create_console()
            console.print(subtle(f"  [{event.task_id}] {activity_text}"))

    # 1. Plan
    plan = _get_plan(adapter, prompt, phase, stack, backend, project_dir, model)

    if verbose and len(plan.tasks) > 1:
        _render_decomposition_plan(plan)

    # Skip decomposition overhead for single-task plans (whether fallback
    # or the LLM legitimately returned only 1 task)
    if len(plan.tasks) == 1:
        result = adapter.execute(plan.tasks[0], project_dir, on_progress)
        return result.returncode

    # 2. Execute
    results = _execute_task_graph(plan, adapter, project_dir, on_progress)

    # 3. Reconcile (non-fatal — log warning on failure)
    reconcile_rc = _reconcile(adapter, project_dir, model)
    if reconcile_rc != 0:
        import logging
        logging.getLogger(__name__).warning(
            "Reconciliation pass failed (exit %d) — scaffold may need manual cleanup",
            reconcile_rc,
        )

    # 4. Report
    failed = [r for r in results if not r.success]
    return 1 if failed else 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_orchestrator.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/ubundiforge/orchestrator.py tests/test_orchestrator.py
git commit -m "feat(agents): add orchestrator plan/execute/reconcile/report flow"
```

---

## Task 9: UI Integration — Progress Event Mapping

**Files:**
- Modify: `src/ubundiforge/orchestrator.py`
- Create: `tests/test_orchestrator_ui.py`

- [ ] **Step 1: Write tests for progress event to activity feed mapping**

```python
# tests/test_orchestrator_ui.py
"""Tests for orchestrator UI integration."""

from ubundiforge.orchestrator import map_progress_to_activity
from ubundiforge.protocol import ProgressEvent


class TestMapProgressToActivity:
    def test_started_event(self):
        event = ProgressEvent(
            task_id="t1",
            agent_label="Data layer agent",
            event_type="started",
            message="Starting data models",
            timestamp=0.0,
        )
        text = map_progress_to_activity(event)
        assert "Data layer agent" in text
        assert "Starting data models" in text

    def test_progress_event(self):
        event = ProgressEvent(
            task_id="t1",
            agent_label="Data layer agent",
            event_type="progress",
            message="Writing models and schemas",
            timestamp=0.0,
        )
        text = map_progress_to_activity(event)
        assert "Data layer agent" in text

    def test_completed_event(self):
        event = ProgressEvent(
            task_id="t1",
            agent_label="Data layer agent",
            event_type="completed",
            message="Done",
            timestamp=0.0,
        )
        text = map_progress_to_activity(event)
        assert "Data layer agent" in text
        assert "Done" in text

    def test_failed_event(self):
        event = ProgressEvent(
            task_id="t1",
            agent_label="Data layer agent",
            event_type="failed",
            message="Exit 1",
            timestamp=0.0,
        )
        text = map_progress_to_activity(event)
        assert "Failed" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_orchestrator_ui.py -v`
Expected: ImportError for `map_progress_to_activity`

- [ ] **Step 3: Implement progress mapping**

Add to `src/ubundiforge/orchestrator.py`:

```python
def _render_decomposition_plan(plan: DecompositionPlan) -> None:
    """Render the decomposition plan to console (verbose/dry-run mode)."""
    from ubundiforge.ui import create_console, grouped_lines, make_panel, subtle, bullet

    console = create_console()
    lines = [subtle(f"Rationale: {plan.rationale}")]
    for i, group in enumerate(plan.execution_order):
        task_map = {t.id: t for t in plan.tasks}
        if len(group) == 1:
            task = task_map.get(group[0])
            if task:
                lines.append(bullet(
                    f"Step {i + 1}: {task.description} [{', '.join(task.file_territory) or 'no files'}]",
                    accent="aqua",
                ))
        else:
            parts = []
            for tid in group:
                task = task_map.get(tid)
                if task:
                    parts.append(f"{task.description} [{', '.join(task.file_territory) or 'no files'}]")
            lines.append(bullet(f"Step {i + 1} (parallel): {' | '.join(parts)}", accent="amber"))

    console.print(make_panel(grouped_lines(lines), title="Agent Decomposition", accent="violet"))


def map_progress_to_activity(event: ProgressEvent) -> str:
    """Convert a ProgressEvent into an activity feed string."""
    if event.event_type == "started":
        return f"{event.agent_label}: {event.message}"
    elif event.event_type == "progress":
        return f"{event.agent_label}: {event.message}"
    elif event.event_type == "completed":
        return f"{event.agent_label}: Done"
    elif event.event_type == "failed":
        return f"{event.agent_label}: Failed — {event.message}"
    return f"{event.agent_label}: {event.message}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_orchestrator_ui.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/ubundiforge/orchestrator.py tests/test_orchestrator_ui.py
git commit -m "feat(agents): add progress event to activity feed mapping"
```

---

## Task 10: CLI Integration — --agents Flag

**Files:**
- Modify: `src/ubundiforge/cli.py`

**Note:** Read `cli.py` at implementation time. The codebase may have changed since this plan was written. The key areas to modify:

1. The main `forge` command function signature (add `--agents` option)
2. The **main scaffold execution loop** where `run_ai()` and `run_ai_parallel()` are called for phases — this is where the orchestrator routing goes
3. The **dry-run code path** — add decomposition preview
4. The **export code path** — append decomposition section

**Important:** Only wrap the scaffold flow's `run_ai()` and `run_ai_parallel()` calls. Do NOT modify `run_ai()` calls in the `evolve` command or `replay` command — those are separate commands with their own flows.

- [ ] **Step 1: Add --agents flag to the CLI**

In `cli.py`, find the main `forge` command function. Add the `--agents` option:

```python
agents: Annotated[bool, typer.Option("--agents/--no-agents", help="Enable multi-agent orchestration (higher quality, slower)")] = False,
```

- [ ] **Step 2: Add config-based default for agents mode**

In the CLI function, after loading the forge config, check for agents default:

```python
# After loading config
if not agents:
    agents = forge_config.get("agents", False)
```

- [ ] **Step 3: Add orchestrator routing in the phase execution loop**

The existing scaffold flow has three execution paths:
1. **Serial first phase** — `run_ai()` for the first phase
2. **Parallel middle phases** — `run_ai_parallel()` for middle phases
3. **Serial last phase** — `run_ai()` for the last phase

When `--agents` is enabled, ALL three paths route through the orchestrator instead. The orchestrator handles its own parallelism internally, so `run_ai_parallel()` is replaced with sequential `run_phase_orchestrated()` calls (each of which does its own internal parallel decomposition).

For each `run_ai()` call in the scaffold loop:

```python
if agents:
    from ubundiforge.orchestrator import run_phase_orchestrated

    returncode = run_phase_orchestrated(
        phase=phase,
        backend=backend,
        prompt=assembled_prompt,
        project_dir=project_dir,
        stack=answers["stack"],
        conventions=conventions,
        model=model_override or backend_models.get(backend),
        verbose=verbose,
        phase_context=phase_context,
    )
else:
    returncode = run_ai(...)  # existing call unchanged
```

For the `run_ai_parallel()` call:

```python
if agents:
    from ubundiforge.orchestrator import run_phase_orchestrated

    parallel_results = []
    for p in parallel_phases:
        rc = run_phase_orchestrated(
            phase=p["phase"],
            backend=p["backend"],
            prompt=p["prompt"],
            project_dir=project_dir,
            stack=answers["stack"],
            conventions=conventions,
            model=p.get("model"),
            verbose=verbose,
            phase_context=phase_context,
        )
        parallel_results.append((p["label"], rc))
else:
    parallel_results = run_ai_parallel(...)  # existing call unchanged
```

- [ ] **Step 4: Handle --dry-run --agents interaction**

Find the dry-run code path. When `--agents` is also set, make the actual planning call and display the parsed decomposition plan:

```python
if dry_run and agents:
    from ubundiforge.adapters import get_adapter
    from ubundiforge.orchestrator import _get_plan, _render_decomposition_plan

    for phase, backend in phase_backends:
        adapter = get_adapter(backend, conventions)
        plan = _get_plan(adapter, assembled_prompt, phase, stack, backend, project_dir, model)
        if len(plan.tasks) > 1:
            console.print(status_line(f"Phase: {phase}", accent="violet"))
            _render_decomposition_plan(plan)
        else:
            console.print(status_line(f"Phase: {phase} — single task (no decomposition)", accent="aqua"))
```

- [ ] **Step 5: Handle --export --agents interaction**

Find the export code path. After the normal prompt export, append the decomposition:

```python
if export_path and agents:
    from ubundiforge.adapters import get_adapter
    from ubundiforge.orchestrator import _get_plan

    with open(export_path, "a") as f:
        f.write("\n\n## Agent Decomposition\n\n")
        for phase, backend in phase_backends:
            adapter = get_adapter(backend, conventions)
            plan = _get_plan(adapter, assembled_prompt, phase, stack, backend, project_dir, model)
            f.write(f"### {phase} ({backend})\n\n")
            f.write(f"Rationale: {plan.rationale}\n\n")
            for i, group in enumerate(plan.execution_order):
                task_map = {t.id: t for t in plan.tasks}
                names = [task_map[tid].description for tid in group if tid in task_map]
                parallel = " (parallel)" if len(group) > 1 else ""
                f.write(f"- Step {i + 1}{parallel}: {', '.join(names)}\n")
            f.write("\n")
```

- [ ] **Step 6: Run full test suite to verify no regressions**

Run: `uv run pytest -v`
Expected: All existing tests PASS. The `--agents` flag defaults to False, so existing behavior is unchanged.

- [ ] **Step 7: Run smoke test**

```bash
./forge --dry-run --agents --name smoke --stack fastapi --description "test" --no-docker
```

Expected: Should show the normal dry-run output plus agent decomposition preview per phase.

- [ ] **Step 8: Commit**

```bash
git add src/ubundiforge/cli.py
git commit -m "feat(agents): add --agents flag with orchestrator routing in CLI"
```

---

## Task 11: Quality Signal Enhancement

**Files:**
- Create: `src/ubundiforge/agent_quality.py`
- Create: `tests/test_agent_quality.py`
- Modify: `src/ubundiforge/orchestrator.py`

**Note:** The existing `quality.py` has a specific function signature (`append_quality_signal`) designed for per-phase signals with `VerifyReport`. Rather than modifying that interface (which could break existing callers), create a separate `agent_quality.py` module for per-subagent signals. This follows the spec's "extended, not replaced" guidance.

Read `quality.py` at implementation time to understand the existing JSONL format and reuse the same log path (`~/.forge/quality.jsonl`).

- [ ] **Step 1: Write tests for agent quality signals**

```python
# tests/test_agent_quality.py
"""Tests for per-subagent quality signal recording."""

import json
from pathlib import Path

from ubundiforge.agent_quality import append_agent_quality_signal


class TestAppendAgentQualitySignal:
    def test_writes_signal_to_jsonl(self, tmp_path):
        log_path = tmp_path / "quality.jsonl"
        append_agent_quality_signal(
            log_path=log_path,
            phase="architecture",
            backend="claude",
            task_id="task-1",
            task_description="Project skeleton",
            success=True,
            duration=12.5,
        )
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["phase"] == "architecture"
        assert entry["backend"] == "claude"
        assert entry["agent_task_id"] == "task-1"
        assert entry["success"] is True
        assert entry["agent_duration"] == 12.5

    def test_appends_multiple_signals(self, tmp_path):
        log_path = tmp_path / "quality.jsonl"
        for i in range(3):
            append_agent_quality_signal(
                log_path=log_path,
                phase="architecture",
                backend="claude",
                task_id=f"task-{i}",
                task_description=f"Task {i}",
                success=True,
                duration=float(i),
            )
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 3

    def test_records_failure(self, tmp_path):
        log_path = tmp_path / "quality.jsonl"
        append_agent_quality_signal(
            log_path=log_path,
            phase="tests",
            backend="codex",
            task_id="task-1",
            task_description="Write tests",
            success=False,
            duration=5.0,
        )
        entry = json.loads(log_path.read_text().strip())
        assert entry["success"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_agent_quality.py -v`
Expected: ImportError

- [ ] **Step 3: Implement agent_quality.py**

```python
# src/ubundiforge/agent_quality.py
"""Per-subagent quality signal recording for multi-agent orchestration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def append_agent_quality_signal(
    *,
    log_path: Path,
    phase: str,
    backend: str,
    task_id: str,
    task_description: str,
    success: bool,
    duration: float,
) -> None:
    """Append a per-subagent quality signal to the JSONL log."""
    entry = {
        "type": "agent_task",
        "phase": phase,
        "backend": backend,
        "agent_task_id": task_id,
        "agent_task_description": task_description,
        "success": success,
        "agent_duration": duration,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_agent_quality.py -v`
Expected: All PASS

- [ ] **Step 5: Wire into orchestrator**

In `orchestrator.py`, after each subagent task completes in `_execute_task_graph`, call `append_agent_quality_signal`. Import the quality JSONL path from the existing quality module (read at implementation time — likely `QUALITY_LOG_PATH` or similar from `quality.py`).

- [ ] **Step 6: Commit**

```bash
git add src/ubundiforge/agent_quality.py tests/test_agent_quality.py src/ubundiforge/orchestrator.py
git commit -m "feat(agents): add per-subagent quality signal recording"
```

**Deferred:** The spec's Phase 4 "Intelligence" — where the orchestrator reads quality history to inform planning decisions — is explicitly deferred to a future plan. This task only records signals.

---

## Task 12: Dashboard Enhancement

**Files:**
- Modify: `src/ubundiforge/dashboard.py` (read at implementation time to find `render_dashboard` function)
- Modify: the existing dashboard test file

**Note:** Read `dashboard.py` at implementation time. Find the `render_dashboard` function and understand its current parameters and rendering pattern. The change is small — add one optional parameter and one conditional row.

- [ ] **Step 1: Write test for agent task summary row**

Add to the existing dashboard test file (find the test class for `render_dashboard`):

```python
def test_dashboard_includes_agent_stats_when_provided(self, ...):
    """When agent_stats is provided, dashboard output includes task counts."""
    # Call render_dashboard with its existing required params plus:
    #   agent_stats={"planned": 4, "completed": 4, "failed": 0}
    # Capture the console output and assert it contains "Agent tasks"
    # Use the same capture pattern as existing dashboard tests in the file.
    ...
    assert "Agent tasks" in output
    assert "4 planned" in output

def test_dashboard_omits_agent_stats_when_none(self, ...):
    """Without agent_stats, dashboard output has no agent row."""
    # Call render_dashboard with agent_stats=None (or omitted)
    # Assert "Agent tasks" NOT in output
    ...
    assert "Agent tasks" not in output
```

The exact test setup depends on how existing dashboard tests capture output — follow the same pattern.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_dashboard.py -v` (or wherever dashboard tests live)
Expected: Fail — `agent_stats` parameter not accepted yet

- [ ] **Step 3: Add agent_stats parameter to render_dashboard**

In `dashboard.py`, add `agent_stats: dict | None = None` as an optional parameter to `render_dashboard`. In the body, after the existing summary rows, add:

```python
if agent_stats:
    planned = agent_stats.get("planned", 0)
    completed = agent_stats.get("completed", 0)
    failed = agent_stats.get("failed", 0)
    # Add a row using the same Rich pattern as existing rows:
    lines.append(subtle(f"Agent tasks: {planned} planned, {completed} completed, {failed} failed"))
```

Adapt the Rich rendering pattern to match whatever the existing dashboard uses (it may use a table, panel, or grouped_lines — follow the existing pattern).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: All PASS

- [ ] **Step 5: Wire agent_stats into cli.py**

In `cli.py`, after the orchestrated execution completes, compute and pass agent_stats:

```python
if agents:
    agent_stats = {
        "planned": len(all_results),
        "completed": sum(1 for r in all_results if r.success),
        "failed": sum(1 for r in all_results if not r.success),
    }
else:
    agent_stats = None

render_dashboard(..., agent_stats=agent_stats)
```

- [ ] **Step 6: Run tests and commit**

Run: `uv run pytest -v`
Expected: All PASS

```bash
git add src/ubundiforge/dashboard.py src/ubundiforge/cli.py tests/
git commit -m "feat(agents): add agent task summary to post-scaffold dashboard"
```

---

## Task 13: Full Integration Test and Final Verification

- [ ] **Step 1: Run the complete test suite**

Run: `uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Run linter**

Run: `uv run ruff check src/ubundiforge tests`
Expected: No errors

- [ ] **Step 3: Run formatter**

Run: `uv run ruff format src/ubundiforge tests`

- [ ] **Step 4: Run smoke test without --agents (regression check)**

```bash
./forge --dry-run --name smoke --stack fastapi --description "test" --no-docker
```

Expected: Identical to pre-change behavior

- [ ] **Step 5: Run smoke test with --agents**

```bash
./forge --dry-run --agents --name smoke --stack fastapi --description "test" --no-docker
```

Expected: Shows dry-run output with agent decomposition preview (or graceful fallback)

- [ ] **Step 6: Final commit if any formatting/lint fixes**

```bash
git add -A
git commit -m "chore: lint and format fixes for multi-agent orchestration"
```
