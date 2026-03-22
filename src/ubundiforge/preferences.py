"""Adaptive preferences — learns user answer patterns for smart defaults."""

import json

from ubundiforge.conventions import FORGE_DIR

PREFERENCES_PATH = FORGE_DIR / "preferences.json"

_MIN_TOTAL = 3
_DOMINANCE_THRESHOLD = 0.70
_SKIP_KEYS = {"name", "description", "extra_instructions", "services_list", "services"}


def load_preferences() -> dict[str, dict[str, int]]:
    """Load preference frequency data from disk."""
    if not PREFERENCES_PATH.exists():
        return {}
    try:
        return json.loads(PREFERENCES_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def record_preferences(answers: dict) -> None:
    """Record answer values, incrementing frequency counts."""
    prefs = load_preferences()

    for key, value in answers.items():
        if key in _SKIP_KEYS or value is None:
            continue
        # Skip complex types — only track scalar preferences
        if isinstance(value, (dict, list)):
            continue
        str_value = str(value)
        if key not in prefs:
            prefs[key] = {}
        prefs[key][str_value] = prefs[key].get(str_value, 0) + 1

    FORGE_DIR.mkdir(parents=True, exist_ok=True)
    PREFERENCES_PATH.write_text(json.dumps(prefs, indent=2) + "\n")


def get_defaults() -> dict[str, str]:
    """Return dominant answer values (>70% frequency, minimum 3 total scaffolds).

    Returns:
        Dict mapping question key to the dominant answer value string.
    """
    prefs = load_preferences()
    defaults: dict[str, str] = {}

    for key, counts in prefs.items():
        total = sum(counts.values())
        if total < _MIN_TOTAL:
            continue
        for value, count in counts.items():
            if count / total >= _DOMINANCE_THRESHOLD:
                defaults[key] = value
                break

    return defaults
