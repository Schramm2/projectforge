"""Robust JSON extraction utilities for parsing CLI output into DecompositionPlan objects."""

from __future__ import annotations

import json
import re

from ubundiforge.protocol import AgentTask, DecompositionPlan

# Required top-level keys in a decomposition plan
_PLAN_KEYS = {"tasks", "execution_order", "rationale"}

# Required keys in each task object
_TASK_KEYS = {"id", "description", "file_territory", "dependencies"}

# Regex patterns for markdown code fences
_FENCE_JSON = re.compile(r"```json\s*\n(.*?)\n\s*```", re.DOTALL)
_FENCE_PLAIN = re.compile(r"```\s*\n(.*?)\n\s*```", re.DOTALL)


def _try_parse(text: str) -> dict | None:
    """Attempt direct JSON parse, then a trailing-comma repair pass."""
    text = text.strip()
    # Direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Repair: strip trailing commas before } or ]
    repaired = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        result = json.loads(repaired)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    return None


def _extract_by_brace_depth(text: str) -> str | None:
    """Find the first `{` in text and return the balanced substring."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def extract_json(raw: str) -> dict | None:
    """Extract a JSON object from raw CLI output using a multi-step strategy.

    Steps:
    1. Try to find JSON inside markdown fences (```json ... ``` or ``` ... ```)
    2. Find first `{` and match to closing `}` (brace depth counting)
    3. Try direct parse, then repair (strip trailing commas)
    4. Return None if all steps fail
    """
    # Step 1a: ```json fence
    for match in _FENCE_JSON.finditer(raw):
        candidate = match.group(1).strip()
        result = _try_parse(candidate)
        if result is not None:
            return result

    # Step 1b: plain ``` fence
    for match in _FENCE_PLAIN.finditer(raw):
        candidate = match.group(1).strip()
        result = _try_parse(candidate)
        if result is not None:
            return result

    # Step 2 + 3: brace depth extraction then parse/repair
    candidate = _extract_by_brace_depth(raw)
    if candidate is not None:
        return _try_parse(candidate)

    return None


def validate_plan_schema(data: dict) -> bool:
    """Return True iff data contains all required keys for a DecompositionPlan.

    Top-level requirements: tasks, execution_order, rationale.
    Each task must have: id, description, file_territory, dependencies.
    """
    if not _PLAN_KEYS.issubset(data.keys()):
        return False

    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        return False

    for task in tasks:
        if not isinstance(task, dict):
            return False
        if not _TASK_KEYS.issubset(task.keys()):
            return False

    return True


def parse_decomposition_plan(
    raw_output: str,
    phase: str,
    backend: str,
) -> DecompositionPlan | None:
    """Parse raw CLI output into a DecompositionPlan.

    Combines extract_json + validate_plan_schema + conversion to domain objects.
    Stamps `phase` and `backend` onto each AgentTask.
    Returns None if extraction or validation fails.
    """
    data = extract_json(raw_output)
    if data is None:
        return None

    if not validate_plan_schema(data):
        return None

    tasks: list[AgentTask] = []
    for raw_task in data["tasks"]:
        tasks.append(
            AgentTask(
                id=raw_task["id"],
                description=raw_task["description"],
                file_territory=raw_task["file_territory"],
                context=raw_task.get("context", ""),
                dependencies=raw_task["dependencies"],
                phase=phase,
                backend=backend,
                model=raw_task.get("model"),
            )
        )

    return DecompositionPlan(
        tasks=tasks,
        execution_order=data["execution_order"],
        rationale=data["rationale"],
    )
