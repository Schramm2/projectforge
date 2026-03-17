"""Tests for the runner module."""

from forge.runner import _build_cmd


def test_claude_cmd_basic():
    cmd = _build_cmd("claude", "do stuff")
    assert cmd == ["claude", "-p", "--dangerously-skip-permissions", "do stuff"]


def test_claude_cmd_with_model():
    cmd = _build_cmd("claude", "do stuff", model="opus")
    assert cmd == [
        "claude", "-p", "--dangerously-skip-permissions",
        "--model", "opus", "do stuff",
    ]


def test_gemini_cmd_basic():
    cmd = _build_cmd("gemini", "do stuff")
    assert cmd == ["gemini", "-p", "do stuff", "-y"]


def test_gemini_cmd_with_model():
    cmd = _build_cmd("gemini", "do stuff", model="flash")
    assert cmd == ["gemini", "-p", "do stuff", "-y", "--model", "flash"]


def test_codex_cmd_basic():
    cmd = _build_cmd("codex", "do stuff")
    assert cmd == [
        "codex", "exec", "--dangerously-bypass-approvals-and-sandbox", "do stuff",
    ]


def test_codex_cmd_with_model():
    cmd = _build_cmd("codex", "do stuff", model="o3")
    assert cmd == [
        "codex", "exec", "--dangerously-bypass-approvals-and-sandbox",
        "--model", "o3", "do stuff",
    ]


def test_unknown_backend_returns_empty():
    cmd = _build_cmd("unknown", "do stuff")
    assert cmd == []
