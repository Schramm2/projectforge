"""UbundiForge CLI — entry point."""

import re
from pathlib import Path
from typing import Annotated

import questionary
import typer
from rich.text import Text

from ubundiforge import __version__
from ubundiforge.config import (
    SUPPORTED_BACKENDS,
    BackendStatus,
    get_backend_statuses,
)
from ubundiforge.conventions import load_claude_md_template, load_conventions
from ubundiforge.design_templates import (
    DESIGN_TEMPLATE_OPTIONS,
    design_template_ids_for_stack,
    design_template_supported_for_stack,
    load_design_template,
)
from ubundiforge.logo import print_logo
from ubundiforge.media_assets import (
    MEDIA_DIR,
    build_asset_manifest,
    copy_assets,
    list_collections,
    scan_assets,
    target_asset_dir,
)
from ubundiforge.prompt_builder import build_phase_prompt
from ubundiforge.prompts import collect_answers
from ubundiforge.questionary_theme import prompt_confirm, prompt_select, prompt_text
from ubundiforge.router import (
    PHASE_LABELS,
    STACK_PHASES,
    merge_adjacent_phases,
    pick_phase_backends,
)
from ubundiforge.runner import (
    ensure_git_init,
    open_in_editor,
    reset_project_dir,
    run_ai,
    run_ai_parallel,
    run_post_scaffold_hook,
)
from ubundiforge.safety import check_for_secrets
from ubundiforge.scaffold_log import append_scaffold_log, write_scaffold_manifest
from ubundiforge.scaffold_options import (
    AUTH_PROVIDER_OPTIONS,
    CI_TEMPLATE_MODES,
    auth_provider_ids_for_stack,
    auth_provider_supported_for_stack,
    ci_action_ids_for_stack,
)
from ubundiforge.setup import load_forge_config, needs_setup, run_setup
from ubundiforge.ui import (
    bullet,
    command_text,
    create_console,
    grouped_lines,
    header_panel,
    make_panel,
    make_step_panel,
    muted,
    path_text,
    status_line,
    subtle,
)
from ubundiforge.verify import print_report, verify_scaffold

app = typer.Typer()
console = create_console()

_PROJECT_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
_BACKEND_LOGIN_COMMANDS = {
    "claude": "claude auth login",
    "codex": "codex login",
}


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


def _render_routing_plan(
    serial_first: list[tuple[str, str]],
    parallel_middle: list[tuple[str, str]],
    serial_last: list[tuple[str, str]],
    can_parallel: bool,
) -> None:
    """Render the selected routing plan."""
    if not parallel_middle and not serial_last and len(serial_first) == 1:
        _, backend = serial_first[0]
        console.print(status_line(f"Using {backend} for all scaffolding", accent="violet"))
        return

    lines: list[Text] = []
    step = 1
    for phase, backend in serial_first:
        label = PHASE_LABELS.get(phase, phase)
        lines.append(bullet(f"{step}. {label} -> {backend}", accent="aqua"))
        step += 1
    if can_parallel:
        parts = [
            f"{PHASE_LABELS.get(phase, phase)} -> {backend}" for phase, backend in parallel_middle
        ]
        lines.append(bullet(f"{step}. parallel: {' | '.join(parts)}", accent="amber"))
        step += 1
    else:
        for phase, backend in parallel_middle:
            label = PHASE_LABELS.get(phase, phase)
            lines.append(bullet(f"{step}. {label} -> {backend}", accent="aqua"))
            step += 1
    for phase, backend in serial_last:
        label = PHASE_LABELS.get(phase, phase)
        lines.append(bullet(f"{step}. {label} -> {backend}", accent="plum"))
        step += 1

    console.print(
        make_panel(
            grouped_lines(lines),
            title="Routing Plan",
            accent="violet",
        )
    )


