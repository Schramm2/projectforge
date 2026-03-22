from io import StringIO

from rich.console import Console

from ubundiforge.ui import make_loader_panel, make_phase_timeline


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
