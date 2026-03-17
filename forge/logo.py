"""Ubundi ASCII logo display."""

from rich.console import Console

LOGO = r"""
 _   _ _                    _ _
| | | | |__  _   _ _ __   __| (_)
| | | | '_ \| | | | '_ \ / _` | |
| |_| | |_) | |_| | | | | (_| | |
 \___/|_.__/ \__,_|_| |_|\__,_|_|
"""


def print_logo(console: Console) -> None:
    """Print the Ubundi ASCII logo in cyan."""
    console.print(f"[bold cyan]{LOGO}[/bold cyan]")
