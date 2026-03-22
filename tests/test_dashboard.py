"""Tests for the post-scaffold dashboard."""

from pathlib import Path

from ubundiforge.dashboard import collect_project_stats


def test_collect_stats_empty_dir(tmp_path: Path):
    stats = collect_project_stats(tmp_path)
    assert stats["file_count"] == 0
    assert stats["line_count"] == 0
    assert stats["dep_count"] == 0


def test_collect_stats_with_files(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\nprint('world')\n")
    (tmp_path / "lib.py").write_text("x = 1\n")
    stats = collect_project_stats(tmp_path)
    assert stats["file_count"] == 2
    assert stats["line_count"] == 3


def test_collect_stats_ignores_hidden_dirs(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("stuff\n")
    (tmp_path / "main.py").write_text("x = 1\n")
    stats = collect_project_stats(tmp_path)
    assert stats["file_count"] == 1


def test_collect_stats_counts_python_deps(tmp_path: Path):
    toml = '[project]\nname = "test"\ndependencies = ["fastapi", "pydantic", "httpx"]\n'
    (tmp_path / "pyproject.toml").write_text(toml)
    stats = collect_project_stats(tmp_path)
    assert stats["dep_count"] == 3


def test_collect_stats_counts_node_deps(tmp_path: Path):
    pkg = '{"dependencies": {"react": "^18", "next": "^14"}, "devDependencies": {"vitest": "^1"}}'
    (tmp_path / "package.json").write_text(pkg)
    stats = collect_project_stats(tmp_path)
    assert stats["dep_count"] == 3
