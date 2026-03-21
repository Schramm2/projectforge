"""
UBUNDI Block Art Terminal Banner
Import and call print_banner() from any Python CLI tool.
"""

# Block-pixel grid definitions (1 = filled, 0 = empty)
# Each letter is 6 cols × 7 rows
LETTERS = {
    'U': [
        [1,1,0,1,1,0],
        [1,1,0,1,1,0],
        [1,1,0,1,1,0],
        [1,1,0,1,1,0],
        [1,1,0,1,1,0],
        [1,1,1,1,1,0],
        [0,1,1,1,0,0],
    ],
    'B': [
        [1,1,1,1,0,0],
        [1,1,0,0,1,0],
        [1,1,0,0,1,0],
        [1,1,1,1,0,0],
        [1,1,0,0,1,0],
        [1,1,0,0,1,0],
        [1,1,1,1,0,0],
    ],
    'N': [
        [1,1,0,1,1,0],
        [1,1,1,1,1,0],
        [1,1,1,1,1,0],
        [1,1,1,1,1,0],
        [1,1,0,1,1,0],
        [1,1,0,1,1,0],
        [1,1,0,1,1,0],
    ],
    'D': [
        [1,1,1,1,0,0],
        [1,1,0,0,1,0],
        [1,1,0,0,1,0],
        [1,1,0,0,1,0],
        [1,1,0,0,1,0],
        [1,1,0,0,1,0],
        [1,1,1,1,0,0],
    ],
    'I': [
        [1,1,1,1,1,0],
        [0,0,1,0,0,0],
        [0,0,1,0,0,0],
        [0,0,1,0,0,0],
        [0,0,1,0,0,0],
        [0,0,1,0,0,0],
        [1,1,1,1,1,0],
    ],
}

BLOCK = "██"
SHADOW = "░░"
EMPTY = "  "


def render_ubundi(shadow: bool = True, color: bool = True) -> str:
    """Render UBUNDI as block art string."""
    word = "UBUNDI"
    rows = 7
    lines = []

    # ANSI codes
    W = "\033[97m" if color else ""   # bright white
    D = "\033[90m" if color else ""   # dark gray
    R = "\033[0m" if color else ""    # reset

    for row in range(rows):
        line = "  "
        for i, ch in enumerate(word):
            grid = LETTERS[ch]
            for col in range(6):
                if grid[row][col]:
                    line += f"{W}{BLOCK}{R}"
                else:
                    line += EMPTY
            if i < len(word) - 1:
                line += "  "  # letter spacing
        lines.append(line)

    if shadow:
        # Add shadow line at bottom
        shadow_line = "  "
        for i, ch in enumerate(word):
            grid = LETTERS[ch]
            bottom = grid[-1]
            for col in range(6):
                if bottom[col]:
                    shadow_line += f"{D}▀▀{R}"
                else:
                    shadow_line += EMPTY
            if i < len(word) - 1:
                shadow_line += "  "
        lines.append(shadow_line)

    return "\n".join(lines)


def print_banner(shadow: bool = True, color: bool = True):
    """Print the UBUNDI banner to stdout."""
    print()
    print(render_ubundi(shadow=shadow, color=color))
    print()


if __name__ == "__main__":
    print_banner()