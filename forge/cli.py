"""Forge CLI — entry point."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from forge import __version__
from forge.config import SUPPORTED_BACKENDS, check_backend_installed
from forge.conventions import load_claude_md_template, load_conventions
from forge.logo import print_logo
from forge.prompt_builder import build_prompt
from forge.prompts import collect_answers
from forge.router import pick_backend_with_fallback
from forge.runner import open_in_editor, run_ai

app = typer.Typer(add_completion=False)
console = Console()


STACK_ALIASES = {
    "nextjs": "nextjs",
    "next": "nextjs",
    "react": "nextjs",
    "fastapi": "fastapi",
    "api": "fastapi",
    "both": "both",
    "fullstack": "both",
    "monorepo": "both",
    "python-cli": "python-cli",
    "cli": "python-cli",
    "typer": "python-cli",
    "ts-package": "ts-package",
    "npm-package": "ts-package",
    "library": "ts-package",
    "python-worker": "python-worker",
    "worker": "python-worker",
    "service": "python-worker",
}


@app.callback(invoke_without_command=True)
def main(
    use: Annotated[
        str | None,
        typer.Option("--use", help="Override AI routing (claude, gemini, or codex)."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print the assembled prompt without executing."),
    ] = False,
    version: Annotated[
        bool,
        typer.Option("--version", "-v", help="Show version and exit."),
    ] = False,
    model: Annotated[
        str | None,
        typer.Option("--model", "-m", help="Model to pass to the AI CLI backend."),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Project name (skips interactive prompt)."),
    ] = None,
    stack: Annotated[
        str | None,
        typer.Option(
            "--stack", "-s",
            help="Stack: nextjs, fastapi, both, python-cli, ts-package, python-worker.",
        ),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Project description."),
    ] = None,
    docker: Annotated[
        bool | None,
        typer.Option("--docker/--no-docker", help="Include Docker setup."),
    ] = None,
    extra: Annotated[
        str | None,
        typer.Option("--extra", "-e", help="Extra instructions for the AI."),
    ] = None,
    services: Annotated[
        str | None,
        typer.Option(
            "--services",
            help="Comma-separated services to include (e.g. 'Clerk,PostgreSQL').",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show detailed execution info."),
    ] = False,
    open_editor: Annotated[
        bool,
        typer.Option("--open", help="Open project in editor after scaffolding."),
    ] = False,
    export: Annotated[
        str | None,
        typer.Option("--export", help="Export assembled prompt to a file."),
    ] = None,
) -> None:
    """Forge — Ubundi Project Scaffolder. Scaffold projects with AI + your conventions."""
    if version:
        console.print(f"forge {__version__}")
        raise typer.Exit()

    if use and use not in SUPPORTED_BACKENDS:
        backends = ", ".join(SUPPORTED_BACKENDS)
        console.print(
            f"[red]Unknown backend '{use}'. Choose from: {backends}[/red]"
        )
        raise typer.Exit(1)

    print_logo(console)
    console.print(Panel("[bold]Forge[/bold] -- Ubundi Project Scaffolder", style="cyan"))

    # Non-interactive mode: all required flags provided
    if name and stack and description:
        resolved_stack = STACK_ALIASES.get(stack.lower())
        if not resolved_stack:
            valid = ", ".join(sorted(set(STACK_ALIASES.values())))
            console.print(f"[red]Unknown stack '{stack}'. Choose from: {valid}[/red]")
            raise typer.Exit(1)

        svc_list = [s.strip() for s in services.split(",")] if services else []
        answers: dict = {
            "name": name.strip(),
            "stack": resolved_stack,
            "description": description.strip(),
            "docker": docker if docker is not None else True,
            "services": svc_list,
            "extra": (extra or "").strip(),
        }
    else:
        answers = collect_answers()

    # Pick backend with fallback
    backend, was_fallback = pick_backend_with_fallback(answers["stack"], override=use)

    if was_fallback:
        from forge.router import pick_backend

        primary = pick_backend(answers["stack"], override=use)
        console.print(
            f"\n[yellow]{primary} not found, falling back to {backend}[/yellow]"
        )
    else:
        console.print(
            f"\n[dim]Using {backend} ({answers['stack']} project detected)[/dim]"
        )

    if model:
        console.print(f"[dim]Model: {model}[/dim]")

    # Check backend is installed (fallback may still fail if nothing is installed)
    if not check_backend_installed(backend):
        console.print(
            f"\n[red bold]{backend}[/red bold] [red]is not installed or not on PATH.[/red]"
            "\n[dim]Install at least one AI CLI (claude, gemini, or codex).[/dim]"
        )
        raise typer.Exit(1)

    # Load conventions and CLAUDE.md template
    conventions, conv_warnings = load_conventions()
    for warning in conv_warnings:
        console.print(f"[yellow]{warning}[/yellow]")
    if verbose:
        n = len(conventions)
        console.print(f"[dim]Conventions: {n} chars from ~/.forge/conventions.md[/dim]")
    else:
        console.print("[dim]Loaded conventions from ~/.forge/conventions.md[/dim]")

    claude_md_template = load_claude_md_template()
    if claude_md_template:
        console.print("[dim]Loaded CLAUDE.md template[/dim]")

    # Build prompt
    prompt = build_prompt(answers, conventions, claude_md_template)

    if verbose:
        console.print(f"[dim]Prompt length: {len(prompt)} chars[/dim]")

    # Export prompt to file
    if export:
        export_path = Path(export)
        export_path.write_text(prompt)
        console.print(f"\n[green]Prompt exported to {export_path}[/green]")
        raise typer.Exit()

    if dry_run:
        console.print("\n[bold]Assembled prompt:[/bold]\n")
        console.print(prompt)
        raise typer.Exit()

    # Run
    project_dir = Path.cwd() / answers["name"]
    console.print(f"[dim]Handing off to {backend}...[/dim]\n")
    returncode = run_ai(backend, prompt, project_dir, model=model, verbose=verbose)

    if returncode == 0:
        console.print(
            f"\n[green bold]Done![/green bold] "
            f"Project created at [bold]{project_dir}[/bold]"
        )
        if open_editor:
            open_in_editor(project_dir)
    else:
        console.print(f"\n[red]{backend} exited with code {returncode}.[/red]")
        raise typer.Exit(returncode)
