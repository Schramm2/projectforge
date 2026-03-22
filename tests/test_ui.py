from io import StringIO

from rich.console import Console

from ubundiforge.ui import make_loader_panel


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
