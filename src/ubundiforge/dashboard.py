"""Post-scaffold dashboard — the project report card."""

import json
from pathlib import Path

from rich.console import Console
from rich.text import Text

from ubundiforge.ui import (
    ACCENTS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    command_text,
    grouped_lines,
    muted,
    subtle,
)
from ubundiforge.verify import VerifyReport

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


def render_dashboard(
    *,
    console: Console,
    answers: dict,
    phase_backends: list[tuple[str, str]],
    project_dir: Path,
    verify_report: VerifyReport | None,
    elapsed: float,
) -> None:
    """Render the post-scaffold project report card."""
    name = answers.get("name", "project")
    stack = answers.get("stack", "unknown")
    backends_used = sorted({b for _, b in phase_backends})

    stats = collect_project_stats(project_dir)

    # --- Header row ---
    header = Text()
    header.append("Project Ready", style=f"bold {ACCENTS['violet']}")
    console.print()
    console.print(header)
    console.print()

    # --- Metadata ---
    meta_lines: list[Text] = []
    meta_parts = [
        ("Project", name),
        ("Stack", stack),
        ("Backend", " + ".join(backends_used)),
        ("Time", f"{elapsed:.0f}s"),
    ]
    for label, value in meta_parts:
        line = Text()
        line.append(f"  {label:<10}", style=TEXT_MUTED)
        line.append(value, style=f"bold {TEXT_PRIMARY}")
        meta_lines.append(line)
    console.print(grouped_lines(meta_lines))
    console.print()

    # --- Health checks ---
    if verify_report is not None:
        check_line = Text("  ")
        for check in verify_report.checks:
            if check.skipped:
                check_line.append(f"- {check.name}  ", style=TEXT_MUTED)
            elif check.passed:
                check_line.append("✓ ", style=ACCENTS["aqua"])
                detail = check.detail or check.name
                check_line.append(f"{detail}  ", style=TEXT_SECONDARY)
            else:
                check_line.append("✗ ", style=ACCENTS["plum"])
                check_line.append(f"{check.name}  ", style=TEXT_SECONDARY)
        console.print(muted("  HEALTH CHECKS"))
        console.print(check_line)
    else:
        console.print(muted("  HEALTH CHECKS"))
        console.print(subtle("  skipped (use --verify to enable)"))
    console.print()

    # --- Scaffold summary ---
    console.print(muted("  SCAFFOLD SUMMARY"))
    summary = Text("  ")
    summary.append(str(stats["file_count"]), style=f"bold {ACCENTS['amber']}")
    summary.append(" files  ", style=TEXT_MUTED)
    summary.append(f"{stats['line_count']:,}", style=f"bold {ACCENTS['amber']}")
    summary.append(" lines  ", style=TEXT_MUTED)
    summary.append(str(len(phase_backends)), style=f"bold {ACCENTS['amber']}")
    summary.append(" phases  ", style=TEXT_MUTED)
    if stats["dep_count"]:
        summary.append(str(stats["dep_count"]), style=f"bold {ACCENTS['amber']}")
        summary.append(" deps", style=TEXT_MUTED)
    console.print(summary)
    console.print()

    # --- Next steps ---
    from ubundiforge.stacks import STACK_META

    console.print(muted("  NEXT STEPS"))
    console.print(command_text(f"  cd {project_dir.name}"))
    meta = STACK_META.get(stack)
    if meta and meta.env_hints:
        console.print(subtle("  cp .env.example .env"))
    if meta and meta.dev_commands:
        run_cmd = meta.dev_commands.get("run") or meta.dev_commands.get("dev")
        if run_cmd:
            console.print(command_text(f"  {run_cmd}"))
    console.print()
