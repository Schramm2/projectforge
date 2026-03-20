"""Module entry point for `python -m ubundiforge`."""

from ubundiforge.cli import app


def main() -> None:
    """Run the Forge CLI."""
    app(prog_name="forge")


if __name__ == "__main__":
    main()
