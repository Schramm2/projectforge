"""Shared Questionary theme and prompt wrappers."""

from __future__ import annotations

from typing import Any

import questionary

from ubundiforge.ui import ACCENTS, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY

QUESTIONARY_STYLE = questionary.Style(
    [
        ("qmark", f"fg:{ACCENTS['aqua']} bold"),
        ("question", f"fg:{TEXT_PRIMARY} bold"),
        ("answer", f"fg:{ACCENTS['plum']} bold"),
        ("pointer", f"fg:{ACCENTS['amber']} bold"),
        ("highlighted", f"fg:{ACCENTS['violet']} bold"),
        ("selected", f"fg:{ACCENTS['aqua']} bold"),
        ("separator", f"fg:{TEXT_MUTED}"),
        ("instruction", f"fg:{TEXT_MUTED} italic"),
        ("text", f"fg:{TEXT_SECONDARY}"),
        ("disabled", f"fg:{TEXT_MUTED} italic"),
    ]
)


def prompt_text(message: str, **kwargs: Any):
    """Create a themed free-text prompt."""
    return questionary.text(message, style=QUESTIONARY_STYLE, **kwargs)


def prompt_select(message: str, **kwargs: Any):
    """Create a themed single-select prompt."""
    return questionary.select(message, style=QUESTIONARY_STYLE, **kwargs)


def prompt_confirm(message: str, **kwargs: Any):
    """Create a themed confirm prompt."""
    return questionary.confirm(message, style=QUESTIONARY_STYLE, **kwargs)


def prompt_checkbox(message: str, **kwargs: Any):
    """Create a themed multi-select prompt."""
    return questionary.checkbox(message, style=QUESTIONARY_STYLE, **kwargs)
