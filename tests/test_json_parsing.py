"""Tests for JSON extraction utilities in adapters.json_parsing."""

from ubundiforge.adapters.json_parsing import (
    extract_json,
    parse_decomposition_plan,
    validate_plan_schema,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_TASK = {
    "id": "task-1",
    "description": "Set up skeleton",
    "file_territory": ["src/", "pyproject.toml"],
    "dependencies": [],
}

VALID_PLAN_DICT = {
    "tasks": [MINIMAL_TASK],
    "execution_order": [["task-1"]],
    "rationale": "Start with the skeleton",
}

VALID_PLAN_JSON = """{
    "tasks": [
        {
            "id": "task-1",
            "description": "Set up skeleton",
            "file_territory": ["src/", "pyproject.toml"],
            "dependencies": []
        }
    ],
    "execution_order": [["task-1"]],
    "rationale": "Start with the skeleton"
}"""


# ---------------------------------------------------------------------------
# TestExtractJson
# ---------------------------------------------------------------------------


class TestExtractJson:
    def test_clean_json(self):
        result = extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_markdown_fences(self):
        raw = "```json\n" + VALID_PLAN_JSON + "\n```"
        result = extract_json(raw)
        assert result is not None
        assert result["rationale"] == "Start with the skeleton"

    def test_json_with_preamble_text(self):
        raw = "Here is the decomposition plan:\n\n" + VALID_PLAN_JSON
        result = extract_json(raw)
        assert result is not None
        assert "tasks" in result

    def test_json_with_trailing_text(self):
        raw = VALID_PLAN_JSON + "\n\nLet me know if you need adjustments."
        result = extract_json(raw)
        assert result is not None
        assert "tasks" in result

    def test_json_with_trailing_commas(self):
        # Trailing comma in object — invalid JSON that we repair
        raw = '{"key": "value", "list": [1, 2, 3,],}'
        result = extract_json(raw)
        assert result is not None
        assert result["key"] == "value"
        assert result["list"] == [1, 2, 3]

    def test_returns_none_for_no_json(self):
        assert extract_json("no json here at all") is None

    def test_returns_none_for_malformed_json(self):
        # Unclosed brace — cannot be repaired
        assert extract_json('{"key": "value"') is None

    def test_nested_json_objects(self):
        raw = '{"outer": {"inner": {"deep": true}}}'
        result = extract_json(raw)
        assert result == {"outer": {"inner": {"deep": True}}}

    def test_triple_backtick_without_json_label(self):
        raw = "```\n" + VALID_PLAN_JSON + "\n```"
        result = extract_json(raw)
        assert result is not None
        assert "tasks" in result


# ---------------------------------------------------------------------------
# TestValidatePlanSchema
# ---------------------------------------------------------------------------


class TestValidatePlanSchema:
    def test_valid_plan(self):
        assert validate_plan_schema(VALID_PLAN_DICT) is True

    def test_missing_tasks_key(self):
        data = {k: v for k, v in VALID_PLAN_DICT.items() if k != "tasks"}
        assert validate_plan_schema(data) is False

    def test_missing_execution_order(self):
        data = {k: v for k, v in VALID_PLAN_DICT.items() if k != "execution_order"}
        assert validate_plan_schema(data) is False

    def test_missing_rationale(self):
        data = {k: v for k, v in VALID_PLAN_DICT.items() if k != "rationale"}
        assert validate_plan_schema(data) is False

    def test_task_missing_id(self):
        task = {k: v for k, v in MINIMAL_TASK.items() if k != "id"}
        data = {**VALID_PLAN_DICT, "tasks": [task]}
        assert validate_plan_schema(data) is False

    def test_task_missing_description(self):
        task = {k: v for k, v in MINIMAL_TASK.items() if k != "description"}
        data = {**VALID_PLAN_DICT, "tasks": [task]}
        assert validate_plan_schema(data) is False

    def test_task_missing_file_territory(self):
        task = {k: v for k, v in MINIMAL_TASK.items() if k != "file_territory"}
        data = {**VALID_PLAN_DICT, "tasks": [task]}
        assert validate_plan_schema(data) is False

    def test_task_missing_dependencies(self):
        task = {k: v for k, v in MINIMAL_TASK.items() if k != "dependencies"}
        data = {**VALID_PLAN_DICT, "tasks": [task]}
        assert validate_plan_schema(data) is False


# ---------------------------------------------------------------------------
# TestParseDecompositionPlan
# ---------------------------------------------------------------------------


class TestParseDecompositionPlan:
    def test_parses_valid_output(self):
        plan = parse_decomposition_plan(VALID_PLAN_JSON, phase="architecture", backend="claude")
        assert plan is not None
        assert len(plan.tasks) == 1
        assert plan.tasks[0].id == "task-1"
        assert plan.execution_order == [["task-1"]]
        assert plan.rationale == "Start with the skeleton"

    def test_stamps_phase_and_backend(self):
        plan = parse_decomposition_plan(VALID_PLAN_JSON, phase="scaffold", backend="gemini")
        assert plan is not None
        assert plan.tasks[0].phase == "scaffold"
        assert plan.tasks[0].backend == "gemini"

    def test_returns_none_for_unparseable(self):
        result = parse_decomposition_plan("no json here", phase="architecture", backend="claude")
        assert result is None

    def test_returns_none_for_invalid_schema(self):
        # Valid JSON but missing required plan keys
        result = parse_decomposition_plan('{"foo": "bar"}', phase="architecture", backend="claude")
        assert result is None

    def test_parses_plan_in_markdown_fences(self):
        raw = "Here is the plan:\n\n```json\n" + VALID_PLAN_JSON + "\n```\n\nGood luck!"
        plan = parse_decomposition_plan(raw, phase="architecture", backend="claude")
        assert plan is not None
        assert plan.tasks[0].description == "Set up skeleton"

    def test_multiple_tasks_preserve_order(self):
        raw = """{
            "tasks": [
                {
                    "id": "task-1",
                    "description": "First",
                    "file_territory": ["src/"],
                    "dependencies": []
                },
                {
                    "id": "task-2",
                    "description": "Second",
                    "file_territory": ["tests/"],
                    "dependencies": ["task-1"]
                }
            ],
            "execution_order": [["task-1"], ["task-2"]],
            "rationale": "Sequential build"
        }"""
        plan = parse_decomposition_plan(raw, phase="scaffold", backend="claude")
        assert plan is not None
        assert len(plan.tasks) == 2
        assert plan.tasks[0].id == "task-1"
        assert plan.tasks[1].id == "task-2"
        assert plan.tasks[1].dependencies == ["task-1"]

    def test_context_defaults_to_empty_string_when_missing(self):
        # Tasks in raw JSON may not include 'context' — should default to ""
        plan = parse_decomposition_plan(VALID_PLAN_JSON, phase="architecture", backend="claude")
        assert plan is not None
        assert plan.tasks[0].context == ""
