"""Tests for typed live, preview, export, and progress prompt records."""

from projectforge.scaffold_execution import PhaseRoutePlan
from projectforge.scaffold_prompts import ScaffoldPromptPlan


def test_prompt_plan_builds_live_and_merged_forms_with_runtime_boundary(monkeypatch) -> None:
    calls: list[tuple[tuple[str, ...], str]] = []

    def fake_build(phases, _all_phases, _answers, _conventions, *, backend, **_kwargs):
        calls.append((tuple(phases), backend))
        return f"prompt:{'+'.join(phases)}:{backend}"

    monkeypatch.setattr("projectforge.scaffold_prompts.build_phase_prompt", fake_build)
    route_plan = PhaseRoutePlan.from_pairs(
        [
            ("architecture", "claude"),
            ("tests", "codex"),
            ("verify", "claude"),
        ]
    )

    plan = ScaffoldPromptPlan.build(
        route_plan=route_plan,
        merged_groups=[(["architecture"], "claude"), (["tests"], "codex"), (["verify"], "claude")],
        all_phases=["architecture", "tests", "verify"],
        answers={},
        conventions="conventions",
        claude_md_template=None,
    )

    assert calls == [
        (("architecture",), "claude"),
        (("tests",), "codex"),
        (("verify",), "claude"),
        (("architecture",), "claude"),
        (("tests",), "codex"),
        (("verify",), "claude"),
    ]
    assert all("<forge_runtime_boundary>" in prompt.content for prompt in plan.live)
    assert plan.progress_records[1][:2] == ("tests", "codex")
    assert plan.total_live_characters == sum(len(prompt.content) for prompt in plan.live)


def test_prompt_plan_exports_single_preview_without_heading(monkeypatch) -> None:
    monkeypatch.setattr(
        "projectforge.scaffold_prompts.build_phase_prompt",
        lambda *_args, **_kwargs: "one prompt",
    )
    route_plan = PhaseRoutePlan.from_pairs([("architecture", "claude")])

    plan = ScaffoldPromptPlan.build(
        route_plan=route_plan,
        merged_groups=[(["architecture"], "claude")],
        all_phases=["architecture"],
        answers={},
        conventions="",
        claude_md_template=None,
    )

    assert plan.export_text() == plan.previews[0].content
    assert not plan.export_text().startswith("===")


def test_prompt_plan_exports_multiple_previews_with_phase_and_backend_headings(monkeypatch) -> None:
    monkeypatch.setattr(
        "projectforge.scaffold_prompts.build_phase_prompt",
        lambda phases, *_args, backend, **_kwargs: f"prompt for {phases[0]} via {backend}",
    )
    route_plan = PhaseRoutePlan.from_pairs([("architecture", "claude"), ("tests", "codex")])

    plan = ScaffoldPromptPlan.build(
        route_plan=route_plan,
        merged_groups=[(["architecture"], "claude"), (["tests"], "codex")],
        all_phases=["architecture", "tests"],
        answers={},
        conventions="",
        claude_md_template=None,
    )

    exported = plan.export_text()
    assert "=== Architecture & Core (claude) ===" in exported
    assert "=== Tests & Automation (codex) ===" in exported
    assert "prompt for architecture via claude" in exported
