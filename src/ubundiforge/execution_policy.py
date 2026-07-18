"""Provider-neutral approval modes and shared AI CLI command construction."""

from __future__ import annotations

APPROVAL_MODES = ("safe", "plan", "unsafe")


class UnsafeExecutionError(ValueError):
    """Raised when unsafe execution is requested without explicit consent."""


def validate_approval_mode(approval_mode: str, *, allow_unsafe: bool) -> None:
    """Validate a Forge approval mode before any provider process starts."""
    if approval_mode not in APPROVAL_MODES:
        valid = ", ".join(APPROVAL_MODES)
        raise ValueError(f"unknown approval mode {approval_mode!r}; choose from: {valid}")
    if approval_mode == "unsafe" and not allow_unsafe:
        raise UnsafeExecutionError("unsafe execution requires explicit consent via --allow-unsafe")


def build_provider_command(
    backend: str,
    prompt: str,
    model: str | None = None,
    *,
    approval_mode: str = "safe",
    allow_unsafe: bool = False,
) -> list[str]:
    """Build one provider command from a stable Forge approval mode."""
    validate_approval_mode(approval_mode, allow_unsafe=allow_unsafe)

    if backend == "claude":
        provider_mode = {
            "safe": "acceptEdits",
            "plan": "plan",
            "unsafe": "bypassPermissions",
        }[approval_mode]
        cmd = [
            "claude",
            "-p",
            "--permission-mode",
            provider_mode,
            "--no-session-persistence",
        ]
    elif backend == "codex":
        if approval_mode == "unsafe":
            cmd = ["codex", "--dangerously-bypass-approvals-and-sandbox", "exec"]
        else:
            sandbox = "read-only" if approval_mode == "plan" else "workspace-write"
            cmd = [
                "codex",
                "--ask-for-approval",
                "never",
                "--sandbox",
                sandbox,
                "exec",
            ]
    elif backend == "gemini":
        provider_mode = {
            "safe": "auto_edit",
            "plan": "plan",
            "unsafe": "yolo",
        }[approval_mode]
        cmd = ["gemini", "-p", prompt, "--approval-mode", provider_mode, "--sandbox"]
        if model:
            cmd.extend(["--model", model])
        return cmd
    else:
        return []

    if model:
        cmd.extend(["--model", model])
    cmd.append(prompt)
    return cmd