def _render_loaded_context(
    required_backends: set[str],
    backend_models: dict[str, str],
    *,
    model_override: str | None,
    conventions: str,
    claude_md_loaded: bool,
    design_template_label: str | None,
    media_collection: str | None = None,
    media_asset_count: int = 0,
) -> None:
    """Render loaded scaffold context."""
    lines: list[Text] = []
    if model_override:
        lines.append(subtle(f"Model override: {model_override}"))
    elif backend_models:
        for backend in sorted(required_backends):
            configured_model = backend_models.get(backend)
            if configured_model:
                lines.append(subtle(f"{backend} model: {configured_model}"))

    lines.append(subtle(f"Conventions: {len(conventions)} chars from ~/.forge/conventions.md"))
    if claude_md_loaded:
        lines.append(subtle("CLAUDE.md starter loaded"))
    if design_template_label:
        lines.append(subtle(f"Design template: {design_template_label}"))
    if media_collection and media_asset_count:
        lines.append(subtle(f"Media: {media_asset_count} files from {media_collection}/"))

    console.print(make_panel(grouped_lines(lines), title="Scaffold Context", accent="aqua"))


def _render_completion(project_dir: Path, *, git_ok: bool) -> None:
    """Render the final completion state."""
    if git_ok:
        lines = grouped_lines(
            [
                subtle("Project created at"),
                path_text(project_dir),
            ]
        )
        console.print(make_panel(lines, title="Scaffold Complete", accent="aqua"))
        return

    lines = grouped_lines(
        [
            subtle("Project created, but git initialization failed."),
            path_text(project_dir),
            muted('Run git init && git add -A && git commit -m "Initial commit" manually.'),
        ]
    )
    console.print(make_panel(lines, title="Scaffold Complete", accent="amber"))


def _render_next_steps(answers: dict, project_dir: Path, *, open_editor: bool) -> None:
    """Render the next-step commands."""
    lines: list[Text] = [command_text(f"cd {project_dir}")]

    from ubundiforge.stacks import STACK_META

    meta = STACK_META.get(answers["stack"])
    if meta and meta.env_hints:
        lines.append(subtle("Copy .env.example to .env.local and fill in your secrets."))
    if meta and meta.dev_commands:
        run_cmd = meta.dev_commands.get("run") or meta.dev_commands.get("dev")
        if run_cmd:
            lines.append(command_text(run_cmd))
        test_cmd = meta.dev_commands.get("test")
        if test_cmd:
            lines.append(command_text(test_cmd))
    if not open_editor:
        lines.append(muted(f"Open your editor manually from {project_dir}."))

    console.print(
        make_panel(
            grouped_lines(lines),
            title="Next Steps",
            accent="plum",
        )
    )


def _backend_help_line(backend: str, status: BackendStatus) -> Text:
    """Return a user-facing readiness line for a backend."""
    if status.ready is False:
        login_command = status.login_command or _BACKEND_LOGIN_COMMANDS.get(backend, backend)
        return subtle(f"{backend} needs login. Run {login_command}.")
    if not status.installed:
        return subtle(f"{backend} is not installed or not on PATH.")
    return subtle(f"{backend} is installed, but Forge could not auto-check readiness.")


def _render_backend_readiness_notice(
    backend_statuses: dict[str, BackendStatus],
    *,
    required_backends: set[str],
) -> None:
    """Render a panel when required backends are unavailable for routing."""
    lines: list[Text] = []
    for backend in sorted(required_backends):
        status = backend_statuses.get(backend, BackendStatus(False, False))
        lines.append(_backend_help_line(backend, status))
    lines.append(muted("Run forge --setup after fixing login or install issues."))
    console.print(make_panel(grouped_lines(lines), title="Backend Readiness", accent="amber"))


def _render_phase_failure(backend: str, label: str, returncode: int) -> None:
    """Render helpful follow-up guidance when a scaffold phase fails."""
    lines: list[Text] = [
        subtle(f"{label} failed with {backend} (exit {returncode})."),
        subtle("Re-run with --verbose for full subprocess output."),
        subtle("Use --dry-run to inspect the assembled prompt before trying again."),
        muted("You can also force a different backend with --use if another one is ready."),
    ]
    console.print(make_panel(grouped_lines(lines), title="Execution", accent="amber"))


