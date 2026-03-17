"""Tests for scaffold option helpers."""

from ubundiforge.scaffold_options import (
    auth_provider_choices_for_stack,
    auth_provider_ids_for_stack,
    auth_provider_supported_for_stack,
)


def test_auth_provider_choices_are_available_for_supported_stacks():
    choices = auth_provider_choices_for_stack("nextjs")

    assert choices
    assert choices[0][0] == "clerk"


def test_auth_provider_ids_are_empty_for_unsupported_stacks():
    assert auth_provider_ids_for_stack("fastapi") == []


def test_auth_provider_supported_for_stack_checks_stack_capabilities():
    assert auth_provider_supported_for_stack("both", "clerk") is True
    assert auth_provider_supported_for_stack("fastapi", "clerk") is False
