"""Secret-safe runtime diagnostics for ProjectForge."""

from __future__ import annotations

import json
import platform
import shutil
import sys

from ubundiforge import __version__
from ubundiforge.config import (
    SUPPORTED_BACKENDS,
    BackendStatus,
    _run_status_command,
    get_backend_statuses,
)
from ubundiforge.setup import CONFIG_PATH, _normalize_forge_config

_VERSION_COMMANDS = {
    "claude": ["claude", "--version"],
    "gemini": ["gemini", "--version"],
    "codex": ["codex", "--version"],
}
_EDITOR_COMMANDS = ("cursor", "code", "antigravity", "windsurf", "zed")


def get_backend_version(backend: str) -> str | None:
    """Return a bounded first-line CLI version without invoking a model."""
    command = _VERSION_COMMANDS.get(backend)
    if command is None:
        return None
    result = _run_status_command(command)
    if result is None or result.returncode != 0:
        return None
    output = (result.stdout or result.stderr or "").strip()
    if not output:
        return None
    return output.splitlines()[0][:160]


def _tool_diagnostic(command: str) -> dict[str, bool | str | None]:
    installed = shutil.which(command) is not None
    version = None
    if installed:
        result = _run_status_command([command, "--version"])
        if result is not None and result.returncode == 0:
            output = (result.stdout or result.stderr or "").strip()
            version = output.splitlines()[0][:160] if output else None
    return {"installed": installed, "version": version}


def build_environment_report() -> dict:
    """Return non-identifying local toolchain facts in stable key order."""
    return {
        "python": {
            "version": platform.python_version(),
            "supported": sys.version_info >= (3, 12),
        },
        "git": _tool_diagnostic("git"),
        "docker": _tool_diagnostic("docker"),
        "editors": {editor: shutil.which(editor) is not None for editor in _EDITOR_COMMANDS},
    }


def _config_diagnostic() -> dict[str, str]:
    """Inspect configuration health without loading values or mutating the file."""
    if not CONFIG_PATH.exists():
        return {"status": "missing"}
    try:
        _normalize_forge_config(json.loads(CONFIG_PATH.read_text()))
    except json.JSONDecodeError:
        return {"status": "corrupt"}
    except ValueError:
        return {"status": "invalid"}
    except OSError:
        return {"status": "unreadable"}
    return {"status": "valid"}


def _readiness_label(status: BackendStatus) -> str:
    if not status.installed:
        return "not_installed"
    if status.ready is True:
        return "ready"
    if status.ready is False:
        return "needs_login"
    return "preflight_required"


def build_doctor_report() -> dict:
    """Build a deterministic report containing no configuration or identity values."""
    statuses = get_backend_statuses()
    providers: dict[str, dict] = {}
    for backend in SUPPORTED_BACKENDS:
        status = statuses[backend]
        providers[backend] = {
            "installed": status.installed,
            "readiness": _readiness_label(status),
            "version": get_backend_version(backend) if status.installed else None,
            "auth_mode": status.auth_mode or None,
            "login_command": status.login_command or None,
        }

    config = _config_diagnostic()
    has_ready_provider = any(status.usable for status in statuses.values())
    overall_status = (
        "ready" if has_ready_provider and config["status"] == "valid" else "attention"
    )
    return {
        "schema_version": 1,
        "projectforge_version": __version__,
        "status": overall_status,
        "config": config,
        "environment": build_environment_report(),
        "providers": providers,
    }


def doctor_exit_code(report: dict) -> int:
    """Return zero only when the diagnostic report says Forge is runnable."""
    return 0 if report.get("status") == "ready" else 1
