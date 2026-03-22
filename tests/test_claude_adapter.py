"""Tests for ClaudeAdapter."""

from __future__ import annotations

from ubundiforge.adapters.claude_adapter import ClaudeAdapter
from ubundiforge.protocol import AgentTask

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(
    *,
    description: str = "Write the main module",
    file_territory: list[str] | None = None,
    context: str = "",
) -> AgentTask:
    return AgentTask(
        id="task-1",
        description=description,
        file_territory=file_territory or ["src/main.py"],
        context=context,
        dependencies=[],
        phase="scaffold",
        backend="claude",
    )


# ---------------------------------------------------------------------------
# TestClaudeAdapterBuildCmd
# ---------------------------------------------------------------------------


class TestClaudeAdapterBuildCmd:
    def test_basic_command_structure(self):
        adapter = ClaudeAdapter()
        cmd = adapter.build_cmd("some prompt")
        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert "--dangerously-skip-permissions" in cmd

    def test_without_model(self):
        adapter = ClaudeAdapter()
        cmd = adapter.build_cmd("some prompt", model=None)
        assert "--model" not in cmd

    def test_with_model(self):
        adapter = ClaudeAdapter()
        cmd = adapter.build_cmd("some prompt", model="claude-opus-4-5")
        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-opus-4-5"

    def test_has_dangerously_skip_permissions(self):
        adapter = ClaudeAdapter()
        cmd = adapter.build_cmd("irrelevant")
        assert "--dangerously-skip-permissions" in cmd


# ---------------------------------------------------------------------------
# TestClaudeAdapterBuildPrompt
# ---------------------------------------------------------------------------


class TestClaudeAdapterBuildPrompt:
    def test_includes_description(self):
        adapter = ClaudeAdapter()
        task = _make_task(description="Implement the auth module")
        prompt = adapter.build_prompt(task)
        assert "Implement the auth module" in prompt

    def test_includes_file_territory(self):
        adapter = ClaudeAdapter()
        task = _make_task(file_territory=["src/auth.py", "tests/test_auth.py"])
        prompt = adapter.build_prompt(task)
        assert "src/auth.py" in prompt
        assert "tests/test_auth.py" in prompt

    def test_includes_conventions_when_present(self):
        adapter = ClaudeAdapter(conventions="Use type hints everywhere.")
        task = _make_task()
        prompt = adapter.build_prompt(task)
        assert "Use type hints everywhere." in prompt

    def test_omits_conventions_section_when_empty(self):
        adapter = ClaudeAdapter(conventions="")
        task = _make_task()
        prompt = adapter.build_prompt(task)
        assert "Conventions:" not in prompt

    def test_includes_context_when_present(self):
        adapter = ClaudeAdapter()
        task = _make_task(context="Previous agent created the DB schema.")
        prompt = adapter.build_prompt(task)
        assert "Previous agent created the DB schema." in prompt

    def test_omits_context_section_when_empty(self):
        adapter = ClaudeAdapter()
        task = _make_task(context="")
        prompt = adapter.build_prompt(task)
        assert "Context from completed work" not in prompt


# ---------------------------------------------------------------------------
# TestClaudeAdapterPlanningPrompt
# ---------------------------------------------------------------------------


class TestClaudeAdapterPlanningPrompt:
    def test_includes_brief(self):
        adapter = ClaudeAdapter()
        prompt = adapter.build_planning_prompt(
            brief="Build a REST API", phase="scaffold", stack="fastapi"
        )
        assert "Build a REST API" in prompt

    def test_includes_phase(self):
        adapter = ClaudeAdapter()
        prompt = adapter.build_planning_prompt(brief="anything", phase="scaffold", stack="fastapi")
        assert "scaffold" in prompt

    def test_includes_stack(self):
        adapter = ClaudeAdapter()
        prompt = adapter.build_planning_prompt(brief="anything", phase="scaffold", stack="fastapi")
        assert "fastapi" in prompt

    def test_includes_json_schema_keys(self):
        adapter = ClaudeAdapter()
        prompt = adapter.build_planning_prompt(brief="anything", phase="scaffold", stack="nextjs")
        # All required schema keys must appear in the prompt
        for key in (
            "tasks",
            "execution_order",
            "rationale",
            "id",
            "description",
            "file_territory",
            "dependencies",
        ):
            assert key in prompt, f"Missing key in planning prompt: {key!r}"


# ---------------------------------------------------------------------------
# TestClaudeAdapterParsePlan
# ---------------------------------------------------------------------------


class TestClaudeAdapterParsePlan:
    _VALID_JSON = """{
  "tasks": [
    {
      "id": "task-1",
      "description": "Create the models",
      "file_territory": ["src/models.py"],
      "dependencies": []
    }
  ],
  "execution_order": [["task-1"]],
  "rationale": "Single task, nothing to parallelise"
}"""

    def test_parses_valid_plan(self):
        adapter = ClaudeAdapter()
        plan = adapter.parse_plan(self._VALID_JSON, phase="scaffold", backend="claude")
        assert plan is not None
        assert len(plan.tasks) == 1
        assert plan.tasks[0].id == "task-1"
        assert plan.rationale == "Single task, nothing to parallelise"

    def test_returns_none_for_garbage(self):
        adapter = ClaudeAdapter()
        plan = adapter.parse_plan("this is not json at all", phase="scaffold", backend="claude")
        assert plan is None
