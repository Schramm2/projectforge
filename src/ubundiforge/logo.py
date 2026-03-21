"""Ubundi block-art logo display with deep shadow."""

from rich.console import Console
from rich.text import Text

# Block-pixel grids (1 = filled, 0 = empty). Each letter: 6 cols x 7 rows.
_LETTERS = {
    "U": [
        [1, 1, 0, 1, 1, 0],
        [1, 1, 0, 1, 1, 0],
        [1, 1, 0, 1, 1, 0],
        [1, 1, 0, 1, 1, 0],
        [1, 1, 0, 1, 1, 0],
        [1, 1, 1, 1, 1, 0],
        [0, 1, 1, 1, 0, 0],
    ],
    "B": [
        [1, 1, 1, 1, 0, 0],
        [1, 1, 0, 0, 1, 0],
        [1, 1, 0, 0, 1, 0],
        [1, 1, 1, 1, 0, 0],
        [1, 1, 0, 0, 1, 0],
        [1, 1, 0, 0, 1, 0],
        [1, 1, 1, 1, 0, 0],
    ],
    "N": [
        [1, 1, 0, 1, 1, 0],
        [1, 1, 1, 1, 1, 0],
        [1, 1, 1, 1, 1, 0],
        [1, 1, 1, 1, 1, 0],
        [1, 1, 0, 1, 1, 0],
        [1, 1, 0, 1, 1, 0],
        [1, 1, 0, 1, 1, 0],
    ],
    "D": [
        [1, 1, 1, 1, 0, 0],
        [1, 1, 0, 0, 1, 0],
        [1, 1, 0, 0, 1, 0],
        [1, 1, 0, 0, 1, 0],
        [1, 1, 0, 0, 1, 0],
        [1, 1, 0, 0, 1, 0],
        [1, 1, 1, 1, 0, 0],
    ],
    "I": [
        [1, 1, 1, 1, 1, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
        [1, 1, 1, 1, 1, 0],
    ],
}

_BLOCK = "\u2588\u2588"
_EMPTY = "  "
_WORD = "UBUNDI"
_ROWS = 7
_LETTER_SPACING = "  "
_SHADOW_OFFSET = 1  # rows down

# Cell types for the composite grid
_CELL_NONE = 0
_CELL_MAIN = 1
_CELL_SHADOW = 2


def _build_flat_row(row_idx: int) -> list[int]:
    """Return a flat list of 0/1 values for one row across all letters."""
    cells: list[int] = []
    for i, ch in enumerate(_WORD):
        grid = _LETTERS[ch]
        for col in range(6):
            cells.append(grid[row_idx][col])
        if i < len(_WORD) - 1:
            cells.append(0)  # letter spacing column
    return cells


def _build_composite() -> list[list[int]]:
    """Build a composite grid with main blocks and shadow layer."""
    main_width = len(_build_flat_row(0))
    total_rows = _ROWS + _SHADOW_OFFSET
    composite = [[_CELL_NONE] * main_width for _ in range(total_rows)]

    # Place shadow first (offset down by _SHADOW_OFFSET)
    for row_idx in range(_ROWS):
        flat = _build_flat_row(row_idx)
        for col, val in enumerate(flat):
            if val:
                shadow_row = row_idx + _SHADOW_OFFSET
                if shadow_row < total_rows:
                    composite[shadow_row][col] = _CELL_SHADOW

    # Place main blocks on top (overwrites shadow where they overlap)
    for row_idx in range(_ROWS):
        flat = _build_flat_row(row_idx)
        for col, val in enumerate(flat):
            if val:
                composite[row_idx][col] = _CELL_MAIN

    return composite


def render_logo_text(terminal_width: int | None = None) -> Text:
    """Return the block-art logo as a Rich Text with white blocks and gray shadow."""
    composite = _build_composite()
    text = Text()
    for row_idx, row in enumerate(composite):
        if row_idx:
            text.append("\n")
        # Build line segments grouped by cell type for fewer style spans
        col = 0
        while col < len(row):
            cell = row[col]
            if cell == _CELL_MAIN:
                text.append(_BLOCK, style="bold bright_white")
            elif cell == _CELL_SHADOW:
                text.append(_BLOCK, style="#444444")
            else:
                text.append(_EMPTY)
            col += 1
    return text


def print_logo(console: Console) -> None:
    """Print the Ubundi logo in black and white with deep shadow."""
    console.print(render_logo_text(console.size.width))
