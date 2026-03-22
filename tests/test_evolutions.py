"""Tests for the forge evolve capability registry."""

from ubundiforge.evolutions import get_capabilities, get_capability


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
