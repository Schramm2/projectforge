"""Stable, credential-free provider failure categories and recovery guidance."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderFailure:
    """A privacy-safe failure category suitable for UI and progress evidence."""

    category: str
    summary: str
    remediation: str


_RULES = (
    (
        "missing_binary",
        re.compile(r"command not found|no such file|executable.*not found", re.I),
        "The selected AI tool is not available.",
        "Run `forge doctor` for setup steps, then retry with `--resume`.",
    ),
    (
        "authentication",
        re.compile(r"not logged in|please log[ -]?in|login required|unauth|authentication", re.I),
        "Forge could not confirm sign-in for the selected AI tool.",
        "Run `forge doctor`, complete the recommended sign-in step, then retry with `--resume`.",
    ),
    (
        "quota",
        re.compile(r"rate.?limit|\b429\b|quota|credit|billing limit|usage limit", re.I),
        "The AI service is temporarily unavailable because of a usage limit.",
        "Keep the partial project, wait for access to return, then retry with `--resume`.",
    ),
    (
        "network",
        re.compile(
            r"connection refused|connection reset|network|dns|timed out connecting|proxy", re.I
        ),
        "Forge could not reach the AI service.",
        "Check your connection and proxy settings, run `forge doctor`, then retry with `--resume`.",
    ),
    (
        "permission",
        re.compile(r"permission denied|not permitted|sandbox|workspace.*denied|approval", re.I),
        "A workspace permission blocked this step.",
        "Keep safe mode, review the selected tool's workspace access, then retry with `--resume`.",
    ),
    (
        "model",
        re.compile(r"model.*(?:not available|not found|unsupported|invalid)|unknown model", re.I),
        "That model is not available for this run.",
        "Remove `--model` to use the default, then retry with `--resume`.",
    ),
)


def classify_provider_failure(
    output: str,
    *,
    returncode: int | None,
    timed_out: bool = False,
) -> ProviderFailure:
    """Classify untrusted provider output without echoing any of it."""
    if timed_out:
        return ProviderFailure(
            category="timeout",
            summary="Project generation took longer than the allowed time.",
            remediation="Keep the partial project and retry the incomplete work with `--resume`.",
        )
    for category, pattern, summary, remediation in _RULES:
        if pattern.search(output):
            return ProviderFailure(category, summary, remediation)
    return ProviderFailure(
        category="unknown",
        summary="Project generation stopped for an unexpected reason.",
        remediation="Keep the partial project, run `forge doctor`, then retry with `--resume`.",
    )
