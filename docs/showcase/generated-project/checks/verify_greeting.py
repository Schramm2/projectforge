"""Verification checks for the showcase greeting CLI."""

from typer.testing import CliRunner

from hello_forge.cli import app


def test_named_greeting() -> None:
    """The CLI greets the requested name."""
    result = CliRunner().invoke(app, ["--name", "Ada"])

    assert result.exit_code == 0
    assert result.stdout == "Hello, Ada!\n"
