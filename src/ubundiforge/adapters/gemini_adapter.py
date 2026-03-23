"""Gemini CLI backend adapter."""

from __future__ import annotations

from ubundiforge.adapters.base import CLIAdapterBase
from ubundiforge.adapters.json_parsing import parse_decomposition_plan
from ubundiforge.protocol import AgentTask, DecompositionPlan

_PLANNING_PROMPT_TEMPLATE = """\
You are a scaffold planning agent. Given this project brief and phase, \
decompose the work into focused subagent tasks.

Brief: {brief}
Phase: {phase}
Stack: {stack}

Decompose this phase into 2-6 focused tasks. Each task should own a \
distinct set of files. Assign non-overlapping file territories to tasks \
that can run in parallel.

You MUST respond with ONLY a valid JSON object. No text before or after. \
No markdown fences. No explanation. The response must start with {{ and end \
with }}.

Return a JSON object with this exact structure:
{{
  "tasks": [
    {{"id": "task-1", "description": "...", "file_territory": ["..."], "dependencies": []}}
  ],
  "execution_order": [["task-1"], ["task-2", "task-3"]],
  "rationale": "why this decomposition"
}}"""


class GeminiAdapter(CLIAdapterBase):
    """Backend adapter for Gemini CLI (`gemini` CLI)."""

    def build_cmd(self, prompt: str, model: str | None = None) -> list[str]:
        cmd = ["gemini", "-p", prompt, "-y"]
        if model:
            cmd += ["--model", model]
        return cmd

    def build_prompt(self, task: AgentTask) -> str:
        territory = "\n".join(f"- {f}" for f in task.file_territory)
        parts = [
            "You are a specialist subagent working on a scaffold project.",
            "",
            f"Your assignment: {task.description}",
            f"Files you own:\n{territory}",
        ]

        if task.context:
            parts += [
                "",
                f"Context from completed work: {task.context}",
            ]

        if self.phase_brief:
            parts += [
                "",
                "Full phase brief (for reference — focus on your assignment above):",
                self.phase_brief,
            ]

        parts += [
            "",
            "Rules:",
            "- Only create/modify files in your territory unless absolutely necessary",
            "- Follow the conventions provided",
            "- Build on what previous agents created — do not overwrite their files",
        ]

        if self.conventions:
            parts += [
                "",
                f"Conventions: {self.conventions}",
            ]

        return "\n".join(parts)

    def build_planning_prompt(self, brief: str, phase: str, stack: str) -> str:
        return _PLANNING_PROMPT_TEMPLATE.format(brief=brief, phase=phase, stack=stack)

    def parse_plan(self, raw_output: str, phase: str, backend: str) -> DecompositionPlan | None:
        return parse_decomposition_plan(raw_output, phase=phase, backend=backend)
