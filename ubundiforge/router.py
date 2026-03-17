"""AI backend routing — picks the best CLI tool for the job."""

from ubundiforge.config import check_backend_installed

ROUTING = {
    "nextjs": "claude",
    "fastapi": "claude",
    "fastapi-ai": "claude",
    "both": "claude",
    "python-cli": "claude",
    "ts-package": "claude",
    "python-worker": "claude",
}

FALLBACK_ORDER = ("claude", "gemini", "codex")


def pick_backend(stack: str, override: str | None = None) -> str:
    """Pick the AI CLI backend based on stack selection.

    Args:
        stack: The stack identifier (nextjs, fastapi, both).
        override: Force a specific backend regardless of routing logic.

    Returns:
        The backend name (claude, gemini, or codex).
    """
    if override:
        return override

    return ROUTING.get(stack, "claude")


def pick_backend_with_fallback(stack: str, override: str | None = None) -> tuple[str, bool]:
    """Pick a backend, falling back to the next available if the primary isn't installed.

    Returns:
        Tuple of (backend_name, was_fallback). was_fallback is True if the
        primary choice wasn't available and a fallback was used.
    """
    primary = pick_backend(stack, override)

    if check_backend_installed(primary):
        return primary, False

    for fallback in FALLBACK_ORDER:
        if fallback != primary and check_backend_installed(fallback):
            return fallback, True

    return primary, False