def _render_verification_guidance(project_dir: Path) -> None:
    """Render concrete next steps after verification failures."""
    console.print()
    console.print(
        make_panel(
            grouped_lines(
                [
                    subtle("Some verification checks failed."),
                    subtle("The scaffold was still created successfully."),
                    subtle(
                        "Inspect the failing checks above, then rerun the relevant "
                        "commands in:"
                    ),
                    path_text(project_dir),
                    command_text(f"cd {project_dir}"),
                ]
            ),
            title="Verification",
            accent="amber",
        )
    )


def _validate_project_name_for_collision(name: str) -> bool | str:
    """Validate a replacement project name when resolving collisions."""
    if not name.strip():
        return "Project name cannot be empty."
    if not _PROJECT_NAME_RE.match(name):
        return (
            "Must start with a letter/number and contain only letters, numbers, "
            "dots, hyphens, or underscores."
        )
    return True


def _resolve_project_dir(base_dir: Path, answers: dict) -> Path:
    """Resolve the final scaffold directory, offering safer collision options."""
    while True:
        project_dir = base_dir / answers["name"]
        if not project_dir.exists() or not any(project_dir.iterdir()):
            return project_dir

        console.print()
        console.print(
            make_panel(
                grouped_lines(
                    [
                        Text(
                            f"{project_dir} already exists and is not empty.",
                            style="bold #F7F9FF",
                        ),
                        subtle("Choose another name, overwrite it, or cancel."),
                    ]
                ),
                title="Existing Directory",
                accent="amber",
            )
        )

        action = prompt_select(
            "How would you like to proceed?",
            choices=[
                questionary.Choice("Choose another project name", value="rename"),
                questionary.Choice("Overwrite the existing directory", value="overwrite"),
                questionary.Choice("Cancel", value="cancel"),
            ],
            default="rename",
        ).ask()
        if action is None or action == "cancel":
            console.print(status_line("Aborted.", accent="amber"))
            raise typer.Exit(0)

        if action == "rename":
            new_name = prompt_text(
                "Choose another project name",
                default=f"{answers['name']}-2",
                validate=_validate_project_name_for_collision,
            ).ask()
            if new_name is None:
                raise typer.Exit(0)
            answers["name"] = new_name.strip()
            continue

        confirm = prompt_confirm("Overwrite the existing directory", default=False).ask()
        if confirm is None:
            raise typer.Exit(0)
        if confirm:
            reset_project_dir(project_dir)
            return project_dir


def _has_explicit_scaffold_request(**kwargs: object) -> bool:
    """Return whether the user has already signaled project-scaffold intent."""
    return any(
        [
            bool(kwargs.get("use")),
            bool(kwargs.get("model")),
            bool(kwargs.get("name")),
            bool(kwargs.get("stack")),
            bool(kwargs.get("description")),
            bool(kwargs.get("design_template")),
            kwargs.get("docker") is not None,
            bool(kwargs.get("extra")),
            bool(kwargs.get("services")),
            bool(kwargs.get("auth_provider")),
            kwargs.get("ci") is not None,
            bool(kwargs.get("ci_template")),
            bool(kwargs.get("ci_actions")),
            bool(kwargs.get("media")),
            bool(kwargs.get("no_media")),
        ]
    )


