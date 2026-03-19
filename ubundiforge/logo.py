"""Ubundi ASCII logo display."""

from math import ceil
from pathlib import Path

from rich.console import Console
from rich.text import Text

from ubundiforge.ui import ACCENTS

DEFAULT_MAX_WIDTH = 44
DEFAULT_MAX_HEIGHT = 20
MIN_RENDER_WIDTH = 18
CHAR_DENSITY = {
    " ": 0,
    ".": 0,
    ":": 1,
    "-": 2,
    "=": 3,
    "+": 4,
    "*": 5,
    "#": 6,
    "%": 7,
}
LOGO_PATHS = (Path(__file__).resolve().parent.parent / "assets" / "ascii-art.txt",)
FALLBACK_LOGO = """\
 #%%%%%%%         %%%%%%%%
+%%%  -%%+        %%%  =%%%
%%%   %%%-        %%%   #%%
%%% #%%%*          %%%% %%%
:%%%%%%             *%%%%%%
 %%%%                 #%%%
#%%%%%-              %%%%%%
%%% %%%%%%=     -%%%%%%=%%%
 %%%#  %%%%%%%%%%%%%= -%%%#
  %%%%%%*         =%%%%%%
     *%%%%%%%%%%%%%%%%"""


def _load_logo_art() -> str | None:
    """Load the source ASCII art if it exists in the local project."""
    for path in LOGO_PATHS:
        if path.exists():
            return path.read_text()
    return None


def _normalize_lines(art: str) -> list[str]:
    """Trim blank space around the art while preserving its inner layout."""
    lines = art.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _compact_logo(art: str, *, max_width: int, max_height: int) -> str:
    """Downsample large ASCII art into a compact terminal-friendly logo."""
    lines = _normalize_lines(art)
    if not lines:
        return ""

    width = max(len(line) for line in lines)
    padded_lines = [line.ljust(width) for line in lines]
    x_step = max(1, ceil(width / max_width))
    y_step = max(1, ceil(len(padded_lines) / max_height))

    compacted: list[str] = []
    for y in range(0, len(padded_lines), y_step):
        row: list[str] = []
        for x in range(0, width, x_step):
            best_char = " "
            best_density = 0
            for source_row in padded_lines[y : y + y_step]:
                for char in source_row[x : x + x_step]:
                    density = CHAR_DENSITY.get(char, 1)
                    if density > best_density:
                        best_char = char
                        best_density = density
            row.append(best_char)
        compacted.append("".join(row).rstrip())

    compacted = [line for line in compacted if line.strip()]
    if not compacted:
        return ""

    left_padding = min(len(line) - len(line.lstrip()) for line in compacted)
    return "\n".join(line[left_padding:] for line in compacted)


def render_logo(terminal_width: int | None = None) -> str:
    """Return a compact logo string derived from the source asset when available."""
    max_width = DEFAULT_MAX_WIDTH
    if terminal_width is not None:
        max_width = max(MIN_RENDER_WIDTH, min(DEFAULT_MAX_WIDTH, terminal_width - 4))

    art = _load_logo_art()
    if not art:
        return FALLBACK_LOGO

    compact_logo = _compact_logo(
        art,
        max_width=max_width,
        max_height=DEFAULT_MAX_HEIGHT,
    )
    return compact_logo or FALLBACK_LOGO


def render_logo_text(terminal_width: int | None = None) -> Text:
    """Return the logo with a restrained two-tone accent treatment."""
    lines = render_logo(terminal_width).splitlines()
    mid = len(lines) // 2
    text = Text()
    for index, line in enumerate(lines):
        if index:
            text.append("\n")
        color = ACCENTS["violet"] if index < mid else ACCENTS["aqua"]
        text.append(line, style=f"bold {color}")
    return text


def print_logo(console: Console) -> None:
    """Print the Ubundi logo with the brand accent palette."""
    console.print(render_logo_text(console.size.width))
