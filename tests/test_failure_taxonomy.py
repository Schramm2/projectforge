"""Tests for provider failure classification and recovery guidance."""

import pytest

from projectforge.failure_taxonomy import (
    classify_provider_failure,
    is_headless_permission_failure,
)


@pytest.mark.parametrize(
    ("output", "timed_out", "category"),
    [
        ("command not found", False, "missing_binary"),
        ("please login before continuing", False, "authentication"),
        ("429 rate limit exceeded", False, "quota"),
        ("connection refused by upstream", False, "network"),
        ("permission denied for this workspace", False, "permission"),
        (
            "Not inside a trusted directory and --skip-git-repo-check was not specified",
            False,
            "permission",
        ),
        ("model is not available", False, "model"),
        ("anything", True, "timeout"),
        ("unrecognized provider response", False, "unknown"),
    ],
)
def test_provider_failure_taxonomy(output, timed_out, category):
    failure = classify_provider_failure(output, returncode=1, timed_out=timed_out)

    assert failure.category == category
    assert failure.summary
    assert failure.remediation
    assert "--resume" in failure.remediation or category == "missing_binary"


def test_headless_permission_failure_is_detected_even_when_provider_exits_zero():
    output = (
        'no output produced: a tool required the "write_file" permission '
        "that headless mode cannot prompt for"
    )

    assert is_headless_permission_failure(output)
    assert classify_provider_failure(output, returncode=0).category == "permission"


def test_provider_failure_never_echoes_credentials():
    failure = classify_provider_failure(
        "authentication failed for ghp_abcdefghijklmnopqrstuvwxyz1234567890",
        returncode=1,
    )

    rendered = f"{failure.summary} {failure.remediation}"
    assert "ghp_" not in rendered
    assert "abcdefghijklmnopqrstuvwxyz" not in rendered
