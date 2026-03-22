"""Tests for the forge evolve capability registry."""

import json
from pathlib import Path

from ubundiforge.evolutions import build_evolve_prompt, get_capabilities, get_capability


def test_capabilities_exist_for_fastapi():
    caps = get_capabilities("fastapi")
    assert len(caps) > 0
    assert any(c["name"] == "auth" for c in caps)


def test_capabilities_exist_for_nextjs():
    caps = get_capabilities("nextjs")
    assert len(caps) > 0


def test_capabilities_empty_for_unknown_stack():
    caps = get_capabilities("unknown-stack")
    assert caps == []


def test_get_capability_by_name():
    cap = get_capability("fastapi", "auth")
    assert cap is not None
    assert cap["name"] == "auth"
    assert "prompt_fragment" in cap
    assert "typically_touches" in cap


def test_get_capability_returns_none_for_missing():
    cap = get_capability("fastapi", "nonexistent")
    assert cap is None


def test_both_stack_has_fastapi_and_nextjs_caps():
    caps = get_capabilities("both")
    names = [c["name"] for c in caps]
    assert "auth" in names  # from fastapi
    assert "i18n" in names  # from nextjs


def test_build_evolve_prompt_basic(tmp_path: Path):
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir()
    (forge_dir / "scaffold.json").write_text(
        json.dumps(
            {
                "stack": "fastapi",
                "name": "test-project",
                "description": "a test",
                "backends": ["claude"],
            }
        )
    )
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")

    capability = {
        "name": "auth",
        "description": "Add auth",
        "prompt_fragment": "Add Clerk authentication.",
        "typically_touches": ["api/app.py"],
    }

    prompt = build_evolve_prompt(tmp_path, capability)
    assert "Add Clerk authentication" in prompt
    assert "fastapi" in prompt.lower()
    assert "api/app.py" in prompt


def test_build_evolve_prompt_caps_content(tmp_path: Path):
    """Prompt content is capped to stay within token limits."""
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir()
    (forge_dir / "scaffold.json").write_text(
        json.dumps(
            {
                "stack": "fastapi",
                "name": "big-project",
            }
        )
    )
    (tmp_path / "huge.py").write_text("x = 1\n" * 5000)

    capability = {
        "name": "test",
        "prompt_fragment": "Do something.",
        "typically_touches": ["huge.py"],
    }

    prompt = build_evolve_prompt(tmp_path, capability)
    assert len(prompt) < 40000


def test_build_evolve_prompt_no_manifest(tmp_path: Path):
    """Works even without .forge/scaffold.json."""
    capability = {
        "name": "test",
        "prompt_fragment": "Do something.",
        "typically_touches": [],
    }
    prompt = build_evolve_prompt(tmp_path, capability)
    assert "Do something" in prompt
