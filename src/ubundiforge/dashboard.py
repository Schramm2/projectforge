"""Post-scaffold dashboard — the project report card."""

import json
from pathlib import Path

_HIDDEN_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".forge", ".ruff_cache"}
_BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot"}


def collect_project_stats(project_dir: Path) -> dict:
    """Collect file count, line count, and dependency count from a scaffolded project."""
    file_count = 0
    line_count = 0

    for path in project_dir.rglob("*"):
        parts = path.relative_to(project_dir).parts
        if any(part.startswith(".") or part in _HIDDEN_DIRS for part in parts):
            continue
        if path.is_file() and path.suffix not in _BINARY_SUFFIXES:
            file_count += 1
            try:
                line_count += len(path.read_text(errors="replace").splitlines())
            except OSError:
                pass

    dep_count = _count_python_deps(project_dir) + _count_node_deps(project_dir)

    return {
        "file_count": file_count,
        "line_count": line_count,
        "dep_count": dep_count,
    }


def _count_python_deps(project_dir: Path) -> int:
    """Count dependencies from pyproject.toml if present."""
    toml_path = project_dir / "pyproject.toml"
    if not toml_path.exists():
        return 0
    try:
        import tomllib

        data = tomllib.loads(toml_path.read_text())
        return len(data.get("project", {}).get("dependencies", []))
    except Exception:
        return 0


def _count_node_deps(project_dir: Path) -> int:
    """Count dependencies from package.json if present."""
    pkg_path = project_dir / "package.json"
    if not pkg_path.exists():
        return 0
    try:
        data = json.loads(pkg_path.read_text())
        deps = len(data.get("dependencies", {}))
        dev_deps = len(data.get("devDependencies", {}))
        return deps + dev_deps
    except Exception:
        return 0
