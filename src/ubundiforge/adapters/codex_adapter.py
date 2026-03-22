"""Codex CLI backend adapter."""

from __future__ import annotations

from ubundiforge.adapters.base import CLIAdapterBase
from ubundiforge.adapters.json_parsing import parse_decomposition_plan
from ubundiforge.protocol import AgentTask, DecompositionPlan

_PLANNING_PROMPT_TEMPLATE = """\
Scaffold planning agent. Decompose a project phase into subagent tasks.

Brief: {brief}
Phase: {phase}
Stack: {stack}

Output ONLY a JSON object. No markdown fences. No explanation.

Example output:
{{
  "tasks": [
    {{
      "id": "task-1",
      "description": "Create models",
      "file_territory": ["src/models.py"],
      "dependencies": []
    }},
    {{
      "id": "task-2",
      "description": "Create routes",
      "file_territory": ["src/routes.py"],
      "dependencies": ["task-1"]
    }}
  ],
  "execution_order": [["task-1"], ["task-2"]],
  "rationale": "Models must exist before routes reference them"
}}

Now decompose 2-6 tasks for the brief above. Assign non-overlapping file \
territories. Use the same JSON structure as the example."""


class CodexAdapter(CLIAdapterBase):
    """Backend adapter for Codex CLI (`codex` CLI)."""

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]:
        cmd = ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox"]
        if model:
            cmd += ["--model", model]
        cmd.append(prompt)
        return cmd

    def build_prompt(self, task: AgentTask) -> str:
        territory = ", ".join(task.file_territory)
        parts = [
            f"Task: {task.description}",
            f"Files: {territory}",
        ]

        if task.context:
            parts += [f"Context: {task.context}"]

        parts += [
            "Rules: Only modify your files. Follow conventions. Don't overwrite previous work.",
        ]

        if self.conventions:
            parts += [f"Conventions: {self.conventions}"]

        return "\n".join(parts)

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str:
        return _PLANNING_PROMPT_TEMPLATE.format(brief=brief, phase=phase, stack=stack)

    def parse_plan(self, raw_output: str, phase: str, backend: str) -> DecompositionPlan | None:
        return parse_decomposition_plan(raw_output, phase=phase, backend=backend)
