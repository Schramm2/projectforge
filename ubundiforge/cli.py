"""UbundiForge CLI — entry point."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from ubundiforge import __version__
from ubundiforge.config import SUPPORTED_BACKENDS, check_backend_installed
from ubundiforge.conventions import load_claude_md_template, load_conventions
from ubundiforge.logo import print_logo
from ubundiforge.prompt_builder import build_phase_prompt
from ubundiforge.prompts import collect_answers
from ubundiforge.router import (
    PHASE_LABELS,
    STACK_PHASES,
    merge_adjacent_phases,
    pick_phase_backends,
)
from ubundiforge.runner import ensure_git_init, open_in_editor, reset_project_dir, run_ai
from ubundiforge.safety import check_for_secrets
from ubundiforge.scaffold_options import (
    AUTH_PROVIDER_OPTIONS,
    CI_TEMPLATE_MODES,
    auth_provider_ids_for_stack,
    auth_provider_supported_for_stack,
    ci_action_ids_for_stack,
)
from ubundiforge.setup import load_forge_config, needs_setup, run_setup
from ubundiforge.verify import print_report, verify_scaffold

app = typer.Typer(add_completion=False)
console = Console()


STACK_ALIASES = {
    "nextjs": "nextjs",
    "next": "nextjs",
    "react": "nextjs",
    "fastapi": "fastapi",
    "api": "fastapi",
    "fastapi-ai": "fastapi-ai",
    "ai": "fastapi-ai",
    "llm": "fastapi-ai",
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
            "--stack",
            "-s",
            help="Stack: nextjs, fastapi, fastapi-ai, both, python-cli, ts-package, python-worker.",
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
    auth_provider: Annotated[
        str | None,
        typer.Option(
            "--auth-provider",
            help="Optional auth provider for Next.js/fullstack stacks.",
        ),
    ] = None,
    ci: Annotated[
        bool | None,
        typer.Option("--ci/--no-ci", help="Include a GitHub Actions CI workflow."),
    ] = None,
    ci_template: Annotated[
        str | None,
        typer.Option(
            "--ci-template",
            help="CI template mode: questionnaire or blank-template.",
        ),
    ] = None,
    ci_actions: Annotated[
        str | None,
        typer.Option(
            "--ci-actions",
            help="Comma-separated CI actions (e.g. 'lint,typecheck,unit-tests').",
        ),
    ] = None,
    setup: Annotated[
        bool,
        typer.Option("--setup", help="Run the setup wizard."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show detailed execution info."),
    ] = False,
    open_editor: Annotated[
        bool,
        typer.Option("--open/--no-open", help="Open project in editor after scaffolding."),
    ] = True,
    verify: Annotated[
        bool,
        typer.Option("--verify/--no-verify", help="Run post-scaffold verification checks."),
    ] = True,
    export: Annotated[
        str | None,
        typer.Option("--export", help="Export assembled prompt to a file."),
    ] = None,
) -> None:
    """UbundiForge — Ubundi Project Scaffolder. Scaffold projects with AI + your conventions."""
    if version:
        console.print(f"ubundiforge {__version__}")
        raise typer.Exit()

    print_logo(console)
    console.print(Panel("[bold]UbundiForge[/bold] -- Ubundi Project Scaffolder", style="cyan"))

    # First-run setup wizard (or manual --setup)
    if setup or needs_setup():
        run_setup(console)
        if setup:
            raise typer.Exit()

    forge_config = load_forge_config()

    if use and use not in SUPPORTED_BACKENDS:
        backends = ", ".join(SUPPORTED_BACKENDS)
        console.print(f"[red]Unknown backend '{use}'. Choose from: {backends}[/red]")
        raise typer.Exit(1)

    # Non-interactive mode: all required flags provided
    if name and stack and description:
        resolved_stack = STACK_ALIASES.get(stack.lower())
        if not resolved_stack:
            valid = ", ".join(sorted(set(STACK_ALIASES.values())))
            console.print(f"[red]Unknown stack '{stack}'. Choose from: {valid}[/red]")
            raise typer.Exit(1)

        from ubundiforge.stacks import STACK_META

        svc_list = [s.strip() for s in services.split(",")] if services else []
        meta = STACK_META.get(resolved_stack)
        docker_val = docker if docker is not None else (meta.docker_default if meta else True)
        if auth_provider and auth_provider not in AUTH_PROVIDER_OPTIONS:
            valid = ", ".join(sorted(AUTH_PROVIDER_OPTIONS))
            console.print(
                f"[red]Unknown auth provider '{auth_provider}'. Choose from: {valid}[/red]"
            )
            raise typer.Exit(1)
        if auth_provider and not auth_provider_supported_for_stack(resolved_stack, auth_provider):
            allowed = auth_provider_ids_for_stack(resolved_stack)
            if allowed:
                valid = ", ".join(allowed)
                console.print(
                    "[red]Auth provider "
                    f"'{auth_provider}' is not supported for stack '{resolved_stack}'. "
                    f"Choose from: {valid}[/red]"
                )
            else:
                console.print(
                    f"[red]Stack '{resolved_stack}' does not support --auth-provider.[/red]"
                )
            raise typer.Exit(1)

        if ci_template and ci_template not in CI_TEMPLATE_MODES:
            valid = ", ".join(CI_TEMPLATE_MODES)
            console.print(f"[red]Unknown CI template '{ci_template}'. Choose from: {valid}[/red]")
            raise typer.Exit(1)

        ci_requested = ci if ci is not None else bool(ci_template or ci_actions)
        ci_mode = None
        action_ids: list[str] = []
        if ci_requested:
            ci_mode = ci_template or ("questionnaire" if ci_actions else "blank-template")
            allowed_actions = set(ci_action_ids_for_stack(resolved_stack))
            if ci_actions:
                action_ids = [action.strip() for action in ci_actions.split(",") if action.strip()]
                invalid_actions = [action for action in action_ids if action not in allowed_actions]
                if invalid_actions:
                    valid = ", ".join(sorted(allowed_actions))
                    invalid = ", ".join(invalid_actions)
                    console.print(
                        "[red]Unknown CI actions "
                        f"'{invalid}' for stack '{resolved_stack}'. Choose from: {valid}[/red]"
                    )
                    raise typer.Exit(1)
            elif ci_mode == "questionnaire":
                action_ids = ci_action_ids_for_stack(resolved_stack)

        answers: dict = {
            "name": name.strip(),
            "stack": resolved_stack,
            "description": description.strip(),
            "docker": docker_val,
            "auth_provider": auth_provider,
            "services": svc_list,
            "ci": {
                "include": ci_requested,
                "mode": ci_mode,
                "actions": action_ids,
            },
            "extra": (extra or "").strip(),
        }
    else:
        answers = collect_answers(
            docker_available=forge_config.get("docker_available", True),
        )

    # --- Multi-backend phase routing ---
    phase_backends = pick_phase_backends(
        answers["stack"],
        override=use,
        description=answers.get("description", ""),
    )
    merged_groups = merge_adjacent_phases(phase_backends)
    all_phases = STACK_PHASES.get(answers["stack"], ["architecture", "tests"])

    # Show routing plan
    if len(merged_groups) == 1:
        _, backend = merged_groups[0]
        console.print(f"\n[dim]Using {backend} for all scaffolding[/dim]")
    else:
        console.print("\n[dim]Multi-backend routing:[/dim]")
        for i, (phases, backend) in enumerate(merged_groups, 1):
            labels = " + ".join(PHASE_LABELS.get(p, p) for p in phases)
            console.print(f"[dim]  {i}. {labels} -> {backend}[/dim]")

    # Check that all required backends are installed
    required_backends = {backend for _, backend in merged_groups}
    for backend in required_backends:
        if not check_backend_installed(backend):
            console.print(
                f"\n[red bold]{backend}[/red bold] [red]is not installed or not on PATH.[/red]"
                "\n[dim]Install at least one AI CLI (claude, gemini, or codex).[/dim]"
            )
            raise typer.Exit(1)

    # Resolve model per backend: --model overrides everything, else use config
    backend_models: dict[str, str] = forge_config.get("backend_models", {})
    if model:
        console.print(f"[dim]Model override: {model}[/dim]")
    elif backend_models:
        for b, m in backend_models.items():
            if b in required_backends:
                console.print(f"[dim]Model for {b}: {m}[/dim]")

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

    # Check all user-supplied text for secrets before passing to AI
    fields_to_scan = {
        "name": answers.get("name", ""),
        "description": answers.get("description", ""),
        "extra": answers.get("extra", ""),
    }
    svc_list = answers.get("services", [])
    if svc_list:
        fields_to_scan["services"] = " ".join(svc_list)

    for field_name, text in fields_to_scan.items():
        if not text:
            continue
        secret_warnings = check_for_secrets(text)
        if secret_warnings:
            types = ", ".join(secret_warnings)
            console.print(
                f"\n[red bold]Possible secrets detected in {field_name}: "
                f"{types}[/red bold]"
                "\n[red]Remove credentials before passing them to an AI CLI.[/red]"
            )
            raise typer.Exit(1)

    # Build prompts for each phase group
    phase_prompts: list[tuple[list[str], str, str]] = []
    for phases, backend in merged_groups:
        prompt = build_phase_prompt(
            phases,
            all_phases,
            answers,
            conventions,
            backend=backend,
            claude_md_template=claude_md_template,
        )
        phase_prompts.append((phases, backend, prompt))

    # Dry run / export: show all phase prompts
    if dry_run or export:
        for phases, backend, prompt in phase_prompts:
            labels = " + ".join(PHASE_LABELS.get(p, p) for p in phases)
            if dry_run:
                if len(phase_prompts) > 1:
                    console.print(f"\n[bold]--- {labels} ({backend}) ---[/bold]\n")
                else:
                    console.print("\n[bold]Assembled prompt:[/bold]\n")
                console.print(prompt)

        if export:
            export_path = Path(export)
            parts = []
            for phases, backend, prompt in phase_prompts:
                label = " + ".join(PHASE_LABELS.get(p, p) for p in phases)
                if len(phase_prompts) > 1:
                    parts.append(f"=== {label} ({backend}) ===\n\n{prompt}")
                else:
                    parts.append(prompt)
            all_text = "\n\n".join(parts)
            export_path.write_text(all_text)
            console.print(f"\n[green]Prompt exported to {export_path}[/green]")

        raise typer.Exit()

    if verbose:
        total_chars = sum(len(prompt) for _, _, prompt in phase_prompts)
        n = len(phase_prompts)
        console.print(f"[dim]Total prompt length: {total_chars} chars across {n} phase(s)[/dim]")

    # Run — use saved projects_dir if set, otherwise CWD
    base_dir = Path(forge_config.get("projects_dir") or Path.cwd())
    project_dir = base_dir / answers["name"]

    # Check if directory already exists
    if project_dir.exists() and any(project_dir.iterdir()):
        console.print(
            f"\n[yellow bold]{project_dir} already exists and is not empty.[/yellow bold]"
        )
        import questionary

        confirm = questionary.confirm("Overwrite existing directory?", default=False).ask()
        if not confirm:
            console.print("[dim]Aborted.[/dim]")
            raise typer.Exit(0)
        reset_project_dir(project_dir)

    # Execute each phase group
    total_groups = len(phase_prompts)
    for group_idx, (phases, backend, prompt) in enumerate(phase_prompts, 1):
        labels = " + ".join(PHASE_LABELS.get(p, p) for p in phases)
        if total_groups > 1:
            console.print(f"\n[dim]Phase {group_idx}/{total_groups}: {labels} -> {backend}[/dim]")
        else:
            console.print(f"[dim]Handing off to {backend}...[/dim]\n")

        effective_model = model or backend_models.get(backend)
        returncode = run_ai(backend, prompt, project_dir, model=effective_model, verbose=verbose)

        if returncode != 0:
            console.print(f"\n[red]{backend} exited with code {returncode} during {labels}.[/red]")
            raise typer.Exit(returncode)

    # Post-scaffold: git init, verify, and open editor
    git_ok = ensure_git_init(project_dir)

    if verify:
        report = verify_scaffold(answers["stack"], project_dir, verbose=verbose)
        print_report(report, console)
        if not report.all_passed:
            console.print(
                "[yellow]Some verification checks failed. "
                "The project was still created successfully.[/yellow]"
            )

    if git_ok:
        console.print(
            f"\n[green bold]Done![/green bold] Project created at [bold]{project_dir}[/bold]"
        )
    else:
        console.print(
            f"\n[yellow bold]Project created at [bold]{project_dir}[/bold], "
            f"but git initialization failed.[/yellow bold]"
            "\n[yellow]Run 'git init && git add -A && git commit -m \"Initial commit\"' "
            "manually to finish setup.[/yellow]"
        )
    if open_editor:
        preferred = forge_config.get("preferred_editor", "")
        open_in_editor(project_dir, preferred_editor=preferred)
    else:
        console.print(f"[dim]Run your editor manually: cd {project_dir}[/dim]")
