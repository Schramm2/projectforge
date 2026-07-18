"""Completion sound — optional audio feedback on scaffold finish."""

import platform
import shutil
import subprocess
import threading


def _play_async(cmd: list[str]) -> None:
    """Play a sound asynchronously in a background thread."""

    def _run():
        try:
            subprocess.run(cmd, capture_output=True, timeout=5)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def _bell() -> None:
    """Play terminal bell as universal fallback."""
    print("\a", end="", flush=True)


def play_completion_sound(*, success: bool, enabled: bool) -> None:
    """Play a completion sound if enabled.

    Uses platform-specific audio players with terminal bell fallback.
    """
    if not enabled:
        return

    system = platform.system()

    if system == "Darwin" and shutil.which("afplay"):
        tone = "Glass" if success else "Basso"
        _play_async(["afplay", f"/System/Library/Sounds/{tone}.aiff"])
        return

    if system == "Linux":
        for player in ("paplay", "aplay"):
            if shutil.which(player):
                _bell()
                return

    # Universal fallback
    _bell()
