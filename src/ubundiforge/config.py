"""Configuration and tool availability checks."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass

SUPPORTED_BACKENDS = ("claude", "gemini", "codex")


def check_backend_installed(backend: str) -> bool:
    """Check if the given AI CLI tool is installed and available on PATH."""
    return shutil.which(backend) is not None


def get_available_backends() -> list[str]:
    """Return list of installed AI CLI backends."""
    return [b for b in SUPPORTED_BACKENDS if check_backend_installed(b)]


@dataclass(frozen=True)
class BackendStatus:
    """Runtime readiness for a supported AI backend."""

    installed: bool
    ready: bool | None
    detail: str = ""
    login_command: str = ""

    @property
    def usable(self) -> bool:
        """Return whether the backend should be considered routable."""
        return self.installed and self.ready is not False

    @property
    def status_label(self) -> str:
        """Return a concise user-facing readiness label."""
        if not self.installed:
            return "Not found"
        if self.ready is True:
            return "Ready"
        if self.ready is False:
            return "Needs login"
        return "Not verified"


def _run_status_command(
    cmd: list[str],
    timeout: int = 5,
) -> subprocess.CompletedProcess[str] | None:
    """Run a backend status command and return its process result."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def _check_claude_status() -> BackendStatus:
    """Inspect Claude Code authentication state."""
    if not check_backend_installed("claude"):
        return BackendStatus(installed=False, ready=False)

    result = _run_status_command(["claude", "auth", "status"])
    if result is None:
        return BackendStatus(
            installed=True,
            ready=None,
            detail="Could not verify Claude login status.",
            login_command="claude auth login",
        )

    stdout = (result.stdout or "").strip()
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        payload = {}

    if payload.get("loggedIn") is True:
        auth_method = payload.get("authMethod", "authenticated")
        return BackendStatus(
            installed=True,
            ready=True,
            detail=f"Logged in via {auth_method}.",
            login_command="claude auth login",
        )

    if payload.get("loggedIn") is False or "not logged in" in stdout.lower():
        return BackendStatus(
            installed=True,
            ready=False,
            detail="Claude is installed but not authenticated.",
            login_command="claude auth login",
        )

    return BackendStatus(
        installed=True,
        ready=None,
        detail="Claude is installed; login state could not be confirmed.",
        login_command="claude auth login",
    )


def _check_codex_status() -> BackendStatus:
    """Inspect Codex authentication state."""
    if not check_backend_installed("codex"):
        return BackendStatus(installed=False, ready=False)

    result = _run_status_command(["codex", "login", "status"])
    if result is None:
        return BackendStatus(
            installed=True,
            ready=None,
            detail="Could not verify Codex login status.",
            login_command="codex login",
        )

    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip().lower()
    if "not logged in" in output or "login required" in output:
        return BackendStatus(
            installed=True,
            ready=False,
            detail="Codex is installed but not authenticated.",
            login_command="codex login",
        )
    if "logged in" in output:
        return BackendStatus(
            installed=True,
            ready=True,
            detail="Codex login verified.",
            login_command="codex login",
        )

    return BackendStatus(
        installed=True,
        ready=None,
        detail="Codex is installed; login state could not be confirmed.",
        login_command="codex login",
    )


def _check_gemini_status() -> BackendStatus:
    """Inspect Gemini availability.

    Gemini's bundled help does not expose a login-status command, so setup
    can only verify that the CLI exists on PATH.
    """
    if not check_backend_installed("gemini"):
        return BackendStatus(installed=False, ready=False)

    return BackendStatus(
        installed=True,
        ready=None,
        detail="Gemini is installed; login readiness is not verified by setup.",
    )


def get_backend_status(backend: str) -> BackendStatus:
    """Return a backend's installation and readiness status."""
    if backend == "claude":
        return _check_claude_status()
    if backend == "codex":
        return _check_codex_status()
    if backend == "gemini":
        return _check_gemini_status()
    return BackendStatus(installed=False, ready=False, detail="Unsupported backend.")


def get_backend_statuses() -> dict[str, BackendStatus]:
    """Return statuses for every supported backend."""
    return {backend: get_backend_status(backend) for backend in SUPPORTED_BACKENDS}


def get_usable_backends() -> list[str]:
    """Return installed backends that are ready or cannot be verified safely."""
    return [backend for backend, status in get_backend_statuses().items() if status.usable]
