"""Shared Rich UI primitives for UbundiForge terminal surfaces."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from rich import box
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

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
