"""Scoped, temporary provider permission grants for headless scaffolding.

Antigravity's print mode auto-denies ``write_file`` unless an allow-rule exists
in its ``settings.json``. Forge grants a rule scoped to exactly the target
workspace for the duration of a safe-mode run, then restores the file to its
previous state. Only safe mode needs this: plan mode is read-only and unsafe
mode uses ``--dangerously-skip-permissions``.

The grant is:

- Narrow — ``write_file(<workspace>)`` for the one target directory, never
  ``write_file(*)``.
- Non-destructive — existing user settings are preserved on a best-effort JSON
  merge; the file is restored to its exact prior bytes (or removed if Forge
  created it) once the run finishes.
- Reference-counted — concurrent phases that share one workspace add the rule
  once and restore only after the last phase completes.
"""

from __future__ import annotations

import contextlib
import json
import threading
from collections.abc import Iterator
from pathlib import Path

ANTIGRAVITY_SETTINGS_PATH = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"

_lock = threading.Lock()
_refcounts: dict[str, int] = {}
_snapshots: dict[Path, bytes | None] = {}


def allow_rule(project_dir: Path) -> str:
    """Return the narrow ``write_file`` allow-rule for a workspace."""
    return f"write_file({project_dir.resolve()})"


@contextlib.contextmanager
def workspace_write_permission(
    backend: str,
    approval_mode: str,
    project_dir: Path | None,
    *,
    settings_path: Path = ANTIGRAVITY_SETTINGS_PATH,
) -> Iterator[None]:
    """Temporarily allow the provider to write into ``project_dir``.

    A no-op unless ``backend`` is antigravity running in safe mode with a
    workspace. Safe to nest across concurrent phases that share a workspace.
    """
    if not (backend == "antigravity" and approval_mode == "safe" and project_dir is not None):
        yield
        return

    rule = allow_rule(project_dir)
    with _lock:
        if _refcounts.get(rule, 0) == 0:
            _snapshots.setdefault(
                settings_path,
                settings_path.read_bytes() if settings_path.exists() else None,
            )
            _grant(settings_path, rule)
        _refcounts[rule] = _refcounts.get(rule, 0) + 1

    try:
        yield
    finally:
        with _lock:
            _refcounts[rule] -= 1
            if _refcounts[rule] == 0:
                del _refcounts[rule]
                if not _refcounts:
                    _restore(settings_path, _snapshots.pop(settings_path, None))


def _load(settings_path: Path) -> dict:
    if not settings_path.exists():
        return {}
    try:
        data = json.loads(settings_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _grant(settings_path: Path, rule: str) -> None:
    settings = _load(settings_path)
    permissions = settings.setdefault("permissions", {})
    if not isinstance(permissions, dict):
        permissions = {}
        settings["permissions"] = permissions
    allow = permissions.setdefault("allow", [])
    if not isinstance(allow, list):
        allow = []
        permissions["allow"] = allow
    if rule not in allow:
        allow.append(rule)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def _restore(settings_path: Path, snapshot: bytes | None) -> None:
    if snapshot is None:
        settings_path.unlink(missing_ok=True)
    else:
        settings_path.write_bytes(snapshot)
