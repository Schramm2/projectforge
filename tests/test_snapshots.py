"""Snapshot tests for assembled prompts."""

import os
from pathlib import Path

from ubundiforge.prompt_builder import build_phase_prompt, build_prompt

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _assert_snapshot(name: str, content: str) -> None:
    snapshot_path = SNAPSHOT_DIR / name
    normalized = content.rstrip() + "\n"

    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(normalized)

    assert snapshot_path.exists(), f"Missing snapshot: {snapshot_path}"
    assert snapshot_path.read_text() == normalized


def test_nextjs_full_prompt_snapshot():
    prompt = build_prompt(
        {
            "name": "studio",
            "stack": "nextjs",
            "description": "A branded client portal",
            "docker": False,
            "auth_provider": "clerk",
            "services": ["Segment (analytics)"],
            "ci": {
                "include": True,
                "mode": "questionnaire",
                "actions": ["lint", "typecheck", "unit-tests"],
            },
            "extra": "Use Tailwind v4",
            "demo_mode": True,
        },
        conventions="Use strict typing.",
        claude_md_template=None,
    )

    _assert_snapshot("nextjs_full_prompt.md", prompt)


def test_fastapi_tests_phase_prompt_snapshot():
    prompt = build_phase_prompt(
        ["tests"],
        ["architecture", "tests", "verify"],
        {
            "name": "atlas-api",
            "stack": "fastapi",
            "description": "A health and metrics API",
            "docker": True,
            "auth_provider": None,
            "services": [],
            "ci": {
                "include": True,
                "mode": "questionnaire",
                "actions": ["lint", "typecheck", "unit-tests"],
            },
            "extra": "Prefer focused unit tests first.",
            "demo_mode": True,
        },
        conventions="Prefer explicit typing.",
        backend="codex",
        claude_md_template=None,
    )

    _assert_snapshot("fastapi_tests_phase_prompt_codex.md", prompt)
