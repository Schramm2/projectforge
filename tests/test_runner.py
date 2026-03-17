"""Tests for the runner module."""

from pathlib import Path

from ubundiforge.runner import _build_cmd, reset_project_dir


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


def test_reset_project_dir_clears_existing_contents(tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("stale")
    nested_dir = project_dir / "src"
    nested_dir.mkdir()
    (nested_dir / "main.py").write_text("print('stale')")

    reset_project_dir(project_dir)

    assert project_dir.exists()
    assert list(project_dir.iterdir()) == []


def test_reset_project_dir_creates_missing_directory(tmp_path):
    project_dir = tmp_path / "new-project"

    reset_project_dir(project_dir)

    assert project_dir.exists()
    assert isinstance(project_dir, Path)
