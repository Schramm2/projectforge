"""Tests for the AI routing logic."""

from unittest.mock import patch

from ubundiforge.router import pick_backend, pick_backend_with_fallback


def test_nextjs_routes_to_gemini():
    assert pick_backend("nextjs") == "claude"


def test_fastapi_routes_to_claude():
    assert pick_backend("fastapi") == "claude"


def test_both_routes_to_claude():
    assert pick_backend("both") == "claude"


def test_fastapi_ai_routes_to_claude():
    assert pick_backend("fastapi-ai") == "claude"


def test_python_cli_routes_to_claude():
    assert pick_backend("python-cli") == "claude"


def test_ts_package_routes_to_claude():
    assert pick_backend("ts-package") == "claude"


def test_python_worker_routes_to_claude():
    assert pick_backend("python-worker") == "claude"


def test_unknown_stack_defaults_to_claude():
    assert pick_backend("unknown") == "claude"


def test_override_takes_precedence():
    assert pick_backend("nextjs", override="codex") == "codex"
    assert pick_backend("fastapi", override="gemini") == "gemini"


def test_override_none_uses_routing():
    assert pick_backend("nextjs", override=None) == "claude"


# Fallback chain tests


@patch("ubundiforge.router.check_backend_installed", return_value=True)
def test_fallback_not_needed_when_primary_installed(mock_check):
    backend, was_fallback = pick_backend_with_fallback("fastapi")
    assert backend == "claude"
    assert was_fallback is False


@patch("ubundiforge.router.check_backend_installed", side_effect=lambda b: b != "claude")
def test_fallback_to_gemini_when_claude_missing(mock_check):
    backend, was_fallback = pick_backend_with_fallback("fastapi")
    assert backend == "gemini"
    assert was_fallback is True


@patch("ubundiforge.router.check_backend_installed", side_effect=lambda b: b == "codex")
def test_fallback_to_codex_when_others_missing(mock_check):
    backend, was_fallback = pick_backend_with_fallback("fastapi")
    assert backend == "codex"
    assert was_fallback is True


@patch("ubundiforge.router.check_backend_installed", return_value=False)
def test_fallback_returns_primary_when_nothing_installed(mock_check):
    backend, was_fallback = pick_backend_with_fallback("fastapi")
    assert backend == "claude"
    assert was_fallback is False


@patch("ubundiforge.router.check_backend_installed", side_effect=lambda b: b != "gemini")
def test_fallback_for_nextjs_when_gemini_missing(mock_check):
    backend, was_fallback = pick_backend_with_fallback("nextjs")
    assert backend == "claude"
    assert was_fallback is False
