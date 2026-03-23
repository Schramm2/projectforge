"""Tests for CodexAdapter."""

from __future__ import annotations

from ubundiforge.adapters.codex_adapter import CodexAdapter
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
        backend="codex",
    )


# ---------------------------------------------------------------------------
# TestCodexAdapterBuildCmd
# ---------------------------------------------------------------------------


class TestCodexAdapterBuildCmd:
    def test_basic_command_structure(self):
        adapter = CodexAdapter()
        cmd = adapter.build_cmd("some prompt")
        assert cmd[0] == "codex"
        assert "exec" in cmd

    def test_has_bypass_flag(self):
        adapter = CodexAdapter()
        cmd = adapter.build_cmd("irrelevant")
        assert "--dangerously-bypass-approvals-and-sandbox" in cmd

    def test_prompt_is_included(self):
        adapter = CodexAdapter()
        cmd = adapter.build_cmd("my test prompt")
        assert "my test prompt" in cmd

    def test_without_model(self):
        adapter = CodexAdapter()
        cmd = adapter.build_cmd("some prompt", model=None)
        assert "--model" not in cmd

    def test_with_model(self):
        adapter = CodexAdapter()
        cmd = adapter.build_cmd("some prompt", model="o4-mini")
        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "o4-mini"


# ---------------------------------------------------------------------------
# TestCodexAdapterBuildPrompt
# ---------------------------------------------------------------------------


class TestCodexAdapterBuildPrompt:
    def test_includes_description(self):
        adapter = CodexAdapter()
        task = _make_task(description="Implement the auth module")
        prompt = adapter.build_prompt(task)
        assert "Implement the auth module" in prompt

    def test_includes_file_territory(self):
        adapter = CodexAdapter()
        task = _make_task(file_territory=["src/auth.py", "tests/test_auth.py"])
        prompt = adapter.build_prompt(task)
        assert "src/auth.py" in prompt
        assert "tests/test_auth.py" in prompt

    def test_includes_conventions_when_present(self):
        adapter = CodexAdapter(conventions="Use type hints everywhere.")
        task = _make_task()
        prompt = adapter.build_prompt(task)
        assert "Use type hints everywhere." in prompt

    def test_omits_conventions_section_when_empty(self):
        adapter = CodexAdapter(conventions="")
        task = _make_task()
        prompt = adapter.build_prompt(task)
        assert "Conventions:" not in prompt

    def test_includes_context_when_present(self):
        adapter = CodexAdapter()
        task = _make_task(context="Previous agent created the DB schema.")
        prompt = adapter.build_prompt(task)
        assert "Previous agent created the DB schema." in prompt

    def test_omits_context_section_when_empty(self):
        adapter = CodexAdapter()
        task = _make_task(context="")
        prompt = adapter.build_prompt(task)
        assert "Context from completed work" not in prompt


# ---------------------------------------------------------------------------
# TestCodexAdapterPlanningPrompt
# ---------------------------------------------------------------------------


class TestCodexAdapterPlanningPrompt:
    def test_includes_brief(self):
        adapter = CodexAdapter()
        prompt = adapter.build_planning_prompt(
            brief="Build a REST API", phase="scaffold", stack="fastapi"
        )
        assert "Build a REST API" in prompt

    def test_includes_phase(self):
        adapter = CodexAdapter()
        prompt = adapter.build_planning_prompt(brief="anything", phase="scaffold", stack="fastapi")
        assert "scaffold" in prompt

    def test_includes_stack(self):
        adapter = CodexAdapter()
        prompt = adapter.build_planning_prompt(brief="anything", phase="scaffold", stack="fastapi")
        assert "fastapi" in prompt

    def test_includes_json_schema_keys(self):
        adapter = CodexAdapter()
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

    def test_includes_example_json_response(self):
        adapter = CodexAdapter()
        prompt = adapter.build_planning_prompt(brief="anything", phase="scaffold", stack="nextjs")
        # Codex prompts should include a concrete example to guide the model
        assert "task-1" in prompt or "example" in prompt.lower()
