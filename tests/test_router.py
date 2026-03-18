"""Tests for the AI routing logic."""

from unittest.mock import patch

from ubundiforge.router import (
    merge_adjacent_phases,
    pick_backend,
    pick_backend_with_fallback,
    pick_phase_backends,
)

# --- Legacy single-backend tests ---


def test_override_takes_precedence():
    assert pick_backend("nextjs", override="codex") == "codex"
    assert pick_backend("fastapi", override="gemini") == "gemini"


def test_default_is_claude():
    assert pick_backend("fastapi") == "claude"
    assert pick_backend("nextjs") == "claude"
    assert pick_backend("unknown") == "claude"


# --- Fallback chain tests (legacy) ---


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


# --- Phase-based routing tests ---


@patch("ubundiforge.router.check_backend_installed", return_value=True)
def test_all_three_installed_nextjs_gets_four_phases(mock_check):
    result = pick_phase_backends("nextjs")
    assert result == [
        ("architecture", "claude"),
        ("frontend", "gemini"),
        ("tests", "codex"),
        ("verify", "claude"),
    ]


@patch("ubundiforge.router.check_backend_installed", return_value=True)
def test_all_three_installed_fastapi_gets_three_phases(mock_check):
    result = pick_phase_backends("fastapi")
    assert result == [
        ("architecture", "claude"),
        ("tests", "codex"),
        ("verify", "claude"),
    ]


@patch("ubundiforge.router.check_backend_installed", side_effect=lambda b: b == "claude")
def test_only_claude_handles_everything(mock_check):
    result = pick_phase_backends("nextjs")
    assert result == [
        ("architecture", "claude"),
        ("frontend", "claude"),
        ("tests", "claude"),
        ("verify", "claude"),
    ]


@patch(
    "ubundiforge.router.check_backend_installed",
    side_effect=lambda b: b in ("claude", "gemini"),
)
def test_claude_gemini_routes_frontend_to_gemini(mock_check):
    result = pick_phase_backends("nextjs")
    assert result == [
        ("architecture", "claude"),
        ("frontend", "gemini"),
        ("tests", "claude"),
        ("verify", "claude"),
    ]


@patch("ubundiforge.router.check_backend_installed", side_effect=lambda b: b in ("claude", "codex"))
def test_claude_codex_routes_tests_to_codex(mock_check):
    result = pick_phase_backends("fastapi")
    assert result == [
        ("architecture", "claude"),
        ("tests", "codex"),
        ("verify", "claude"),
    ]


@patch("ubundiforge.router.check_backend_installed", return_value=True)
def test_override_forces_single_backend(mock_check):
    result = pick_phase_backends("nextjs", override="gemini")
    assert result == [
        ("architecture", "gemini"),
        ("frontend", "gemini"),
        ("tests", "gemini"),
        ("verify", "gemini"),
    ]


@patch("ubundiforge.router.check_backend_installed", return_value=True)
def test_description_keywords_route_architecture_to_codex(mock_check):
    result = pick_phase_backends("fastapi", description="a CI pipeline automation tool")
    assert result[0] == ("architecture", "codex")


@patch("ubundiforge.router.check_backend_installed", return_value=True)
def test_description_keywords_no_match_keeps_claude(mock_check):
    result = pick_phase_backends("fastapi", description="a customer dashboard")
    assert result[0] == ("architecture", "claude")


@patch("ubundiforge.router.check_backend_installed", side_effect=lambda b: b == "codex")
def test_codex_only_handles_all_phases(mock_check):
    result = pick_phase_backends("nextjs")
    assert all(backend == "codex" for _, backend in result)


# --- Phase merging tests ---


def test_merge_same_backend_collapses():
    phase_backends = [
        ("architecture", "claude"),
        ("frontend", "claude"),
        ("tests", "claude"),
    ]
    merged = merge_adjacent_phases(phase_backends)
    assert merged == [
        (["architecture", "frontend", "tests"], "claude"),
    ]


def test_merge_different_backends_stays_separate():
    phase_backends = [
        ("architecture", "claude"),
        ("frontend", "gemini"),
        ("tests", "codex"),
    ]
    merged = merge_adjacent_phases(phase_backends)
    assert merged == [
        (["architecture"], "claude"),
        (["frontend"], "gemini"),
        (["tests"], "codex"),
    ]


def test_merge_adjacent_same_backend():
    phase_backends = [
        ("architecture", "claude"),
        ("frontend", "gemini"),
        ("tests", "claude"),
    ]
    merged = merge_adjacent_phases(phase_backends)
    assert merged == [
        (["architecture"], "claude"),
        (["frontend"], "gemini"),
        (["tests"], "claude"),
    ]


def test_merge_two_phase_stack():
    phase_backends = [
        ("architecture", "claude"),
        ("tests", "codex"),
    ]
    merged = merge_adjacent_phases(phase_backends)
    assert merged == [
        (["architecture"], "claude"),
        (["tests"], "codex"),
    ]


def test_merge_two_phase_same_backend():
    phase_backends = [
        ("architecture", "claude"),
        ("tests", "claude"),
    ]
    merged = merge_adjacent_phases(phase_backends)
    assert merged == [
        (["architecture", "tests"], "claude"),
    ]


def test_merge_empty_input():
    assert merge_adjacent_phases([]) == []
