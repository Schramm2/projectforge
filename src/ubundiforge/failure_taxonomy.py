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
        "The provider CLI is unavailable.",
        "Install the provider from its official source, then rerun `forge doctor`.",
    ),
    (
        "authentication",
        re.compile(r"not logged in|please log[ -]?in|login required|unauth|authentication", re.I),
        "The provider is not authenticated for this run.",
        "Use the provider-owned login flow, rerun `forge doctor`, then repeat with `--resume`.",
    ),
    (
        "quota",
        re.compile(r"rate.?limit|\b429\b|quota|credit|billing limit|usage limit", re.I),
        "The provider rejected the call because of quota or rate limits.",
        "Preserve the project, wait or choose another ready provider, then repeat with `--resume`.",
    ),
    (
        "network",
        re.compile(
            r"connection refused|connection reset|network|dns|timed out connecting|proxy", re.I
        ),
        "The provider could not be reached reliably.",
        "Check connectivity and proxy settings, rerun `forge doctor`, then repeat with `--resume`.",
    ),
    (
        "permission",
        re.compile(r"permission denied|not permitted|sandbox|workspace.*denied|approval", re.I),
        "The provider's workspace or approval policy blocked the operation.",
        "Keep safe mode, adjust only the scoped provider policy, then repeat with `--resume`.",
    ),
    (
        "model",
        re.compile(r"model.*(?:not available|not found|unsupported|invalid)|unknown model", re.I),
        "The requested model is unavailable to the provider.",
        "Remove the model override or select a provider-supported model, then repeat with "
        "`--resume`.",
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
            summary="The provider phase exceeded its time limit.",
            remediation=(
                "Preserve partial output and repeat only the incomplete phase with `--resume`."
            ),
        )
    for category, pattern, summary, remediation in _RULES:
        if pattern.search(output):
            return ProviderFailure(category, summary, remediation)
    exit_label = f" (exit {returncode})" if returncode is not None else ""
    return ProviderFailure(
        category="unknown",
        summary=f"The provider phase failed{exit_label} for an unclassified reason.",
        remediation=(
            "Preserve partial output, inspect the redacted failure, then repeat with `--resume`."
        ),
    )
