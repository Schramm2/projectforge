"""Tests for AntigravityAdapter."""

from __future__ import annotations

from projectforge.adapters.antigravity_adapter import AntigravityAdapter
from projectforge.protocol import AgentTask

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
        backend="antigravity",
    )


# ---------------------------------------------------------------------------
# TestAntigravityAdapterBuildCmd
# ---------------------------------------------------------------------------


class TestAntigravityAdapterBuildCmd:
    def test_basic_command_structure(self):
        adapter = AntigravityAdapter()
        cmd = adapter.build_cmd("some prompt")
        assert cmd[0] == "agy"
        assert "--print" in cmd
        assert cmd[cmd.index("--mode") + 1] == "accept-edits"
        assert "--sandbox" in cmd

    def test_prompt_is_included(self):
        adapter = AntigravityAdapter()
        cmd = adapter.build_cmd("my test prompt")
        assert "my test prompt" in cmd

    def test_without_model(self):
        adapter = AntigravityAdapter()
        cmd = adapter.build_cmd("some prompt", model=None)
        assert "--model" not in cmd

    def test_with_model(self):
        adapter = AntigravityAdapter()
        cmd = adapter.build_cmd("some prompt", model="Gemini 3.5 Flash (High)")
        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "Gemini 3.5 Flash (High)"

    def test_does_not_skip_permissions_by_default(self):
        adapter = AntigravityAdapter()
        cmd = adapter.build_cmd("irrelevant")
        assert "--dangerously-skip-permissions" not in cmd


# ---------------------------------------------------------------------------
# TestAntigravityAdapterBuildPrompt
# ---------------------------------------------------------------------------


class TestAntigravityAdapterBuildPrompt:
    def test_includes_description(self):
        adapter = AntigravityAdapter()
        task = _make_task(description="Implement the auth module")
        prompt = adapter.build_prompt(task)
        assert "Implement the auth module" in prompt

    def test_includes_file_territory(self):
        adapter = AntigravityAdapter()
        task = _make_task(file_territory=["src/auth.py", "tests/test_auth.py"])
        prompt = adapter.build_prompt(task)
        assert "src/auth.py" in prompt
        assert "tests/test_auth.py" in prompt

    def test_includes_conventions_when_present(self):
        adapter = AntigravityAdapter(conventions="Use type hints everywhere.")
        task = _make_task()
        prompt = adapter.build_prompt(task)
        assert "Use type hints everywhere." in prompt

    def test_omits_conventions_section_when_empty(self):
        adapter = AntigravityAdapter(conventions="")
        task = _make_task()
        prompt = adapter.build_prompt(task)
        assert "Conventions:" not in prompt

    def test_includes_context_when_present(self):
        adapter = AntigravityAdapter()
        task = _make_task(context="Previous agent created the DB schema.")
        prompt = adapter.build_prompt(task)
        assert "Previous agent created the DB schema." in prompt

    def test_omits_context_section_when_empty(self):
        adapter = AntigravityAdapter()
        task = _make_task(context="")
        prompt = adapter.build_prompt(task)
        assert "Context from completed work" not in prompt


# ---------------------------------------------------------------------------
# TestAntigravityAdapterPlanningPrompt
# ---------------------------------------------------------------------------


class TestAntigravityAdapterPlanningPrompt:
    def test_includes_brief(self):
        adapter = AntigravityAdapter()
        prompt = adapter.build_planning_prompt(
            brief="Build a REST API", phase="scaffold", stack="fastapi"
        )
        assert "Build a REST API" in prompt

    def test_includes_phase(self):
        adapter = AntigravityAdapter()
        prompt = adapter.build_planning_prompt(brief="anything", phase="scaffold", stack="fastapi")
        assert "scaffold" in prompt

    def test_includes_stack(self):
        adapter = AntigravityAdapter()
        prompt = adapter.build_planning_prompt(brief="anything", phase="scaffold", stack="fastapi")
        assert "fastapi" in prompt

    def test_includes_json_schema_keys(self):
        adapter = AntigravityAdapter()
        prompt = adapter.build_planning_prompt(brief="anything", phase="scaffold", stack="nextjs")
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

    def test_includes_json_only_instruction(self):
        adapter = AntigravityAdapter()
        prompt = adapter.build_planning_prompt(brief="anything", phase="scaffold", stack="nextjs")
        assert "ONLY" in prompt
        assert "JSON" in prompt

    def test_includes_no_markdown_fences_instruction(self):
        adapter = AntigravityAdapter()
        prompt = adapter.build_planning_prompt(brief="anything", phase="scaffold", stack="nextjs")
        assert "markdown" in prompt.lower() or "fences" in prompt.lower()
