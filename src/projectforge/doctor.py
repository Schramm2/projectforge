"""Secret-safe runtime diagnostics for ProjectForge."""

from __future__ import annotations

import json
import platform
import shutil
import sys

from projectforge import __version__
from projectforge.config import (
    SUPPORTED_BACKENDS,
    BackendStatus,
    _run_status_command,
    get_backend_statuses,
)
from projectforge.provider_capabilities import PROVIDER_CAPABILITIES
from projectforge.setup import (
    CONFIG_PATH,
    SUPPORTED_EDITORS,
    _check_editor_installed,
    _normalize_forge_config,
)

_VERSION_COMMANDS = {
    "claude": ["claude", "--version"],
    "antigravity": ["agy", "--version"],
    "codex": ["codex", "--version"],
}
_READINESS_COMMANDS = {
    "claude": "claude auth status",
    "antigravity": "agy --version; agy models",
    "codex": "codex login status",
}


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
    editors = {
        command: any(_check_editor_installed(command, app_bundle))
        for command, _label, app_bundle in SUPPORTED_EDITORS
    }
    return {
        "python": {
            "version": platform.python_version(),
            "supported": sys.version_info >= (3, 12),
        },
        "git": _tool_diagnostic("git"),
        "docker": _tool_diagnostic("docker"),
        "editors": editors,
    }


def _config_diagnostic() -> tuple[dict[str, str], dict[str, str]]:
    """Inspect config and return only health plus credential-safe model overrides."""
    if not CONFIG_PATH.exists():
        return {"status": "missing"}, {}
    try:
        config = _normalize_forge_config(json.loads(CONFIG_PATH.read_text()))
    except json.JSONDecodeError:
        return {"status": "corrupt"}, {}
    except ValueError:
        return {"status": "invalid"}, {}
    except OSError:
        return {"status": "unreadable"}, {}
    return {"status": "valid"}, dict(config.get("backend_models", {}))


def _readiness_label(status: BackendStatus) -> str:
    if not status.installed:
        return "not_installed"
    if status.ready is True:
        return "ready"
    if status.ready is False:
        return "needs_login"
    return "check_inconclusive"


def _provider_repair(backend: str, status: BackendStatus) -> str:
    """Return a provider-specific, identity-free recovery action."""
    if status.ready is True:
        return "No action required."
    if not status.installed:
        return (
            "Run `projectforge --setup` for the official installation guide, then rerun "
            "`projectforge doctor`."
        )
    if status.ready is False:
        return "Complete this tool's official sign-in flow, then rerun `projectforge doctor`."
    return (
        "Run `projectforge --setup` for the recommended manual readiness check, then rerun "
        "`projectforge doctor`."
    )


def _provider_check(backend: str, status: BackendStatus) -> dict[str, str]:
    """Describe the credential-safe readiness check and its observed result."""
    command = _READINESS_COMMANDS[backend]
    if not status.installed:
        executable = command.split()[0]
        return {
            "command": f"PATH lookup for `{executable}`",
            "observed": "Forge could not find this tool on your system.",
        }
    if backend == "antigravity" and "version check" in status.detail.lower():
        command = "agy --version"
    if status.ready is True:
        observed = "The readiness check confirmed an active signed-in session."
    elif status.ready is False:
        observed = "The readiness check reported that authentication is required."
    else:
        observed = "The readiness check could not confirm sign-in."
    return {"command": command, "observed": observed}


def build_doctor_report() -> dict:
    """Build a deterministic report containing no configuration or identity values."""
    statuses = get_backend_statuses()
    config, backend_models = _config_diagnostic()
    providers: dict[str, dict] = {}
    for backend in SUPPORTED_BACKENDS:
        status = statuses[backend]
        capability = PROVIDER_CAPABILITIES[backend]
        providers[backend] = {
            "installed": status.installed,
            "readiness": _readiness_label(status),
            "version": get_backend_version(backend) if status.installed else None,
            "auth_mode": status.auth_mode or None,
            "login_command": status.login_command or None,
            "install_url": capability.install_url,
            "model_behavior": {
                "mode": "override" if backend in backend_models else "provider_default",
                "value": backend_models.get(backend),
            },
            "capabilities": capability.diagnostic_payload(),
            "check": _provider_check(backend, status),
            "repair": _provider_repair(backend, status),
        }

    has_ready_provider = any(status.usable for status in statuses.values())
    overall_status = "ready" if has_ready_provider and config["status"] == "valid" else "attention"
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
