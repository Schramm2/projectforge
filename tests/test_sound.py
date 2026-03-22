"""Tests for the completion sound module."""

from unittest.mock import patch

from ubundiforge.sound import play_completion_sound


def test_play_sound_success_no_crash():
    """play_completion_sound(success=True) does not crash."""
    with patch("ubundiforge.sound._play_async"):
        play_completion_sound(success=True, enabled=True)


def test_play_sound_failure_no_crash():
    """play_completion_sound(success=False) does not crash."""
    with patch("ubundiforge.sound._play_async"):
        play_completion_sound(success=False, enabled=True)


def test_play_sound_disabled_noop():
    """Does nothing when disabled."""
    play_completion_sound(success=True, enabled=False)
    # Should not crash, should not play anything


def test_play_sound_bell_fallback():
    """Falls back to terminal bell when no audio player found."""
    with patch("ubundiforge.sound.platform.system", return_value="Other"):
        with patch("ubundiforge.sound.shutil.which", return_value=None):
            with patch("builtins.print") as mock_print:
                play_completion_sound(success=True, enabled=True)
                mock_print.assert_called_once_with("\a", end="", flush=True)
