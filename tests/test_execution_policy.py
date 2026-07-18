"""Tests for provider-neutral execution approval modes."""

import pytest

from projectforge.execution_policy import (
    UnsafeExecutionError,
    build_provider_command,
    validate_approval_mode,
)


@pytest.mark.parametrize(
    ("backend", "expected"),
    [
        ("claude", ["--permission-mode", "plan"]),
        ("codex", ["--sandbox", "read-only"]),
        ("antigravity", ["--mode", "plan"]),
    ],
)
def test_plan_mode_is_read_only(backend, expected):
    cmd = build_provider_command(backend, "inspect", approval_mode="plan")
    index = cmd.index(expected[0])
    assert cmd[index : index + 2] == expected


def test_unsafe_mode_requires_explicit_consent():
    with pytest.raises(UnsafeExecutionError, match="normal protections"):
        build_provider_command("codex", "write files", approval_mode="unsafe")


def test_unknown_approval_mode_is_rejected_before_execution():
    with pytest.raises(ValueError, match="not available"):
        validate_approval_mode("automatic", allow_unsafe=False)


@pytest.mark.parametrize(
    ("backend", "dangerous_value"),
    [
        ("claude", "bypassPermissions"),
        ("codex", "--dangerously-bypass-approvals-and-sandbox"),
        ("antigravity", "--dangerously-skip-permissions"),
    ],
)
def test_unsafe_mode_is_deliberately_named_and_provider_specific(backend, dangerous_value):
    cmd = build_provider_command(
        backend,
        "write files",
        approval_mode="unsafe",
        allow_unsafe=True,
    )
    assert dangerous_value in cmd


def test_antigravity_safe_mode_uses_headless_sandboxed_accept_edits():
    cmd = build_provider_command("antigravity", "build it", approval_mode="safe")

    assert cmd == [
        "agy",
        "--mode",
        "accept-edits",
        "--sandbox",
        "--print",
        "build it",
    ]


def test_antigravity_print_flag_remains_immediately_before_prompt_with_model():
    cmd = build_provider_command(
        "antigravity",
        "build it",
        model="Gemini 3.5 Flash (High)",
        approval_mode="safe",
    )

    assert cmd[-2:] == ["--print", "build it"]
    assert cmd[cmd.index("--model") + 1] == "Gemini 3.5 Flash (High)"
