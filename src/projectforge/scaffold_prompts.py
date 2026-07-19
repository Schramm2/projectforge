"""Build typed live, preview, export, and progress prompt records for one scaffold."""

from __future__ import annotations

from dataclasses import dataclass

from projectforge.prompt_builder import build_phase_prompt
from projectforge.router import PHASE_LABELS
from projectforge.scaffold_execution import PhasePromptTriple, PhaseRoutePlan

_FORGE_RUNTIME_BOUNDARY = """

<forge_runtime_boundary>
Do not read, edit, delete, or replace `.forge/progress.json`; ProjectForge owns that runtime
evidence file. Preserve existing project output from earlier phases.
</forge_runtime_boundary>"""


@dataclass(frozen=True)
class LivePhasePrompt:
    """The prompt executed for one routed provider phase."""

    phase: str
    backend: str
    content: str

    def as_progress_record(self) -> PhasePromptTriple:
        return self.phase, self.backend, self.content


@dataclass(frozen=True)
class MergedPromptPreview:
    """A prompt-only view that combines adjacent phases owned by one backend."""

    phases: tuple[str, ...]
    backend: str
    content: str

    @property
    def label(self) -> str:
        return " + ".join(PHASE_LABELS.get(phase, phase) for phase in self.phases)


@dataclass(frozen=True)
class ScaffoldPromptPlan:
    """All provider prompt forms derived from one normalized scaffold request."""

    live: tuple[LivePhasePrompt, ...]
    previews: tuple[MergedPromptPreview, ...]

    @classmethod
    def build(
        cls,
        *,
        route_plan: PhaseRoutePlan,
        merged_groups: list[tuple[list[str], str]],
        all_phases: list[str],
        answers: dict,
        conventions: str,
        claude_md_template: str | None,
    ) -> ScaffoldPromptPlan:
        live = tuple(
            LivePhasePrompt(
                phase=route.phase,
                backend=route.backend,
                content=_build_bounded_prompt(
                    [route.phase],
                    all_phases,
                    answers,
                    conventions,
                    backend=route.backend,
                    claude_md_template=claude_md_template,
                ),
            )
            for route in route_plan.ordered
        )
        previews = tuple(
            MergedPromptPreview(
                phases=tuple(phases),
                backend=backend,
                content=_build_bounded_prompt(
                    phases,
                    all_phases,
                    answers,
                    conventions,
                    backend=backend,
                    claude_md_template=claude_md_template,
                ),
            )
            for phases, backend in merged_groups
        )
        return cls(live=live, previews=previews)

    @property
    def progress_records(self) -> list[PhasePromptTriple]:
        return [prompt.as_progress_record() for prompt in self.live]

    @property
    def total_live_characters(self) -> int:
        return sum(len(prompt.content) for prompt in self.live)

    def export_text(self) -> str:
        if len(self.previews) == 1:
            return self.previews[0].content
        return "\n\n".join(
            f"=== {preview.label} ({preview.backend}) ===\n\n{preview.content}"
            for preview in self.previews
        )


def _build_bounded_prompt(
    phases: list[str],
    all_phases: list[str],
    answers: dict,
    conventions: str,
    *,
    backend: str,
    claude_md_template: str | None,
) -> str:
    return (
        build_phase_prompt(
            phases,
            all_phases,
            answers,
            conventions,
            backend=backend,
            claude_md_template=claude_md_template,
        )
        + _FORGE_RUNTIME_BOUNDARY
    )
