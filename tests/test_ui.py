from io import StringIO
from pathlib import Path

from rich.console import Console

from ubundiforge.ui import make_file_tree, make_loader_panel, make_phase_timeline


def test_loader_panel_with_activity_feed():
    """make_loader_panel accepts and renders an activity list."""
    activities = [
        {"summary": "Reviewing the scaffold brief", "completed": True},
        {"summary": "Writing and refining project files", "completed": False},
    ]
    panel = make_loader_panel(
        "Architecture & Core",
        "Writing and refining project files",
        elapsed=42.0,
        spinner_frame="⠹",
        spinner_style="#A16EFA",
        accent="violet",
        activities=activities,
    )
    console = Console(file=StringIO(), width=80)
    console.print(panel)


def test_loader_panel_without_activities():
    """make_loader_panel still works without activities (backward compat)."""
    panel = make_loader_panel(
        "Architecture & Core",
        "Designing the project foundation",
        elapsed=10.0,
        spinner_frame="⠹",
        spinner_style="#A16EFA",
        accent="violet",
    )
    console = Console(file=StringIO(), width=80)
    console.print(panel)


def test_phase_timeline_renders():
    """Phase timeline renders without error."""
    phases = [
        {
            "label": "Architecture & Core",
            "status": "completed",
            "elapsed": 42.0,
            "accent": "violet",
        },
        {"label": "Frontend & UI", "status": "active", "elapsed": 18.0, "accent": "amber"},
        {"label": "Tests & Automation", "status": "pending", "elapsed": 0.0, "accent": "aqua"},
        {"label": "Verify & Fix", "status": "pending", "elapsed": 0.0, "accent": "violet"},
    ]
    renderable = make_phase_timeline(phases)
    console = Console(file=StringIO(), width=80)
    console.print(renderable)


def test_phase_timeline_single_phase():
    """Timeline works with a single phase."""
    phases = [
        {
            "label": "Architecture & Core",
            "status": "active",
            "elapsed": 10.0,
            "accent": "violet",
        },
    ]
    renderable = make_phase_timeline(phases)
    console = Console(file=StringIO(), width=80)
    console.print(renderable)


def test_phase_timeline_all_completed():
    """Timeline works when all phases are done."""
    phases = [
        {
            "label": "Architecture & Core",
            "status": "completed",
            "elapsed": 42.0,
            "accent": "violet",
        },
        {"label": "Tests & Automation", "status": "completed", "elapsed": 30.0, "accent": "aqua"},
    ]
    renderable = make_phase_timeline(phases)
    console = Console(file=StringIO(), width=80)
    console.print(renderable)


def _render_to_string(renderable) -> str:
    """Render a Rich renderable to a plain string."""
    console = Console(file=StringIO(), width=80, color_system=None)
    console.print(renderable)
    return console.file.getvalue()


def test_file_tree_renders_files(tmp_path: Path):
    """File tree renders a directory with files."""
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "routes.py").write_text("x = 1\n")
    (tmp_path / "pyproject.toml").write_text("[project]\n")

    tree = make_file_tree(tmp_path)
    console = Console(file=StringIO(), width=80)
    console.print(tree)


def test_file_tree_ignores_hidden(tmp_path: Path):
    """File tree skips .git and other hidden directories."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x\n")
    (tmp_path / "main.py").write_text("x = 1\n")

    tree = make_file_tree(tmp_path)
    output = _render_to_string(tree)
    assert ".git" not in output
    assert "main.py" in output


def test_file_tree_empty_dir(tmp_path: Path):
    """File tree handles an empty directory."""
    tree = make_file_tree(tmp_path)
    console = Console(file=StringIO(), width=80)
    console.print(tree)
