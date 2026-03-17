"""Tests for scaffold prompt assembly."""

from ubundiforge.prompt_builder import build_prompt


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