def _prompt_post_setup_next_step() -> str:
    """Ask a first-run user what they want to do after setup completes."""
    from ubundiforge.config import get_usable_backends

    has_usable = bool(get_usable_backends())

    console.print()
    if has_usable:
        console.print(
            make_panel(
                grouped_lines(
                    [
                        subtle("Forge is configured and ready."),
                        subtle(
                            "You can create a project now, revisit your setup, "
                            "or exit and come back later."
                        ),
                        muted("Useful commands: forge, forge --dry-run, forge --setup"),
                    ]
                ),
                title="You're Ready",
                accent="plum",
            )
        )
    else:
        console.print(
            make_panel(
                grouped_lines(
                    [
                        subtle("Forge is configured, but no backends are ready yet."),
                        subtle("Log into an AI CLI before creating a project."),
                        muted("Useful commands: forge --setup, forge --dry-run"),
                    ]
                ),
                title="Almost Ready",
                accent="amber",
            )
        )

    choices = []
    if has_usable:
        choices.append(questionary.Choice("Create a project now", value="create"))
    choices.extend([
        questionary.Choice("Review setup again", value="setup"),
        questionary.Choice("Exit for now", value="exit"),
    ])

    action = prompt_select(
        "What would you like to do next?",
        choices=choices,
        default="create" if has_usable else "exit",
    ).ask()
    if action is None:
        raise typer.Exit()
    return action


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
    design_template: Annotated[
        str | None,
        typer.Option(
            "--design-template",
            help="Optional design template / brand guide for frontend-capable stacks.",
        ),
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
    demo: Annotated[
        bool,
        typer.Option(
            "--demo/--no-demo",
            help="Demo mode: project runs without real API keys.",
        ),
    ] = True,
    media: Annotated[
        str | None,
        typer.Option(
            "--media",
            help="Media collection name from the media/ folder to import.",
        ),
    ] = None,
    no_media: Annotated[
        bool,
        typer.Option("--no-media", help="Skip media asset import."),
    ] = False,
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
    prompt_only = dry_run or bool(export)
    explicit_scaffold_request = _has_explicit_scaffold_request(
        use=use,
        model=model,
        name=name,
        stack=stack,
        description=description,
        design_template=design_template,
        docker=docker,
        extra=extra,
        services=services,
        auth_provider=auth_provider,
        ci=ci,
        ci_template=ci_template,
        ci_actions=ci_actions,
        media=media,
        no_media=no_media,
    )

    if version:
        console.print(f"ubundiforge {__version__}")
        raise typer.Exit()

    print_logo(console)
    console.print(header_panel(__version__))

    # First-run setup wizard (or manual --setup)
    auto_setup = not setup and not prompt_only and needs_setup()
    if setup or auto_setup:
        while True:
            run_setup(console)
            if not auto_setup or explicit_scaffold_request:
                break

            action = _prompt_post_setup_next_step()
            if action == "create":
                break
            if action == "setup":
                continue
            raise typer.Exit()

        if setup:
            raise typer.Exit()

    forge_config = load_forge_config()
    backend_statuses = get_backend_statuses() if not prompt_only else {}

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

        if design_template and design_template not in DESIGN_TEMPLATE_OPTIONS:
            valid = ", ".join(sorted(DESIGN_TEMPLATE_OPTIONS))
            console.print(
                f"[red]Unknown design template '{design_template}'. Choose from: {valid}[/red]"
            )
            raise typer.Exit(1)
        if design_template and not design_template_supported_for_stack(
            resolved_stack, design_template
        ):
            allowed = design_template_ids_for_stack(resolved_stack)
            if allowed:
                valid = ", ".join(allowed)
                console.print(
                    "[red]Design template "
                    f"'{design_template}' is not supported for stack '{resolved_stack}'. "
                    f"Choose from: {valid}[/red]"
                )
            else:
                console.print(
                    f"[red]Stack '{resolved_stack}' does not support --design-template.[/red]"
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

        # Resolve --media / --no-media: explicit name, or auto-pick sole collection
        media_collection: str | None = None
        if not no_media:
            if media:
                media_collection = media
            else:
                collections = list_collections()
                if len(collections) == 1:
                    media_collection = collections[0].name

        answers: dict = {
            "name": name.strip(),
            "stack": resolved_stack,
            "description": description.strip(),
            "docker": docker_val,
            "design_template": design_template,
            "media_collection": media_collection,
            "auth_provider": auth_provider,
            "services": svc_list,
            "ci": {
                "include": ci_requested,
                "mode": ci_mode,
                "actions": action_ids,
            },
            "extra": (extra or "").strip(),
            "demo_mode": demo,
        }
    else:
        answers = collect_answers(
            docker_available=forge_config.get("docker_available", True),
        )

    # --- Multi-backend phase routing ---
    available_backends = (
        {backend for backend, status in backend_statuses.items() if status.usable}
        if backend_statuses
        else None
    )
    phase_backends = pick_phase_backends(
        answers["stack"],
        override=use,
        description=answers.get("description", ""),
        prefer_installed_backends=not prompt_only,
        available_backends=available_backends,
    )
    merged_groups = merge_adjacent_phases(phase_backends)
    all_phases = STACK_PHASES.get(answers["stack"], ["architecture", "tests"])

    # Identify which phases can run in parallel (everything between first and last)
    # Architecture must run first, verify must run last, middle phases run concurrently.
    from ubundiforge.router import PHASE_ARCHITECTURE, PHASE_VERIFY

    serial_first: list[tuple[str, str]] = []
    parallel_middle: list[tuple[str, str]] = []
    serial_last: list[tuple[str, str]] = []
    for phase, backend in phase_backends:
        if phase == PHASE_ARCHITECTURE:
            serial_first.append((phase, backend))
        elif phase == PHASE_VERIFY:
            serial_last.append((phase, backend))
        else:
            parallel_middle.append((phase, backend))

    can_parallel = len(parallel_middle) > 1

    # Show routing plan
    console.print()
    _render_routing_plan(serial_first, parallel_middle, serial_last, can_parallel)

    # Check that all required backends are installed
    required_backends = {backend for _, backend in phase_backends}
    if not prompt_only:
        if not available_backends:
            _render_backend_readiness_notice(
                backend_statuses,
                required_backends={
                    backend
                    for backend, status in backend_statuses.items()
                    if status.installed
                },
            )
            raise typer.Exit(1)

        for backend in required_backends:
            status = backend_statuses.get(backend, BackendStatus(False, False))
            if not status.installed:
                console.print(
                    f"\n[red bold]{backend}[/red bold] [red]is not installed or not on PATH.[/red]"
                    "\n[dim]Install at least one AI CLI (claude, gemini, or codex).[/dim]"
                )
                raise typer.Exit(1)
            if status.ready is False:
                _render_backend_readiness_notice(backend_statuses, required_backends={backend})
                raise typer.Exit(1)

    # Resolve model per backend: --model overrides everything, else use config
    backend_models: dict[str, str] = forge_config.get("backend_models", {})

    # Load conventions and CLAUDE.md template
    conventions, conv_warnings = load_conventions()
    for warning in conv_warnings:
        console.print(f"[yellow]{warning}[/yellow]")

    claude_md_template = load_claude_md_template()

    selected_design_template = answers.get("design_template")
    if selected_design_template:
        design_template_content, template_warnings = load_design_template(selected_design_template)
        for warning in template_warnings:
            console.print(f"[yellow]{warning}[/yellow]")
        if design_template_content:
            answers["design_template_content"] = design_template_content
            answers["design_template_label"] = DESIGN_TEMPLATE_OPTIONS[
                selected_design_template
            ].label

    # Scan media assets if a collection was selected
    media_asset_count = 0
    media_source_dir: Path | None = None
    selected_collection = answers.get("media_collection")
    if selected_collection:
        collection_dir = MEDIA_DIR / selected_collection
        media_files = scan_assets(collection_dir)
        if media_files:
            stack = answers["stack"]
            manifest = build_asset_manifest(media_files, target_asset_dir(stack))
            answers["media_assets_manifest"] = manifest
            media_asset_count = len(media_files)
            media_source_dir = collection_dir

    _render_loaded_context(
        required_backends,
        backend_models,
        model_override=model,
        conventions=conventions,
        claude_md_loaded=bool(claude_md_template),
        design_template_label=answers.get("design_template_label"),
        media_collection=selected_collection,
        media_asset_count=media_asset_count,
    )

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

    # Resolve the target project directory before prompts are assembled so any
    # rename choice becomes part of the prompt contract.
    # Skip directory resolution in prompt-only mode to avoid side effects.
    base_dir = Path(forge_config.get("projects_dir") or Path.cwd())
    project_dir = base_dir / answers["name"]
    if not prompt_only:
        project_dir = _resolve_project_dir(base_dir, answers)

    # Build prompts for each individual phase
    phase_prompts: list[tuple[str, str, str]] = []  # (phase, backend, prompt)
    for phase, backend in phase_backends:
        prompt = build_phase_prompt(
            [phase],
            all_phases,
            answers,
            conventions,
            backend=backend,
            claude_md_template=claude_md_template,
        )
        phase_prompts.append((phase, backend, prompt))

    # Also build merged prompts for dry-run/export (preserves existing behavior)
    merged_prompts: list[tuple[list[str], str, str]] = []
    for phases, backend in merged_groups:
        prompt = build_phase_prompt(
            phases,
            all_phases,
            answers,
            conventions,
            backend=backend,
            claude_md_template=claude_md_template,
        )
        merged_prompts.append((phases, backend, prompt))

    # Dry run / export: show all phase prompts
    if dry_run or export:
        for phases, backend, prompt in merged_prompts:
            labels = " + ".join(PHASE_LABELS.get(p, p) for p in phases)
            if dry_run:
                if len(merged_prompts) > 1:
                    console.print()
                    console.print(
                        make_panel(
                            grouped_lines(
                                [
                                    Text(labels, style="bold #F7F9FF"),
                                    Text(f"Backend: {backend}", style="#8893B3"),
                                ]
                            ),
                            title="Prompt Preview",
                            accent="amber",
                        )
                    )
                else:
                    console.print()
                    console.print(
                        make_panel(
                            Text("Assembled prompt", style="bold #F7F9FF"),
                            title="Prompt Preview",
                            accent="amber",
                        )
                    )
                console.print(prompt)

        if export:
            export_path = Path(export)
            parts = []
            for phases, backend, prompt in merged_prompts:
                label = " + ".join(PHASE_LABELS.get(p, p) for p in phases)
                if len(merged_prompts) > 1:
                    parts.append(f"=== {label} ({backend}) ===\n\n{prompt}")
                else:
                    parts.append(prompt)
            all_text = "\n\n".join(parts)
            try:
                export_path.parent.mkdir(parents=True, exist_ok=True)
                export_path.write_text(all_text)
            except OSError as exc:
                console.print()
                console.print(
                    status_line(f"Could not write to {export_path}: {exc}", accent="amber")
                )
                raise typer.Exit(1) from exc
            console.print()
            console.print(status_line(f"Prompt exported to {export_path}", accent="aqua"))

        raise typer.Exit()

    if verbose:
        total_chars = sum(len(prompt) for _, _, prompt in phase_prompts)
        n = len(phase_prompts)
        console.print(
            status_line(
                f"Total prompt length: {total_chars} chars across {n} phase(s)",
                accent="violet",
            )
        )

    # --- Copy media assets before AI runs (so the AI can see them) ---
    if answers.get("media_assets_manifest") and media_source_dir:
        copy_result = copy_assets(media_source_dir, project_dir, answers["stack"])
        if copy_result.copied:
            console.print(
                status_line(
                    f"Copied {copy_result.copied} media assets to {copy_result.target_dir}",
                    accent="aqua",
                )
            )
        for warning in copy_result.warnings:
            console.print(f"[yellow]{warning}[/yellow]")

    # --- Execute phases: serial first, parallel middle, serial last ---
    total_phases = len(phase_backends)
    step = 1

    # Step 1: Run architecture (serial)
    for phase, backend in serial_first:
        label = PHASE_LABELS.get(phase, phase)
        console.print()
        console.print(
            make_step_panel(step, total_phases, label, detail=f"backend: {backend}", accent="aqua")
        )
        phase_prompt = next(p for ph, _, p in phase_prompts if ph == phase)
        effective_model = model or backend_models.get(backend)
        returncode = run_ai(
            backend,
            phase_prompt,
            project_dir,
            model=effective_model,
            verbose=verbose,
            label=label,
        )
        if returncode != 0:
            _render_phase_failure(backend, label, returncode)
            raise typer.Exit(returncode)
        step += 1

    # Step 2: Run middle phases (parallel if multiple, serial if single)
    if parallel_middle:
        if can_parallel:
            labels = " + ".join(f"{PHASE_LABELS.get(p, p)} ({b})" for p, b in parallel_middle)
            console.print()
            console.print(
                make_step_panel(
                    step,
                    total_phases,
                    "Parallel execution window",
                    detail=labels,
                    accent="amber",
                )
            )

            parallel_args = []
            for phase, backend in parallel_middle:
                phase_prompt = next(p for ph, _, p in phase_prompts if ph == phase)
                effective_model = model or backend_models.get(backend)
                parallel_args.append(
                    {
                        "label": PHASE_LABELS.get(phase, phase),
                        "backend": backend,
                        "prompt": phase_prompt,
                        "model": effective_model,
                    }
                )

            results = run_ai_parallel(parallel_args, project_dir, verbose=verbose)
            for label, returncode in results:
                if returncode != 0:
                    _render_phase_failure("parallel backend", label, returncode)
                    raise typer.Exit(returncode)
            step += len(parallel_middle)
        else:
            for phase, backend in parallel_middle:
                label = PHASE_LABELS.get(phase, phase)
                console.print()
                console.print(
                    make_step_panel(
                        step, total_phases, label, detail=f"backend: {backend}", accent="violet"
                    )
                )
                phase_prompt = next(p for ph, _, p in phase_prompts if ph == phase)
                effective_model = model or backend_models.get(backend)
                returncode = run_ai(
                    backend,
                    phase_prompt,
                    project_dir,
                    model=effective_model,
                    verbose=verbose,
                    label=label,
                )
                if returncode != 0:
                    _render_phase_failure(backend, label, returncode)
                    raise typer.Exit(returncode)
                step += 1

    # Step 3: Run verify (serial)
    for phase, backend in serial_last:
        label = PHASE_LABELS.get(phase, phase)
        console.print()
        console.print(
            make_step_panel(step, total_phases, label, detail=f"backend: {backend}", accent="plum")
        )
        phase_prompt = next(p for ph, _, p in phase_prompts if ph == phase)
        effective_model = model or backend_models.get(backend)
        returncode = run_ai(
            backend,
            phase_prompt,
            project_dir,
            model=effective_model,
            verbose=verbose,
            label=label,
        )
        if returncode != 0:
            _render_phase_failure(backend, label, returncode)
            raise typer.Exit(returncode)
        step += 1

    # Post-scaffold: manifest, log, git init, verify, hooks, and open editor
    write_scaffold_manifest(
        answers,
        phase_backends,
        project_dir,
        conventions,
        model_override=model,
        backend_models=backend_models,
    )

    git_ok = ensure_git_init(project_dir)

    if verify:
        report = verify_scaffold(answers["stack"], project_dir, verbose=verbose)
        print_report(report, console)
        if not report.all_passed:
            _render_verification_guidance(project_dir)

    run_post_scaffold_hook(project_dir, answers)
    append_scaffold_log(answers, phase_backends, project_dir)

    console.print()
    _render_completion(project_dir, git_ok=git_ok)
    console.print()
    _render_next_steps(answers, project_dir, open_editor=open_editor)

    if open_editor:
        preferred = forge_config.get("preferred_editor", "")
        open_in_editor(project_dir, preferred_editor=preferred)
