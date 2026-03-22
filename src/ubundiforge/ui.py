"""Shared Rich UI primitives for UbundiForge terminal surfaces."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from rich import box
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

TEXT_PRIMARY = "#F7F9FF"
TEXT_SECONDARY = "#C6CEE6"
TEXT_MUTED = "#8893B3"
SURFACE = "#12172B"

ACCENTS = {
    "plum": "#D768D2",
    "aqua": "#75DCE6",
    "violet": "#A16EFA",
    "amber": "#F3BB58",
    "indigo": "#2D365C",
}

BACKEND_ACCENTS: dict[str, str] = {
    "claude": "violet",
    "gemini": "amber",
    "codex": "aqua",
}

_BADGE_STYLES = {
    "success": (TEXT_PRIMARY, ACCENTS["aqua"]),
    "warning": ("#10131E", ACCENTS["amber"]),
    "error": (TEXT_PRIMARY, ACCENTS["plum"]),
    "info": (TEXT_PRIMARY, ACCENTS["violet"]),
}


_console: Console | None = None


def create_console() -> Console:
    """Return the shared console singleton used across CLI surfaces."""
    global _console
    if _console is None:
        _console = Console(highlight=False)
    return _console


def subtle(text: str) -> Text:
    """Return secondary helper text."""
    return Text(text, style=TEXT_SECONDARY)


def muted(text: str) -> Text:
    """Return muted supporting text."""
    return Text(text, style=TEXT_MUTED)


def highlight(text: str, accent: str = "aqua", *, bold: bool = True) -> Text:
    """Return accent-colored text."""
    weight = "bold " if bold else ""
    return Text(text, style=f"{weight}{ACCENTS[accent]}")


def badge(label: str, tone: str = "info") -> Text:
    """Return a compact status badge. Use sparingly — only for attention-worthy states."""
    if tone == "muted":
        return Text(label, style=TEXT_MUTED)
    foreground, background = _BADGE_STYLES[tone]
    return Text(f" {label} ", style=f"bold {foreground} on {background}")


def command_text(command: str) -> Text:
    """Return styled command text."""
    return Text(command, style=f"bold {ACCENTS['aqua']}")


def path_text(value: str | Path) -> Text:
    """Return styled path text."""
    return Text(str(value), style=f"bold {ACCENTS['plum']}")


def status_line(text: str, accent: str = "aqua") -> Text:
    """Return a single accented status line — use instead of panels for one-liners."""
    line = Text()
    line.append("  ", style="")
    line.append(text, style=ACCENTS[accent])
    return line


def bullet(text: str, accent: str = "aqua") -> Text:
    """Return a simple accented bullet line."""
    line = Text()
    line.append("> ", style=f"bold {ACCENTS[accent]}")
    line.append(text, style=TEXT_SECONDARY)
    return line


def grouped_lines(lines: Iterable[str | Text]) -> Group:
    """Render a sequence of text lines as a Rich group."""
    renderables: list[Text] = []
    for line in lines:
        if isinstance(line, Text):
            renderables.append(line)
        else:
            renderables.append(Text(line, style=TEXT_SECONDARY))
    return Group(*renderables)


def make_panel(
    body: RenderableType,
    *,
    title: str | Text | None = None,
    accent: str = "violet",
    subtitle: str | Text | None = None,
    padding: tuple[int, int] = (0, 1),
) -> Panel:
    """Create a bordered panel using the Ubundi palette."""
    panel_title = title
    if isinstance(title, str):
        panel_title = Text(title, style=f"bold {ACCENTS[accent]}")
    panel_subtitle = subtitle
    if isinstance(subtitle, str):
        panel_subtitle = Text(subtitle, style=TEXT_MUTED)
    return Panel(
        body,
        title=panel_title,
        subtitle=panel_subtitle,
        border_style=ACCENTS[accent],
        box=box.ROUNDED,
        padding=padding,
    )


def make_table(
    *,
    title: str | None = None,
    accent: str = "violet",
    show_header: bool = True,
    show_edge: bool = True,
    pad_edge: bool = True,
    box_style: box.Box | None = box.ROUNDED,
) -> Table:
    """Create a table styled to match the Ubundi terminal theme."""
    table = Table(
        title=Text(title, style=f"bold {ACCENTS[accent]}") if title else None,
        show_header=show_header,
        header_style=f"bold {TEXT_PRIMARY}",
        border_style=ACCENTS[accent],
        show_edge=show_edge,
        pad_edge=pad_edge,
        box=box_style,
    )
    return table


def make_step_panel(
    step: int,
    total: int,
    title: str,
    *,
    detail: str | None = None,
    accent: str = "aqua",
) -> Panel:
    """Create a compact step indicator panel."""
    header = Text.assemble(
        ("Step ", f"bold {TEXT_SECONDARY}"),
        (f"{step}/{total}", f"bold {ACCENTS['amber']}"),
    )
    lines: list[Text] = [header, Text(title, style=f"bold {TEXT_PRIMARY}")]
    if detail:
        lines.append(Text(detail, style=TEXT_MUTED))
    return make_panel(grouped_lines(lines), accent=accent, padding=(0, 1))


def make_loader_panel(
    title: str,
    summary: str,
    *,
    elapsed: float,
    spinner_frame: str,
    spinner_style: str,
    accent: str = "violet",
    detail: str | None = None,
    activities: list[dict] | None = None,
) -> Panel:
    """Create a polished live loader panel for long-running CLI work."""
    header = Text()
    header.append(f"{spinner_frame} ", style=f"bold {spinner_style}")
    header.append(title, style=f"bold {TEXT_PRIMARY}")
    header.append("  ", style="")
    header.append(f"{elapsed:.0f}s", style=TEXT_MUTED)

    lines: list[Text] = [header]

    if activities:
        for step in activities:
            line = Text("  ")
            if step["completed"]:
                line.append("✓ ", style=ACCENTS["aqua"])
                line.append(step["summary"], style=TEXT_MUTED)
            else:
                line.append(f"{spinner_frame} ", style=f"bold {spinner_style}")
                line.append(step["summary"], style=f"bold {TEXT_SECONDARY}")
            lines.append(line)
    else:
        lines.append(Text(summary, style=f"bold {TEXT_SECONDARY}"))
        if detail:
            lines.append(Text(detail, style=TEXT_MUTED))

    return make_panel(
        grouped_lines(lines),
        title="In Progress",
        accent=accent,
        padding=(0, 1),
    )


def make_phase_timeline(phases: list[dict]) -> Group:
    """Create a horizontal phase progress indicator.

    Each phase dict has: label, status (completed/active/pending), elapsed, accent.
    """
    # Phase labels row
    label_line = Text("  ")
    for phase in phases:
        if phase["status"] == "completed":
            label_line.append("● ", style=ACCENTS["aqua"])
            label_line.append(phase["label"], style=TEXT_MUTED)
            label_line.append(f" {phase['elapsed']:.0f}s", style=TEXT_MUTED)
        elif phase["status"] == "active":
            label_line.append("◉ ", style=ACCENTS[phase["accent"]])
            label_line.append(phase["label"], style=f"bold {TEXT_PRIMARY}")
            label_line.append(f" {phase['elapsed']:.0f}s", style=TEXT_MUTED)
        else:
            label_line.append("○ ", style=TEXT_MUTED)
            label_line.append(phase["label"], style=TEXT_MUTED)
        label_line.append("   ", style="")

    # Progress bar
    total = len(phases)
    completed = sum(1 for p in phases if p["status"] == "completed")
    active = sum(1 for p in phases if p["status"] == "active")
    bar_width = min(60, total * 15)

    completed_width = int(bar_width * completed / total)
    active_width = int(bar_width * active / total) if active else 0
    remaining_width = bar_width - completed_width - active_width

    bar = Text("  ")
    if completed_width:
        bar.append("━" * completed_width, style=ACCENTS["aqua"])
    if active_width:
        active_accent = next((p["accent"] for p in phases if p["status"] == "active"), "violet")
        bar.append("━" * active_width, style=ACCENTS[active_accent])
    if remaining_width:
        bar.append("━" * remaining_width, style=ACCENTS["indigo"])

    return Group(label_line, bar)


def header_panel(version: str | None = None) -> Panel:
    """Create the branded header panel for the CLI."""
    lines = grouped_lines(
        [
            Text("UbundiForge", style=f"bold {TEXT_PRIMARY}"),
            Text("Ubundi project scaffolder", style=TEXT_SECONDARY),
        ]
    )
    subtitle = f"v{version}" if version else None
    return make_panel(lines, title="Forge", subtitle=subtitle, accent="violet")


_HIDDEN_TREE_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".forge", ".ruff_cache"}
_CONFIG_FILES = {
    "pyproject.toml",
    "package.json",
    "Dockerfile",
    "docker-compose.yml",
    "tsconfig.json",
    ".env.example",
    "CLAUDE.md",
    ".pre-commit-config.yaml",
    ".gitignore",
    "next.config.ts",
    "tailwind.config.ts",
    "vitest.config.ts",
}


def make_file_tree(project_dir: Path) -> Group:
    """Render a color-coded file tree of a scaffolded project."""
    tree = Tree(
        Text(f"{project_dir.name}/", style=f"bold {ACCENTS['aqua']}"),
        guide_style=TEXT_MUTED,
    )

    file_count = 0
    line_count = 0

    def _add_dir(parent_tree: Tree, directory: Path) -> None:
        nonlocal file_count, line_count
        entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name))
        for entry in entries:
            name = entry.name
            if name in _HIDDEN_TREE_DIRS or name.startswith("."):
                if name not in _CONFIG_FILES:
                    continue
            if entry.is_dir():
                branch = parent_tree.add(Text(f"{name}/", style=ACCENTS["violet"]))
                _add_dir(branch, entry)
            else:
                file_count += 1
                try:
                    line_count += len(entry.read_text(errors="replace").splitlines())
                except OSError:
                    pass
                if name in _CONFIG_FILES:
                    parent_tree.add(Text(name, style=ACCENTS["plum"]))
                else:
                    parent_tree.add(Text(name, style=ACCENTS["aqua"]))

    _add_dir(tree, project_dir)

    summary = Text("  ")
    summary.append(str(file_count), style=f"bold {ACCENTS['amber']}")
    summary.append(" files", style=TEXT_MUTED)
    summary.append(" · ", style=TEXT_MUTED)
    summary.append(f"{line_count:,}", style=f"bold {ACCENTS['amber']}")
    summary.append(" lines", style=TEXT_MUTED)

    return Group(tree, summary)
