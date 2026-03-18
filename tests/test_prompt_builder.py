"""Tests for scaffold prompt assembly."""

from ubundiforge.prompt_builder import (
    build_architecture_prompt,
    build_frontend_prompt,
    build_phase_prompt,
    build_prompt,
    build_tests_prompt,
)


def test_build_prompt_includes_requested_auth_ci_and_agent_docs():
    prompt = build_prompt(
        {
            "name": "atlas",
            "stack": "nextjs",
            "description": "A customer dashboard",
            "docker": False,
            "auth_provider": "clerk",
            "services": ["Segment (analytics)"],
            "ci": {
                "include": True,
                "mode": "questionnaire",
                "actions": ["lint", "typecheck", "unit-tests"],
            },
            "extra": "",
        },
        conventions="Use strict typing.",
        claude_md_template=None,
    )

    assert "Authentication to scaffold:" in prompt
    assert "Clerk" in prompt
    assert "CI GUIDANCE:" in prompt
    assert "Lint: Run the repo lint command and fail on violations." in prompt
    assert "agent_docs/" in prompt
    assert "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=" in prompt


def test_build_prompt_blank_ci_template_uses_placeholder_language():
    prompt = build_prompt(
        {
            "name": "pulse",
            "stack": "fastapi",
            "description": "A status API",
            "docker": True,
            "auth_provider": None,
            "services": [],
            "ci": {
                "include": True,
                "mode": "blank-template",
                "actions": [],
            },
            "extra": "",
        },
        conventions="Prefer uv.",
        claude_md_template=None,
    )

    assert ".github/workflows/ci.yml" in prompt
    assert "blank starter template" in prompt


# --- Phase-specific prompt tests ---

_BASE_ANSWERS = {
    "name": "myapp",
    "stack": "nextjs",
    "description": "A web app",
    "docker": False,
    "auth_provider": None,
    "services": [],
    "ci": {"include": True, "mode": "questionnaire", "actions": ["lint", "unit-tests"]},
    "extra": "Use Tailwind v4",
}


def test_architecture_prompt_excludes_frontend_and_tests():
    prompt = build_architecture_prompt(
        _BASE_ANSWERS,
        "conventions",
        exclude_frontend=True,
        exclude_tests=True,
    )
    assert "Do NOT create frontend UI components" in prompt
    assert "Do NOT create test files" in prompt
    assert "CI GUIDANCE:" not in prompt  # CI excluded when tests are separate


def test_architecture_prompt_includes_tests_when_not_excluded():
    prompt = build_architecture_prompt(
        _BASE_ANSWERS,
        "conventions",
        exclude_frontend=True,
        exclude_tests=False,
    )
    assert "Do NOT create frontend UI components" in prompt
    assert "Do NOT create test files" not in prompt
    assert "CI GUIDANCE:" in prompt


def test_frontend_prompt_focuses_on_ui():
    prompt = build_frontend_prompt(_BASE_ANSWERS)
    assert "frontend UI" in prompt
    assert "Do NOT modify backend code" in prompt
    assert "Use Tailwind v4" in prompt


def test_tests_prompt_focuses_on_testing():
    prompt = build_tests_prompt(_BASE_ANSWERS)
    assert "comprehensive tests" in prompt
    assert "Do NOT modify application code" in prompt
    assert "CI GUIDANCE:" in prompt
    assert "Use Tailwind v4" in prompt


def test_phase_prompt_all_phases_returns_full_prompt():
    all_phases = ["architecture", "frontend", "tests"]
    phase_prompt = build_phase_prompt(
        all_phases,
        all_phases,
        _BASE_ANSWERS,
        "conventions",
    )
    full_prompt = build_prompt(_BASE_ANSWERS, "conventions")
    assert phase_prompt == full_prompt


def test_phase_prompt_architecture_only():
    all_phases = ["architecture", "frontend", "tests"]
    prompt = build_phase_prompt(
        ["architecture"],
        all_phases,
        _BASE_ANSWERS,
        "conventions",
    )
    assert "Do NOT create frontend UI components" in prompt
    assert "Do NOT create test files" in prompt


def test_phase_prompt_frontend_only():
    all_phases = ["architecture", "frontend", "tests"]
    prompt = build_phase_prompt(
        ["frontend"],
        all_phases,
        _BASE_ANSWERS,
        "conventions",
    )
    assert "frontend UI" in prompt
    assert "Do NOT modify backend code" in prompt


def test_phase_prompt_tests_only():
    all_phases = ["architecture", "frontend", "tests"]
    prompt = build_phase_prompt(
        ["tests"],
        all_phases,
        _BASE_ANSWERS,
        "conventions",
    )
    assert "comprehensive tests" in prompt
    assert "Do NOT modify application code" in prompt
