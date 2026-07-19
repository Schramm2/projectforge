"""Tests for flag-driven scaffold request validation and normalization."""

import pytest

from projectforge.scaffold_request import (
    NonInteractiveScaffoldRequest,
    ScaffoldRequestError,
)


def test_request_resolves_alias_defaults_ci_and_sole_media_collection() -> None:
    answers = NonInteractiveScaffoldRequest(
        name="  atlas  ",
        stack="react",
        description="  Customer portal  ",
        services="Clerk, PostgreSQL",
        ci_actions="lint,typecheck",
        extra="  Use Tailwind v4  ",
    ).resolve(list_media_collection_names=lambda: ("brand",))

    assert answers == {
        "name": "atlas",
        "stack": "nextjs",
        "description": "Customer portal",
        "docker": False,
        "design_template": None,
        "media_collection": "brand",
        "auth_provider": None,
        "services": ["Clerk", "PostgreSQL"],
        "ci": {
            "include": True,
            "mode": "questionnaire",
            "actions": ["lint", "typecheck"],
        },
        "extra": "Use Tailwind v4",
        "demo_mode": True,
    }


def test_request_explicit_values_override_stack_and_media_defaults() -> None:
    answers = NonInteractiveScaffoldRequest(
        name="worker",
        stack="python-worker",
        description="Process events",
        docker=False,
        media="campaign",
        ci=False,
    ).resolve(list_media_collection_names=lambda: ("brand",))

    assert answers["docker"] is False
    assert answers["media_collection"] == "campaign"
    assert answers["ci"] == {"include": False, "mode": None, "actions": []}


def test_request_does_not_scan_media_when_explicitly_disabled() -> None:
    answers = NonInteractiveScaffoldRequest(
        name="api",
        stack="fastapi",
        description="Customer API",
        no_media=True,
    ).resolve(
        list_media_collection_names=lambda: (_ for _ in ()).throw(
            AssertionError("disabled media must not be listed")
        )
    )

    assert answers["media_collection"] is None


@pytest.mark.parametrize(
    ("scaffold_request", "message"),
    [
        (
            NonInteractiveScaffoldRequest("x", "unknown", "x"),
            "That stack is not available",
        ),
        (
            NonInteractiveScaffoldRequest("x", "fastapi", "x", auth_provider="clerk"),
            "does not support an authentication option",
        ),
        (
            NonInteractiveScaffoldRequest(
                "x", "fastapi", "x", design_template="default-design-guide"
            ),
            "does not support a design template",
        ),
        (
            NonInteractiveScaffoldRequest("x", "nextjs", "x", ci_actions="docker-build"),
            "CI checks do not work with this stack",
        ),
    ],
)
def test_request_rejects_unsupported_flag_combinations(scaffold_request, message) -> None:
    with pytest.raises(ScaffoldRequestError, match=message):
        scaffold_request.resolve(list_media_collection_names=lambda: ())
