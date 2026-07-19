"""Provider-neutral approval modes and shared AI CLI command construction."""

from __future__ import annotations

from pathlib import Path

APPROVAL_MODES = ("safe", "plan", "unsafe")


class UnsafeExecutionError(ValueError):
    """Raised when unsafe execution is requested without explicit consent."""


def validate_approval_mode(approval_mode: str, *, allow_unsafe: bool) -> None:
    """Validate a Forge approval mode before any provider process starts."""
    if approval_mode not in APPROVAL_MODES:
        raise ValueError("That approval mode is not available. Choose `safe`, `plan`, or `unsafe`.")
    if approval_mode == "unsafe" and not allow_unsafe:
        raise UnsafeExecutionError(
            "Unsafe mode removes normal protections. Add `--allow-unsafe` only inside an "
            "isolated environment you control."
        )


def build_provider_command(
    backend: str,
    prompt: str,
    model: str | None = None,
    *,
    approval_mode: str = "safe",
    allow_unsafe: bool = False,
    project_dir: Path | None = None,
) -> list[str]:
    """Build one provider command from a stable Forge approval mode.

    ``project_dir`` is explicit for providers whose CLI does not reliably use
    the subprocess working directory as its workspace (notably Antigravity).
    """
    validate_approval_mode(approval_mode, allow_unsafe=allow_unsafe)
    workspace = str(project_dir.resolve()) if project_dir is not None else None

    if backend == "claude":
        provider_mode = {
            "safe": "acceptEdits",
            "plan": "plan",
            "unsafe": "bypassPermissions",
        }[approval_mode]
        # Safe mode disables ambient hooks, skills, plugins, MCP, and memory
        # while preserving subscription authentication. Forge supplies its
        # effective conventions explicitly in the prompt.
        cmd = [
            "claude",
            "--safe-mode",
            "-p",
            "--permission-mode",
            provider_mode,
            "--no-session-persistence",
        ]
    elif backend == "codex":
        cmd = ["codex"]
        if workspace:
            cmd.extend(["--cd", workspace])
        if approval_mode == "unsafe":
            cmd.extend(["--dangerously-bypass-approvals-and-sandbox", "exec"])
        else:
            sandbox = "read-only" if approval_mode == "plan" else "workspace-write"
            cmd.extend(
                [
                    "--ask-for-approval",
                    "never",
                    "--sandbox",
                    sandbox,
                    "exec",
                ]
            )
        # Forge scaffolds into fresh directories that are not yet git repos,
        # and git init only runs as a post-scaffold step. Without this flag
        # `codex exec` refuses to start ("not inside a trusted directory"),
        # which breaks every safe/plan scaffold.
        cmd.append("--skip-git-repo-check")
        # Forge does not implement provider-session resume. Keep scripted
        # calls ephemeral and ignore ambient user config/exec rules so the
        # explicit Forge policy remains the effective boundary.
        cmd.extend(["--ephemeral", "--ignore-user-config", "--color", "never"])
    elif backend == "antigravity":
        cmd = ["agy"]
        if workspace:
            # `agy` can otherwise attach a print-mode call to its own scratch
            # project even when the subprocess cwd is the Forge target.
            cmd.extend(["--add-dir", workspace])
        provider_mode = "plan" if approval_mode == "plan" else "accept-edits"
        cmd.extend(["--mode", provider_mode])
        if approval_mode in {"safe", "plan"}:
            cmd.append("--sandbox")
        else:
            cmd.append("--dangerously-skip-permissions")
        if model:
            cmd.extend(["--model", model])
        # Antigravity's Go flag parser treats --print as value-taking, so it
        # must remain the final flag immediately before the prompt.
        cmd.extend(["--print", prompt])
        return cmd
    else:
        return []

    if model:
        cmd.extend(["--model", model])
    cmd.append(prompt)
    return cmd
