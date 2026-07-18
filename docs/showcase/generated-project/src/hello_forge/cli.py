"""Command-line entry point for the showcase fixture."""

from typing import Annotated

import typer

app = typer.Typer(add_completion=False, help="Print a friendly greeting.")


@app.callback(invoke_without_command=True)
def greet(
    name: Annotated[str, typer.Option(help="Name to greet.")] = "world",
) -> None:
    """Print a deterministic greeting."""
    typer.echo(f"Hello, {name}!")
