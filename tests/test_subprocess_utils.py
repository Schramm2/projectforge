"""Tests for the subprocess_utils shared module."""

from ubundiforge.subprocess_utils import (
    ANSI_RE,
    PHASE_TIMEOUT,
    PULSE_STYLES,
    SPINNER_FRAMES,
    format_activity,
    is_noisy_progress_line,
    sanitize_progress_line,
    spinner_frame,
    spinner_style,
    summarize_output_line,
)

# --- Constants ---


def test_phase_timeout_is_reasonable():
    assert isinstance(PHASE_TIMEOUT, int)
    assert PHASE_TIMEOUT >= 60  # at least a minute
    assert PHASE_TIMEOUT <= 7200  # no more than 2 hours


def test_spinner_frames_is_non_empty_tuple_of_strings():
    assert isinstance(SPINNER_FRAMES, tuple)
    assert len(SPINNER_FRAMES) > 0
    for frame in SPINNER_FRAMES:
        assert isinstance(frame, str)


def test_pulse_styles_contains_expected_accents():
    for accent in ("aqua", "amber", "violet", "plum"):
        assert accent in PULSE_STYLES
        palette = PULSE_STYLES[accent]
        assert len(palette) > 0
        for color in palette:
            assert isinstance(color, str)


def test_ansi_re_strips_escape_sequences():
    assert ANSI_RE.sub("", "\x1b[32mhello\x1b[0m") == "hello"
    assert ANSI_RE.sub("", "plain text") == "plain text"


# --- sanitize_progress_line ---


def test_sanitize_strips_ansi_codes():
    result = sanitize_progress_line("\x1b[32mCreating files\x1b[0m")
    assert result == "Creating files"


def test_sanitize_collapses_whitespace():
    result = sanitize_progress_line("  lots   of   spaces  ")
    assert result == "lots of spaces"


def test_sanitize_truncates_long_lines():
    long_line = "x" * 200
    result = sanitize_progress_line(long_line)
    assert len(result) == 120


def test_sanitize_handles_empty_string():
    assert sanitize_progress_line("") == ""


def test_sanitize_preserves_normal_line():
    result = sanitize_progress_line("Writing and refining project files")
    assert result == "Writing and refining project files"


# --- is_noisy_progress_line ---


def test_is_noisy_empty_string():
    assert is_noisy_progress_line("") is True


def test_is_noisy_shell_prompt():
    assert is_noisy_progress_line("$ cat src/main.py") is True


def test_is_noisy_diff_headers():
    assert is_noisy_progress_line("diff --git a/foo.py b/foo.py") is True
    assert is_noisy_progress_line("@@  -1,4 +1,6 @@") is True
    assert is_noisy_progress_line("+++ b/foo.py") is True
    assert is_noisy_progress_line("--- a/foo.py") is True


def test_is_noisy_code_fence():
    assert is_noisy_progress_line("```python") is True


def test_is_noisy_json_brace():
    assert is_noisy_progress_line('{"key": "value"}') is True


def test_is_noisy_deeply_nested_path():
    # more than 6 slashes
    assert is_noisy_progress_line("a/b/c/d/e/f/g/h") is True


def test_is_noisy_normal_line_is_not_noisy():
    assert is_noisy_progress_line("Creating the main application module") is False


def test_is_noisy_gt_prompt():
    assert is_noisy_progress_line("> npm run build") is True


# --- summarize_output_line ---


def test_summarize_review_keywords():
    expected = "Reviewing the scaffold brief"
    assert summarize_output_line("Inspecting the existing codebase") == expected
    assert summarize_output_line("Analyzing the requirements") == expected


def test_summarize_install_keywords():
    assert summarize_output_line("Running pnpm install") == "Installing project dependencies"
    assert summarize_output_line("Installing dependencies now") == "Installing project dependencies"


def test_summarize_write_keywords():
    assert summarize_output_line("create file app/page.tsx") == "Writing and refining project files"
    assert summarize_output_line("apply_patch to routes.py") == "Writing and refining project files"
    assert summarize_output_line("edit routes.py now") == "Writing and refining project files"


def test_summarize_test_keywords():
    assert summarize_output_line("Running pytest -q") == "Running tests and checks"
    assert summarize_output_line("Executing jest suite") == "Running tests and checks"


def test_summarize_build_keywords():
    assert summarize_output_line("Building the project bundle") == "Building the project"


def test_summarize_git_keywords():
    assert summarize_output_line("git init in the project dir") == "Finalizing the repository"


def test_summarize_error_keywords():
    expected = "Working through an issue in the scaffold"
    assert summarize_output_line("Error: module not found") == expected
    assert summarize_output_line("Traceback (most recent call last)") == expected


def test_summarize_done_keywords():
    assert summarize_output_line("All done!") == "Wrapping up this phase"
    assert summarize_output_line("Phase finished successfully.") == "Wrapping up this phase"


def test_summarize_returns_none_for_unmatched():
    assert summarize_output_line("some unrelated line of output") is None


# --- spinner_frame ---


def test_spinner_frame_returns_string():
    result = spinner_frame(0.0)
    assert isinstance(result, str)
    assert len(result) > 0


def test_spinner_frame_cycles_through_frames():
    frames_seen = set()
    for i in range(100):
        frames_seen.add(spinner_frame(i * 0.1))
    # Should see multiple distinct frames
    assert len(frames_seen) > 1


def test_spinner_frame_stays_within_spinner_frames():
    for elapsed in (0.0, 0.5, 1.0, 5.0, 10.0, 99.9):
        assert spinner_frame(elapsed) in SPINNER_FRAMES


# --- spinner_style ---


def test_spinner_style_returns_string():
    result = spinner_style("violet", 0.0)
    assert isinstance(result, str)
    assert result.startswith("#")


def test_spinner_style_unknown_accent_falls_back_to_violet():
    result = spinner_style("nonexistent", 0.0)
    assert result in PULSE_STYLES["violet"]


def test_spinner_style_cycles():
    styles = {spinner_style("aqua", i * 0.2) for i in range(20)}
    assert len(styles) > 1


# --- format_activity ---


def test_format_activity_short_text_unchanged():
    assert format_activity("Short text") == "Short text"


def test_format_activity_exactly_at_limit():
    text = "x" * 54
    assert format_activity(text) == text


def test_format_activity_truncates_long_text():
    text = "x" * 60
    result = format_activity(text)
    assert len(result) == 54
    assert result.endswith("…")


def test_format_activity_custom_limit():
    text = "hello world this is a long message"
    result = format_activity(text, limit=10)
    assert len(result) == 10
    assert result.endswith("…")
