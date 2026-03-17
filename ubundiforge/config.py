"""Configuration and tool availability checks."""

import shutil

SUPPORTED_BACKENDS = ("claude", "gemini", "codex")


def check_backend_installed(backend: str) -> bool:
    """Check if the given AI CLI tool is installed and available on PATH."""
    return shutil.which(backend) is not None


def get_available_backends() -> list[str]:
    """Return list of installed AI CLI backends."""
    return [b for b in SUPPORTED_BACKENDS if check_backend_installed(b)]
