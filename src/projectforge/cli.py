"""ProjectForge CLI — entry point."""

import os
import re
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import questionary
import typer
from rich.text import Text

from projectforge import __version__
from projectforge.card import inject_badge_into_readme, write_card
from projectforge.checks import CheckResult, detect_stack, generate_fix, run_checks
from projectforge.config import (
    SUPPORTED_BACKENDS,
    BackendStatus,
    check_backend_installed,
    get_backend_statuses,
    normalize_legacy_backend,
)
from projectforge.convention_admin import (
    list_scopes,
    render_bundle_preview,
    render_history_result,
    render_record_summary,
    render_validation_summary,
    resolve_open_path,
)
from projectforge.convention_history import load_history
from projectforge.convention_models import CompiledBundle, ConventionValidationError
from projectforge.convention_profiles import (
    import_profile,
    initialize_profile,
    list_profiles,
    profile_path,
)
from projectforge.conventions import (
    build_registry,
    load_bundled_conventions,
    load_claude_md_template,
    load_conventions,
    load_conventions_bundle,
)
from projectforge.dashboard import render_dashboard
from projectforge.design_templates import (
    DESIGN_TEMPLATE_OPTIONS,
    design_template_ids_for_stack,
    design_template_supported_for_stack,
    load_design_template,
)
from projectforge.doctor import build_doctor_report, doctor_exit_code
from projectforge.evolutions import build_evolve_prompt, get_capabilities, get_capability
from projectforge.execution_policy import validate_approval_mode
from projectforge.execution_state import ProgressContractError, initialize_progress, mark_phase
from projectforge.logo import print_logo
from projectforge.media_assets import (
    MEDIA_DIR,
    build_asset_manifest,
    copy_assets,
    list_collections,
    scan_assets,
    target_asset_dir,
)
from projectforge.preferences import record_preferences
from projectforge.prompt_builder import build_phase_prompt
from projectforge.prompts import collect_answers
from projectforge.quality import append_quality_signal, compute_backend_scores, read_quality_signals
from projectforge.questionary_theme import prompt_confirm, prompt_select, prompt_text
from projectforge.router import (
    PHASE_ARCHITECTURE,
    PHASE_LABELS,
    PHASE_VERIFY,
    STACK_PHASES,
    merge_adjacent_phases,
    pick_phase_backends,
)
from projectforge.runner import (
    ensure_git_init,
    open_in_editor,
    reset_project_dir,
    run_ai,
    run_ai_parallel,
    run_post_scaffold_hook,
)
from projectforge.safety import check_for_secrets
from projectforge.scaffold_log import (
    SCAFFOLD_LOG_PATH,
    append_scaffold_log,
    latest_scaffold_duration,
    write_scaffold_manifest,
)
from projectforge.scaffold_options import (
    AUTH_PROVIDER_OPTIONS,
    CI_TEMPLATE_MODES,
    auth_provider_ids_for_stack,
    auth_provider_supported_for_stack,
    ci_action_ids_for_stack,
)
from projectforge.setup import load_forge_config, needs_setup, run_setup, save_forge_config
from projectforge.sound import play_completion_sound
from projectforge.ui import (
    ACCENTS,
    BACKEND_ACCENTS,
    TEXT_MUTED,
    TEXT_SECONDARY,
    bullet,
    create_console,
    grouped_lines,
    header_panel,
    make_file_tree,
    make_panel,
    make_step_panel,
    muted,
    path_text,
    status_line,
    subtle,
)
from projectforge.verify import verify_scaffold, write_verification_report

app = typer.Typer()
admin_app = typer.Typer(help="Repo admin tools.")
conventions_app = typer.Typer(help="Manage user-owned convention profiles.")
app.add_typer(admin_app, name="admin")
app.add_typer(conventions_app, name="conventions")
console = create_console()

_PROJECT_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
_TOP_LEVEL_CONVENTION_HISTORY_TARGETS = {
    "conventions",
    "global",
    "languages",
    "stacks",
    "prompts",
    "manifests",
}
_BACKEND_LOGIN_COMMANDS = {
    "claude": "claude auth login",
    "antigravity": "agy and complete Google Sign-In",
    "codex": "codex login",
}
_PROVIDER_QUOTA_NOTES = {
    "claude": "Claude Code plan limits or configured API billing",
    "antigravity": "Google account plan and Antigravity quota",
    "codex": "ChatGPT/Codex plan limits or configured API billing",
}
_FORGE_RUNTIME_BOUNDARY = """

<forge_runtime_boundary>
Do not read, edit, delete, or replace `.forge/progress.json`; ProjectForge owns that runtime
evidence file. Preserve existing project output from earlier phases.
</forge_runtime_boundary>"""


def _validate_backend_override(backend: str | None) -> None:
    """Reject retired or unknown explicit backend names with migration guidance."""
    if backend is None:
        return
    if backend == "gemini":
        console.print(
            "[red]The Gemini CLI backend was removed. Install Google Antigravity CLI and "
            "use --use antigravity.[/red]"
        )
        raise typer.Exit(1)
    if backend not in SUPPORTED_BACKENDS:
        backends = ", ".join(SUPPORTED_BACKENDS)
        console.print(f"[red]Unknown backend '{backend}'. Choose from: {backends}[/red]")
        raise typer.Exit(1)


@app.command()
def doctor(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit deterministic machine-readable diagnostics."),
    ] = False,
) -> None:
    """Check configuration, provider installation, and authentication without model calls."""
    import json

    report = build_doctor_report()
    if json_output:
        console.print_json(json.dumps(report))
    else:
        console.print(header_panel(__version__))
        config_status = report["config"]["status"]
        console.print(status_line(f"Configuration: {config_status}", accent="violet"))
        environment = report["environment"]
        console.print(
            status_line(
                f"Python: {environment['python']['version']} "
                f"({'supported' if environment['python']['supported'] else 'unsupported'})",
                accent="aqua" if environment["python"]["supported"] else "amber",
            )
        )
        for tool in ("git", "docker"):
            tool_status = environment[tool]
            label = tool_status["version"] or (
                "installed" if tool_status["installed"] else "not installed"
            )
            console.print(status_line(f"{tool}: {label}", accent="violet"))
        installed_editors = [
            editor for editor, installed in environment["editors"].items() if installed
        ]
        editor_label = ", ".join(installed_editors)
        if not editor_label:
            editor_label = "no editor CLI on PATH — set one with `projectforge --setup`"
        console.print(status_line(f"Editors: {editor_label}", accent="violet"))
        for backend, provider in report["providers"].items():
            version = f" ({provider['version']})" if provider["version"] else ""
            console.print(
                status_line(
                    f"{backend}: {provider['readiness']}{version}",
                    accent="aqua" if provider["readiness"] == "ready" else "amber",
                )
            )
            model_behavior = provider["model_behavior"]
            model_label = (
                f"override {model_behavior['value']}"
                if model_behavior["mode"] == "override"
                else "provider default"
            )
            console.print(muted(f"  model: {model_label}"))
            if provider.get("auth_mode"):
                console.print(muted(f"  authentication mode: {provider['auth_mode']}"))
            if provider["readiness"] != "ready":
                check = provider.get("check", {})
                if check.get("command"):
                    console.print(muted(f"  check: {check['command']}"))
                if check.get("observed"):
                    console.print(muted(f"  observed: {check['observed']}"))
                console.print(muted(f"  next: {provider['repair']}"))
    exit_code = doctor_exit_code(report)
    if exit_code:
        raise typer.Exit(exit_code)


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
    approval_mode: str,
    conventions: str,
    claude_md_loaded: bool,
    design_template_label: str | None,
    media_collection: str | None = None,
    media_asset_count: int = 0,
    convention_sources: tuple = (),
    verbose: bool = False,
) -> None:
    """Render loaded scaffold context."""
    lines: list[Text] = []
    for backend in sorted(required_backends):
        configured_model = model_override or backend_models.get(backend)
        lines.append(subtle(f"{backend} model: {configured_model or 'provider default'}"))
    lines.append(subtle(f"Approval mode: {approval_mode}"))

    source_label = "source" if len(convention_sources) == 1 else "sources"
    lines.append(
        subtle(
            f"Conventions: {len(convention_sources)} {source_label}, "
            f"{len(conventions):,} chars (hashes recorded)"
        )
    )
    if verbose:
        for source in convention_sources:
            lines.append(muted(f"  {source.source_id}: {source.display_path} ({source.sha256})"))
    if claude_md_loaded:
        lines.append(subtle("CLAUDE.md starter loaded"))
    if design_template_label:
        lines.append(subtle(f"Design template: {design_template_label}"))
    if media_collection and media_asset_count:
        lines.append(subtle(f"Media: {media_asset_count} files from {media_collection}/"))

    console.print(make_panel(grouped_lines(lines), title="Scaffold Context", accent="aqua"))


def _format_duration(seconds: float) -> str:
    """Format a measured duration for compact preflight display."""
    total_seconds = max(0, round(seconds))
    minutes, remaining_seconds = divmod(total_seconds, 60)
    if minutes:
        return f"{minutes}m {remaining_seconds:02d}s"
    return f"{remaining_seconds}s"


def _provider_commitment_lines(
    phase_backends: list[tuple[str, str]],
    completed_phases: set[str],
    *,
    agents: bool,
) -> list[Text]:
    """Return numeric provider usage and cost caveats for execution preflight."""
    phases_by_backend: dict[str, int] = {}
    for phase, backend in phase_backends:
        if phase not in completed_phases:
            phases_by_backend[backend] = phases_by_backend.get(backend, 0) + 1

    lines: list[Text] = []
    for backend in sorted(phases_by_backend):
        phase_count = phases_by_backend[backend]
        if agents:
            invocation_count = f"typically {phase_count * 4}-{phase_count * 8}"
        else:
            invocation_count = str(phase_count)
        lines.append(
            subtle(
                f"{backend} usage: {invocation_count} provider CLI invocation(s); "
                f"{_PROVIDER_QUOTA_NOTES[backend]}; rough cost: $0 on an included plan or "
                "~$1-$20+ when usage-billed"
            )
        )
    lines.append(
        muted(
            "These are order-of-magnitude planning ranges, not quotes; Forge cannot see "
            "provider tokens, plan limits, or current rates."
        )
    )
    return lines


def _backend_help_line(backend: str, status: BackendStatus) -> Text:
    """Return a user-facing readiness line for a backend."""
    if status.ready is False:
        login_command = status.login_command or _BACKEND_LOGIN_COMMANDS.get(backend, backend)
        return subtle(f"{backend} needs login. Run {login_command}.")
    if not status.installed:
        return subtle(f"{backend} is not installed or not on PATH.")
    return subtle(
        f"{backend} is installed but Forge could not confirm authentication. "
        "Run forge doctor for the recommended next step."
    )


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
        subtle("Partial project output and .forge/progress.json were preserved."),
        subtle("Fix the reported provider issue, then repeat the same command with --resume."),
        muted("Resume verifies the original contract and does not rerun completed phases."),
    ]
    console.print(make_panel(grouped_lines(lines), title="Execution", accent="amber"))


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
            bool(kwargs.get("resume")),
        ]
    )


def _prompt_post_setup_next_step() -> str:
    """Ask a first-run user what they want to do after setup completes."""
    from projectforge.config import get_usable_backends

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
    choices.extend(
        [
            questionary.Choice("Review setup again", value="setup"),
            questionary.Choice("Exit for now", value="exit"),
        ]
    )

    action = prompt_select(
        "What would you like to do next?",
        choices=choices,
        default="create" if has_usable else "exit",
    ).ask()
    if action is None:
        raise typer.Exit()
    return action


def _admin_history_target(value: str) -> str:
    cleaned = value.strip().strip("/")
    if not cleaned:
        raise ConventionValidationError("A stack id or conventions path is required for history.")
    if (
        "/" in cleaned
        or cleaned.endswith(".md")
        or cleaned in _TOP_LEVEL_CONVENTION_HISTORY_TARGETS
    ):
        return cleaned
    return f"stacks/{cleaned}"


def _run_conventions_browse(registry) -> None:
    scopes = list_scopes(registry)
    scope_choice = prompt_select(
        "Choose a conventions scope",
        choices=[
            questionary.Choice(f"{scope.label} ({len(scope.items)})", value=scope.name)
            for scope in scopes
        ],
        default="stack",
    ).ask()
    if scope_choice is None:
        raise typer.Exit(0)

    selected_scope = next(scope for scope in scopes if scope.name == scope_choice)
    if not selected_scope.items:
        console.print(status_line(f"No entries found for {scope_choice}.", accent="amber"))
        raise typer.Exit(0)

    item_choice = prompt_select(
        f"Choose a {selected_scope.name} entry",
        choices=[
            questionary.Choice(f"{item.key} — {item.label}", value=item.target)
            for item in selected_scope.items
        ],
        default=selected_scope.items[0].target,
    ).ask()
    if item_choice is None:
        raise typer.Exit(0)

    if selected_scope.name == "prompt":
        stack = None if item_choice == "default" else item_choice
        console.print(render_bundle_preview(registry, stack))
        return

    console.print(render_record_summary(registry, item_choice))


def _run_admin_conventions_interactive(registry) -> None:
    action = prompt_select(
        "Conventions admin",
        choices=[
            questionary.Choice("Validate bundled conventions", value="validate"),
            questionary.Choice("Browse convention scopes", value="browse"),
            questionary.Choice("Preview a compiled stack bundle", value="preview"),
            questionary.Choice("Show git history for a stack", value="history"),
            questionary.Choice("Resolve a markdown file to edit", value="open"),
        ],
        default="browse",
    ).ask()
    if action is None:
        raise typer.Exit(0)

    if action == "validate":
        console.print(render_validation_summary(registry))
        return
    if action == "browse":
        _run_conventions_browse(registry)
        return
    if action == "preview":
        stack_choice = prompt_select(
            "Choose a stack",
            choices=[
                questionary.Choice(stack_id, value=stack_id)
                for stack_id in sorted(registry.stack_record_ids)
            ],
            default="fastapi" if "fastapi" in registry.stack_record_ids else None,
        ).ask()
        if stack_choice is None:
            raise typer.Exit(0)
        console.print(render_bundle_preview(registry, stack_choice))
        return
    if action == "history":
        stack_choice = prompt_select(
            "Choose a stack",
            choices=[
                questionary.Choice(stack_id, value=stack_id)
                for stack_id in sorted(registry.stack_record_ids)
            ],
            default="fastapi" if "fastapi" in registry.stack_record_ids else None,
        ).ask()
        if stack_choice is None:
            raise typer.Exit(0)
        console.print(render_history_result(load_history(registry.root, f"stacks/{stack_choice}")))
        return

    open_target = prompt_text(
        "Markdown path to open",
        default="global/shared.md",
    ).ask()
    if open_target is None:
        raise typer.Exit(0)
    resolved_path = resolve_open_path(registry.root, open_target)
    console.print(make_panel(path_text(resolved_path), title="Open Markdown", accent="plum"))


def _selected_conventions_profile() -> str:
    """Return the configured profile without exposing other config values."""
    return load_forge_config().get("conventions_profile", "default")


@conventions_app.command("init")
def conventions_init(
    name: Annotated[str, typer.Argument(help="Profile name.")] = "default",
) -> None:
    """Create a starter convention profile without overwriting existing work."""
    try:
        path = initialize_profile(name)
    except ConventionValidationError as exc:
        console.print(status_line(str(exc), accent="amber"))
        raise typer.Exit(1) from exc
    console.print(status_line(f"Created convention profile: {path}", accent="aqua"))


@conventions_app.command("import")
def conventions_import(
    source: Annotated[Path, typer.Argument(help="Markdown instruction file to import.")],
    name: Annotated[
        str | None,
        typer.Option("--name", help="Destination profile name; defaults to the source stem."),
    ] = None,
) -> None:
    """Import AGENTS.md, CLAUDE.md, or another Markdown file as a new profile."""
    try:
        path = import_profile(source, name or source.stem)
    except ConventionValidationError as exc:
        console.print(status_line(str(exc), accent="amber"))
        raise typer.Exit(1) from exc
    console.print(status_line(f"Imported convention profile: {path}", accent="aqua"))


@conventions_app.command("list")
def conventions_list() -> None:
    """List profiles and show the selected profile."""
    selected = _selected_conventions_profile()
    profiles = list_profiles()
    if not profiles:
        console.print(status_line("No profiles found. Run forge conventions init.", accent="amber"))
        return
    for name in profiles:
        marker = " (selected)" if name == selected else ""
        console.print(status_line(f"{name}{marker}", accent="aqua"))


@conventions_app.command("select")
def conventions_select(
    name: Annotated[str, typer.Argument(help="Existing profile name.")],
) -> None:
    """Select the profile used for future scaffolds."""
    try:
        path = profile_path(name)
    except ConventionValidationError as exc:
        console.print(status_line(str(exc), accent="amber"))
        raise typer.Exit(1) from exc
    if not path.exists():
        console.print(status_line(f"Convention profile not found: {name}", accent="amber"))
        raise typer.Exit(1)
    config = load_forge_config()
    config["conventions_profile"] = name
    save_forge_config(config)
    console.print(status_line(f"Selected convention profile: {name}", accent="aqua"))


def _conventions_inspection(stack: str | None) -> tuple[str, CompiledBundle, dict]:
    profile = _selected_conventions_profile()
    bundle = load_conventions_bundle(stack=stack, profile=profile)
    report = {
        "profile": profile,
        "stack": stack,
        "bundle_id": bundle.bundle_id,
        "warnings": list(bundle.warnings),
        "sources": [
            {
                "source_id": source.source_id,
                "path": source.display_path,
                "sha256": source.sha256,
            }
            for source in bundle.contributions
        ],
    }
    return profile, bundle, report


@conventions_app.command("inspect")
def conventions_inspect(
    stack: Annotated[
        str | None,
        typer.Option("--stack", help="Stack whose effective bundle should be inspected."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable source metadata."),
    ] = False,
) -> None:
    """Inspect effective source order, paths, warnings, and hashes."""
    import json

    try:
        profile, bundle, report = _conventions_inspection(stack)
    except ConventionValidationError as exc:
        console.print(status_line(str(exc), accent="amber"))
        raise typer.Exit(1) from exc
    if json_output:
        console.print_json(json.dumps(report))
        return
    console.print(status_line(f"Profile: {profile}; bundle: {bundle.bundle_id}", accent="aqua"))
    for source in bundle.contributions:
        console.print(muted(f"{source.source_id}: {source.display_path} ({source.sha256})"))
    for warning in bundle.warnings:
        console.print(status_line(f"Warning: {warning}", accent="amber"))


@conventions_app.command("preview")
def conventions_preview(
    stack: Annotated[str | None, typer.Option("--stack", help="Stack to preview.")] = None,
) -> None:
    """Print the effective conventions content without starting a provider."""
    try:
        _, bundle, _ = _conventions_inspection(stack)
    except ConventionValidationError as exc:
        console.print(status_line(str(exc), accent="amber"))
        raise typer.Exit(1) from exc
    console.print(bundle.prompt_block)


@conventions_app.command("validate")
def conventions_validate(
    stack: Annotated[str | None, typer.Option("--stack", help="Stack to validate.")] = None,
) -> None:
    """Validate the selected profile and its effective bundle."""
    try:
        profile, bundle, _ = _conventions_inspection(stack)
    except ConventionValidationError as exc:
        console.print(status_line(str(exc), accent="amber"))
        raise typer.Exit(1) from exc
    secret_types = check_for_secrets(bundle.prompt_block)
    if secret_types:
        console.print(
            status_line(
                f"Validation failed: credential-like content ({', '.join(secret_types)}).",
                accent="amber",
            )
        )
        raise typer.Exit(1)
    console.print(status_line(f"Validation passed for profile {profile}.", accent="aqua"))


@conventions_app.command("edit")
def conventions_edit(
    name: Annotated[str | None, typer.Argument(help="Profile name; defaults to selected.")] = None,
) -> None:
    """Open a profile in the configured editor."""
    profile = name or _selected_conventions_profile()
    try:
        path = profile_path(profile)
    except ConventionValidationError as exc:
        console.print(status_line(str(exc), accent="amber"))
        raise typer.Exit(1) from exc
    if not path.exists():
        console.print(status_line(f"Convention profile not found: {profile}", accent="amber"))
        raise typer.Exit(1)
    configured = load_forge_config().get("preferred_editor", "")
    editor = configured or os.environ.get("EDITOR", "")
    executable = shutil.which(editor) if editor else None
    if not executable:
        console.print(
            status_line(
                "No configured editor command found. Set one with forge --setup or $EDITOR.",
                accent="amber",
            )
        )
        raise typer.Exit(1)
    result = subprocess.run([executable, str(path)], check=False)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)


@admin_app.command("conventions")
def admin_conventions(
    validate: Annotated[
        bool,
        typer.Option("--validate", help="Validate the bundled conventions registry."),
    ] = False,
    preview_stack: Annotated[
        str | None,
        typer.Option("--preview-stack", help="Preview the compiled bundle for a stack."),
    ] = None,
    history: Annotated[
        str | None,
        typer.Option("--history", help="Show git history for a stack id or conventions path."),
    ] = None,
    open_path: Annotated[
        str | None,
        typer.Option("--open", help="Resolve a markdown path under conventions/."),
    ] = None,
) -> None:
    """Browse, validate, preview, and inspect bundled conventions."""

    direct_actions = [
        validate,
        preview_stack is not None,
        history is not None,
        open_path is not None,
    ]
    if sum(1 for action in direct_actions if action) > 1:
        console.print(status_line("Choose only one direct admin action at a time.", accent="amber"))
        raise typer.Exit(1)

    try:
        registry = build_registry()
        if validate:
            console.print(render_validation_summary(registry))
            return
        if preview_stack is not None:
            console.print(render_bundle_preview(registry, preview_stack))
            return
        if history is not None:
            history_result = load_history(registry.root, _admin_history_target(history))
            console.print(render_history_result(history_result))
            return
        if open_path is not None:
            resolved_path = resolve_open_path(registry.root, open_path)
            console.print(
                make_panel(path_text(resolved_path), title="Open Markdown", accent="plum")
            )
            return
        _run_admin_conventions_interactive(registry)
    except ConventionValidationError as exc:
        console.print(status_line(f"Conventions error: {exc}", accent="amber"))
        raise typer.Exit(1) from exc


@app.command()
def stats(
    repair: Annotated[
        bool,
        typer.Option(
            "--repair",
            help="Quarantine recognizable pytest artifacts before showing stats.",
        ),
    ] = False,
) -> None:
    """Show scaffold analytics and backend performance."""
    import json

    from projectforge.analytics import aggregate_stats, render_stats
    from projectforge.history import repair_history
    from projectforge.quality import QUALITY_LOG_PATH, read_quality_signals

    if repair:
        repair_result = repair_history(
            scaffold_log_path=SCAFFOLD_LOG_PATH,
            quality_log_path=QUALITY_LOG_PATH,
        )
        if repair_result.total_entries:
            console.print(
                status_line(
                    f"Quarantined {repair_result.scaffold_entries} scaffold and "
                    f"{repair_result.quality_entries} quality entries at "
                    f"{repair_result.quarantine_dir}.",
                    accent="aqua",
                )
            )
        else:
            console.print(status_line("No recognizable pytest history found.", accent="aqua"))

    scaffold_entries: list[dict] = []
    if SCAFFOLD_LOG_PATH.exists():
        for line in SCAFFOLD_LOG_PATH.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    scaffold_entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    quality_entries = read_quality_signals()

    stats_data = aggregate_stats(
        scaffold_entries=scaffold_entries,
        quality_entries=quality_entries,
    )
    render_stats(console, stats_data)


@app.command()
def evolve(
    capability: Annotated[
        str | None,
        typer.Argument(help="Capability to add (e.g., auth, websockets, stripe)."),
    ] = None,
    use: Annotated[
        str | None,
        typer.Option("--use", help="Override AI routing (claude, antigravity, or codex)."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", "-m", help="Model to pass to the AI CLI."),
    ] = None,
    approval_mode: Annotated[
        str,
        typer.Option("--approval-mode", help="Execution mode: safe, plan, or unsafe."),
    ] = "safe",
    allow_unsafe: Annotated[
        bool,
        typer.Option("--allow-unsafe", help="Confirm provider bypass/yolo execution."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show detailed execution info."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print the prompt without executing."),
    ] = False,
) -> None:
    """Add a capability to an existing Forge project."""
    import json

    try:
        validate_approval_mode(
            approval_mode,
            allow_unsafe=allow_unsafe or dry_run,
        )
    except ValueError as exc:
        console.print(status_line(str(exc), accent="amber"))
        raise typer.Exit(1) from exc
    _validate_backend_override(use)

    project_dir = Path.cwd()
    manifest_path = project_dir / ".forge" / "scaffold.json"

    if not manifest_path.exists():
        console.print(
            status_line(
                "No .forge/scaffold.json found. Run this inside a Forge project.",
                accent="amber",
            )
        )
        raise typer.Exit(1)

    dna = json.loads(manifest_path.read_text())
    stack = dna.get("stack", "")

    print_logo(console)
    console.print(header_panel(__version__))
    console.print(
        status_line(f"Project: {dna.get('name', project_dir.name)} ({stack})", accent="violet")
    )

    caps = get_capabilities(stack)
    if not caps:
        console.print(
            status_line(
                f"No evolution capabilities defined for stack '{stack}'.",
                accent="amber",
            )
        )
        raise typer.Exit(1)

    # Select capability
    if capability:
        cap = get_capability(stack, capability)
        if not cap:
            valid = ", ".join(c["name"] for c in caps)
            console.print(
                status_line(
                    f"Unknown capability '{capability}'. Choose from: {valid}",
                    accent="amber",
                )
            )
            raise typer.Exit(1)
    else:
        choices = [
            questionary.Choice(f"{c['name']} — {c['description']}", value=c["name"]) for c in caps
        ]
        selected = prompt_select("What would you like to add?", choices=choices).ask()
        if selected is None:
            raise typer.Exit(0)
        cap = get_capability(stack, selected)

    prompt = build_evolve_prompt(project_dir, cap)

    if dry_run:
        console.print(prompt)
        raise typer.Exit(0)

    # Route through standard backend routing (or --use override)
    if use:
        backend = use
        if not check_backend_installed(backend):
            console.print(status_line(f"{backend} is not installed.", accent="amber"))
            raise typer.Exit(1)
    else:
        phase_plan = pick_phase_backends(stack, override=None)
        backend = phase_plan[0][1] if phase_plan else "claude"

    console.print(status_line(f"Adding {cap['name']} via {backend}...", accent="violet"))

    returncode = run_ai(
        backend,
        prompt,
        project_dir,
        model=model,
        verbose=verbose,
        label=f"Evolve: {cap['name']}",
        approval_mode=approval_mode,
        allow_unsafe=allow_unsafe,
    )

    if returncode == 0:
        evolutions = dna.get("evolutions", [])
        evolutions.append(
            {
                "capability": cap["name"],
                "backend": backend,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        dna["evolutions"] = evolutions
        manifest_path.write_text(json.dumps(dna, indent=2) + "\n")
        console.print(status_line(f"Successfully added {cap['name']}", accent="aqua"))
    else:
        console.print(
            status_line(
                f"Evolution failed (exit {returncode}). Try --verbose for details.",
                accent="amber",
            )
        )
        raise typer.Exit(returncode)


@app.command()
def check(
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Auto-generate missing fixable files."),
    ] = False,
    export: Annotated[
        str | None,
        typer.Option("--export", help="Export the report to a markdown file."),
    ] = None,
) -> None:
    """Audit a project against organization conventions."""
    project_dir = Path.cwd()
    stack = detect_stack(project_dir)

    console.print(header_panel(__version__))
    console.print(status_line(f"Checking: {project_dir.name} ({stack})", accent="violet"))
    console.print()

    results = run_checks(project_dir)

    passed = [r for r in results if r.passed]
    warnings = [r for r in results if not r.passed and r.severity == "warn"]
    failed = [r for r in results if not r.passed and r.severity == "fail"]

    # Group by category
    categories: dict[str, list[CheckResult]] = {}
    for r in results:
        categories.setdefault(r.category, []).append(r)

    for category, checks in sorted(categories.items()):
        console.print(muted(f"  {category.upper()}"))
        for c in checks:
            if c.passed:
                icon = f"[{ACCENTS['aqua']}]✓[/]"
                text = f"[{TEXT_SECONDARY}]{c.name}[/]"
            elif c.severity == "warn":
                icon = f"[{ACCENTS['amber']}]![/]"
                text = f"[{ACCENTS['amber']}]{c.detail or c.name}[/]"
            else:
                icon = f"[{ACCENTS['plum']}]✗[/]"
                text = f"[{ACCENTS['plum']}]{c.detail or c.name}[/]"
            console.print(f"  {icon} {text}")
        console.print()

    # Summary line
    summary = Text("  ")
    summary.append(str(len(passed)), style=f"bold {ACCENTS['aqua']}")
    summary.append(" passed  ", style=TEXT_MUTED)
    if warnings:
        summary.append(str(len(warnings)), style=f"bold {ACCENTS['amber']}")
        summary.append(" warnings  ", style=TEXT_MUTED)
    if failed:
        summary.append(str(len(failed)), style=f"bold {ACCENTS['plum']}")
        summary.append(" failed", style=TEXT_MUTED)
    console.print(summary)

    # Fix mode
    if fix:
        fixable = [r for r in results if r.fixable and not r.passed]
        if fixable:
            console.print()
            for c in fixable:
                if generate_fix(project_dir, c):
                    console.print(status_line(f"Created {c.name}", accent="aqua"))
        else:
            console.print(status_line("Nothing to fix automatically.", accent="amber"))

    # Export mode
    if export:
        lines = [f"# Convention Audit — {project_dir.name}\n"]
        lines.append(f"Stack: {stack}\n")
        for category, checks in sorted(categories.items()):
            lines.append(f"\n## {category.title()}\n")
            for c in checks:
                icon = "✓" if c.passed else ("!" if c.severity == "warn" else "✗")
                lines.append(f"- {icon} {c.name}{': ' + c.detail if c.detail else ''}")
        summary_text = f"{len(passed)} passed, {len(warnings)} warnings, {len(failed)} failed"
        lines.append(f"\n---\n{summary_text}\n")
        Path(export).write_text("\n".join(lines))
        console.print(status_line(f"Report exported to {export}", accent="aqua"))

    if fix:
        console.print(status_line("Run forge check again to verify fixes.", accent="violet"))


@app.command()
def replay(
    diff: Annotated[
        bool,
        typer.Option("--diff", help="Compare replay output against current project."),
    ] = False,
    use: Annotated[
        str | None,
        typer.Option("--use", help="Override AI routing (claude, antigravity, or codex)."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", "-m", help="Model to pass to the AI CLI."),
    ] = None,
    approval_mode: Annotated[
        str,
        typer.Option("--approval-mode", help="Execution mode: safe, plan, or unsafe."),
    ] = "safe",
    allow_unsafe: Annotated[
        bool,
        typer.Option("--allow-unsafe", help="Confirm provider bypass/yolo execution."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show detailed execution info."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print the reconstructed prompt without executing."),
    ] = False,
) -> None:
    """Replay a scaffold using the project's original inputs."""
    import json
    import tempfile

    try:
        validate_approval_mode(
            approval_mode,
            allow_unsafe=allow_unsafe or dry_run,
        )
    except ValueError as exc:
        console.print(status_line(str(exc), accent="amber"))
        raise typer.Exit(1) from exc
    _validate_backend_override(use)

    project_dir = Path.cwd()
    manifest_path = project_dir / ".forge" / "scaffold.json"

    if not manifest_path.exists():
        console.print(
            status_line(
                "No .forge/scaffold.json found. Run this inside a Forge project.",
                accent="amber",
            )
        )
        raise typer.Exit(1)

    dna = json.loads(manifest_path.read_text())
    stack = dna.get("stack", "")
    name = dna.get("name", project_dir.name)

    console.print(header_panel(__version__))
    console.print(status_line(f"Replaying: {name} ({stack})", accent="violet"))

    # Load conventions snapshot or current bundled conventions for the stack
    snapshot_path = project_dir / ".forge" / "conventions-snapshot.md"
    if snapshot_path.exists():
        conventions = snapshot_path.read_text()
    else:
        replay_stack = stack or None
        loaded_stack = replay_stack
        try:
            conventions, conv_warnings = load_bundled_conventions(stack=replay_stack)
        except ConventionValidationError as exc:
            if replay_stack and str(exc) == f"Unknown convention record: stacks/{replay_stack}":
                console.print(
                    status_line(
                        (
                            f"Unknown stack '{replay_stack}' in replay manifest; "
                            "falling back to current bundled conventions."
                        ),
                        accent="amber",
                    )
                )
                loaded_stack = None
                try:
                    conventions, conv_warnings = load_bundled_conventions()
                except ConventionValidationError as fallback_exc:
                    console.print(status_line(f"Conventions error: {fallback_exc}", accent="amber"))
                    raise typer.Exit(1) from fallback_exc
            else:
                console.print(status_line(f"Conventions error: {exc}", accent="amber"))
                raise typer.Exit(1) from exc
        for warning in conv_warnings:
            console.print(f"[yellow]{warning}[/yellow]")
        console.print(
            status_line(
                (
                    f"No conventions snapshot found. Using current bundled conventions "
                    f"for stack '{loaded_stack}'."
                    if loaded_stack
                    else "No conventions snapshot found. Using current conventions."
                ),
                accent="amber",
            )
        )

    # Reconstruct answers from manifest
    answers = {
        "name": name,
        "stack": stack,
        "description": dna.get("description", ""),
        "docker": "Dockerfile" in str(list(project_dir.rglob("Dockerfile"))),
        "design_template": dna.get("design_template"),
        "auth_provider": dna.get("auth_provider"),
        "demo_mode": dna.get("demo_mode", False),
        "extra": "",
        "services": [],
    }

    # Reconstruct phase backends from routing
    routing = dna.get("routing", [])
    phase_backends = [(r["phase"], normalize_legacy_backend(r["backend"])) for r in routing]

    if not phase_backends:
        phase_backends = pick_phase_backends(stack, override=use)

    # Check backend availability
    for _, backend in phase_backends:
        actual = use or backend
        if not check_backend_installed(actual):
            console.print(
                status_line(
                    f"{actual} is not installed. Results may differ from original scaffold.",
                    accent="amber",
                )
            )
            # Fall back to standard routing
            phase_backends = pick_phase_backends(stack, override=use)
            break

    # Build prompt
    all_phases = STACK_PHASES.get(stack, ["architecture", "tests"])
    phase_prompts = []
    merged = merge_adjacent_phases(phase_backends)
    for phases_group, backend in merged:
        prompt = build_phase_prompt(phases_group, all_phases, answers, conventions, backend=backend)
        phase_prompts.append((phases_group, backend, prompt))

    if dry_run:
        for phases_group, backend, prompt in phase_prompts:
            label = " + ".join(phases_group)
            console.print(f"\n--- {label} ({backend}) ---\n")
            console.print(prompt)
        raise typer.Exit(0)

    # Execute into temp directory
    replay_dir = Path(tempfile.mkdtemp(prefix=f"forge-replay-{name}-"))
    console.print(status_line(f"Replaying into {replay_dir}", accent="violet"))

    for phases_group, backend, prompt in phase_prompts:
        label = " + ".join(phases_group)
        effective_model = model or dna.get("backend_models", {}).get(backend)
        returncode = run_ai(
            backend,
            prompt,
            replay_dir,
            model=effective_model,
            verbose=verbose,
            label=label,
            approval_mode=approval_mode,
            allow_unsafe=allow_unsafe,
        )
        if returncode != 0:
            console.print(
                status_line(
                    f"Replay phase '{label}' failed (exit {returncode}).",
                    accent="amber",
                )
            )
            raise typer.Exit(returncode)

    console.print(status_line(f"Replay complete at {replay_dir}", accent="aqua"))

    # Diff mode
    if diff:
        import filecmp

        def _collect_diffs(dcmp, prefix=""):
            """Recursively collect diffs from a dircmp result."""
            added, removed, changed = [], [], []
            for f in dcmp.right_only:
                added.append(f"{prefix}{f}")
            for f in dcmp.left_only:
                removed.append(f"{prefix}{f}")
            for f in dcmp.diff_files:
                changed.append(f"{prefix}{f}")
            for subdir, sub_dcmp in dcmp.subdirs.items():
                a, r, c = _collect_diffs(sub_dcmp, prefix=f"{prefix}{subdir}/")
                added.extend(a)
                removed.extend(r)
                changed.extend(c)
            return added, removed, changed

        dcmp = filecmp.dircmp(
            str(project_dir),
            str(replay_dir),
            ignore=[".forge", ".git", "__pycache__", "node_modules", ".venv"],
        )
        added, removed, changed = _collect_diffs(dcmp)

        console.print()
        if added:
            for f in sorted(added):
                console.print(status_line(f"+ {f}", accent="aqua"))
        if changed:
            for f in sorted(changed):
                console.print(status_line(f"~ {f}", accent="amber"))
        if removed:
            for f in sorted(removed):
                console.print(status_line(f"- {f}", accent="plum"))

        if not added and not changed and not removed:
            console.print(status_line("No structural differences found.", accent="aqua"))

        # Save diff report
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        diff_file = project_dir / ".forge" / f"replay-diff-{date_str}.md"
        lines = [f"# Replay Diff — {name}\n"]
        if added:
            lines.append("\n## Added\n")
            lines.extend(f"- {f}" for f in sorted(added))
        if changed:
            lines.append("\n## Changed\n")
            lines.extend(f"- {f}" for f in sorted(changed))
        if removed:
            lines.append("\n## Removed\n")
            lines.extend(f"- {f}" for f in sorted(removed))
        diff_file.write_text("\n".join(lines) + "\n")
        console.print(status_line(f"Diff saved to {diff_file}", accent="aqua"))


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    use: Annotated[
        str | None,
        typer.Option("--use", help="Override AI routing (claude, antigravity, or codex)."),
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
    approval_mode: Annotated[
        str,
        typer.Option(
            "--approval-mode",
            help="Provider-neutral execution mode: safe, plan, or unsafe.",
        ),
    ] = "safe",
    allow_unsafe: Annotated[
        bool,
        typer.Option(
            "--allow-unsafe",
            help="Confirm blanket provider bypass/yolo execution for this run.",
        ),
    ] = False,
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
    agents: Annotated[
        bool | None,
        typer.Option(
            "--agents/--no-agents",
            help="Enable multi-agent orchestration (higher quality, slower).",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose/--quiet", help="Show detailed execution info and source hashes."),
    ] = False,
    open_editor: Annotated[
        bool,
        typer.Option("--open/--no-open", help="Open project in editor after scaffolding."),
    ] = True,
    verify: Annotated[
        bool,
        typer.Option("--verify/--no-verify", help="Run post-scaffold verification checks."),
    ] = True,
    resume: Annotated[
        bool,
        typer.Option(
            "--resume",
            help="Resume failure; preserve completed phases.",
        ),
    ] = False,
    export: Annotated[
        str | None,
        typer.Option("--export", help="Export assembled prompt to a file."),
    ] = None,
) -> None:
    """ProjectForge — Project Scaffolder. Scaffold projects with AI + organization conventions."""
    if ctx.invoked_subcommand is not None:
        return

    prompt_only = dry_run or bool(export)
    if resume and prompt_only:
        console.print(status_line("--resume cannot be combined with --dry-run or --export."))
        raise typer.Exit(1)
    try:
        validate_approval_mode(
            approval_mode,
            allow_unsafe=allow_unsafe or prompt_only,
        )
    except ValueError as exc:
        console.print(status_line(str(exc), accent="amber"))
        raise typer.Exit(1) from exc
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
        resume=resume,
    )

    if version:
        console.print(f"projectforge {__version__}")
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
    if agents is None:
        agents = forge_config.get("agents", False)
    backend_statuses = get_backend_statuses() if not prompt_only else {}

    _validate_backend_override(use)

    # Non-interactive mode: all required flags provided
    if name and stack and description:
        resolved_stack = STACK_ALIASES.get(stack.lower())
        if not resolved_stack:
            valid = ", ".join(sorted(set(STACK_ALIASES.values())))
            console.print(f"[red]Unknown stack '{stack}'. Choose from: {valid}[/red]")
            raise typer.Exit(1)

        from projectforge.stacks import STACK_META

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
        # Interactive flow: answers dict includes execution mode choice
        if answers.get("agents"):
            agents = True

    # --- Multi-backend phase routing ---
    available_backends = (
        {backend for backend, status in backend_statuses.items() if status.usable}
        if backend_statuses
        else None
    )
    quality_signals = read_quality_signals()
    quality_scores: dict[str, dict[str, float]] = {}
    for phase_name in STACK_PHASES.get(answers["stack"], []):
        scores = compute_backend_scores(quality_signals, stack=answers["stack"], phase=phase_name)
        if scores:
            quality_scores[phase_name] = scores

    phase_backends = pick_phase_backends(
        answers["stack"],
        override=use,
        description=answers.get("description", ""),
        prefer_installed_backends=not prompt_only,
        available_backends=available_backends,
        quality_scores=quality_scores or None,
    )
    merged_groups = merge_adjacent_phases(phase_backends)
    all_phases = STACK_PHASES.get(answers["stack"], ["architecture", "tests"])

    # Identify which phases can run in parallel (everything between first and last)
    # Architecture must run first, verify must run last, middle phases run concurrently.
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
                    backend for backend, status in backend_statuses.items() if status.installed
                },
            )
            raise typer.Exit(1)

        for backend in required_backends:
            status = backend_statuses.get(backend, BackendStatus(False, False))
            if not status.installed:
                console.print(
                    f"\n[red bold]{backend}[/red bold] [red]is not installed or not on PATH.[/red]"
                    "\n[dim]Install at least one AI CLI (claude, antigravity, or codex).[/dim]"
                )
                raise typer.Exit(1)
            if status.ready is not True:
                _render_backend_readiness_notice(backend_statuses, required_backends={backend})
                raise typer.Exit(1)

    # Resolve model per backend: --model overrides everything, else use config
    backend_models: dict[str, str] = forge_config.get("backend_models", {})

    # Load conventions and CLAUDE.md template
    try:
        conventions_profile = forge_config.get("conventions_profile", "default")
        if conventions_profile == "default":
            conventions, conv_warnings = load_conventions(stack=answers["stack"])
        else:
            conventions, conv_warnings = load_conventions(
                stack=answers["stack"],
                profile=conventions_profile,
            )
        convention_bundle = load_conventions_bundle(
            stack=answers["stack"],
            profile=conventions_profile,
        )
    except ConventionValidationError as exc:
        console.print(status_line(f"Conventions error: {exc}", accent="amber"))
        raise typer.Exit(1) from exc
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
        approval_mode=approval_mode,
        conventions=conventions,
        claude_md_loaded=bool(claude_md_template),
        design_template_label=answers.get("design_template_label"),
        media_collection=selected_collection,
        media_asset_count=media_asset_count,
        convention_sources=convention_bundle.contributions,
        verbose=verbose,
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
    if resume:
        if not project_dir.is_dir():
            console.print(
                status_line(
                    "Resume target does not exist. Repeat the original project name and options.",
                    accent="amber",
                )
            )
            raise typer.Exit(1)
    elif not prompt_only:
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
        prompt += _FORGE_RUNTIME_BOUNDARY
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
        prompt += _FORGE_RUNTIME_BOUNDARY
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

        if dry_run:
            console.print()
            console.print(
                status_line(
                    "Preview only: no provider processes started and no model calls made.",
                    accent="aqua",
                )
            )
            if agents:
                console.print(
                    muted("Multi-agent decomposition is generated only when a live run starts.")
                )

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

    try:
        progress_state = initialize_progress(
            project_dir,
            name=answers["name"],
            stack=answers["stack"],
            approval_mode=approval_mode,
            phase_prompts=phase_prompts,
            resume=resume,
        )
    except ProgressContractError as exc:
        console.print(status_line(str(exc), accent="amber"))
        raise typer.Exit(1) from exc
    completed_phases = {
        phase["phase"] for phase in progress_state["phases"] if phase.get("status") == "completed"
    }
    if resume:
        console.print(
            status_line(
                f"Resume validated: preserving {len(completed_phases)} completed phase(s).",
                accent="aqua",
            )
        )

    if verbose:
        total_chars = sum(len(prompt) for _, _, prompt in phase_prompts)
        n = len(phase_prompts)
        console.print(
            status_line(
                f"Total prompt length: {total_chars} chars across {n} phase(s)",
                accent="violet",
            )
        )

    selected_backends = sorted({backend for _, backend in phase_backends})
    model_summary = ", ".join(
        f"{backend}={model or backend_models.get(backend) or 'provider default'}"
        for backend in selected_backends
    )
    execution_windows = len(serial_first) + len(serial_last)
    execution_windows += 1 if can_parallel else len(parallel_middle)
    minimum_minutes = max(1, execution_windows * 2)
    maximum_minutes = max(5, execution_windows * 15)
    remaining_provider_calls = len(phase_backends) - len(completed_phases)
    if agents:
        provider_call_summary = (
            f"typically {remaining_provider_calls * 4}-{remaining_provider_calls * 8} "
            "(planner + 2-6 tasks + reconciliation per remaining phase)"
        )
    else:
        provider_call_summary = f"{remaining_provider_calls} (one per remaining phase)"

    previous_duration = latest_scaffold_duration(answers["stack"])
    history_summary = (
        f"Last {answers['stack']} scaffold: {_format_duration(previous_duration)} "
        "(local measurement)"
        if previous_duration is not None
        else f"Last {answers['stack']} scaffold: no measured duration yet"
    )
    preflight_lines = [
        subtle(f"Workspace: {project_dir.resolve()}"),
        subtle(f"Providers: {', '.join(selected_backends)}"),
        subtle(f"Models: {model_summary}"),
        subtle(f"Approval mode: {approval_mode}"),
        subtle(f"Provider CLI invocations: {provider_call_summary}"),
        subtle(
            f"Planning range: about {minimum_minutes}-{maximum_minutes} minutes; "
            "provider and network latency may vary"
        ),
        subtle(history_summary),
        subtle(
            "Strategy: thorough multi-agent planning and task execution"
            if agents
            else "Strategy: standard one-call-per-phase execution"
        ),
    ]
    preflight_lines.extend(
        _provider_commitment_lines(phase_backends, completed_phases, agents=bool(agents))
    )
    preflight_lines.extend(
        [
            subtle(
                "Demo mode: generated startup should not require real service credentials"
                if answers.get("demo_mode")
                else "Demo mode: disabled; generated startup may require service credentials"
            ),
            subtle(
                "Verification: enabled"
                if verify
                else "Verification: disabled; completion cannot be independently verified"
            ),
            muted(
                "Unsafe mode disables provider approval boundaries."
                if approval_mode == "unsafe"
                else "Writes remain constrained by the selected provider's workspace mode."
            ),
        ]
    )
    console.print(
        make_panel(
            grouped_lines(preflight_lines),
            title="Execution Preflight",
            accent="amber" if approval_mode == "unsafe" else "aqua",
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

    scaffold_start = time.monotonic()

    # Build phase context for the timeline display
    phase_context: list[dict] = []
    for phase, backend in phase_backends:
        phase_context.append(
            {
                "label": PHASE_LABELS.get(phase, phase),
                "status": "completed" if phase in completed_phases else "pending",
                "elapsed": 0.0,
                "accent": BACKEND_ACCENTS.get(backend, "violet"),
            }
        )

    # Accumulated agent task stats across all orchestrated phases (agents mode only)
    _agent_stats: dict = {"planned": 0, "completed": 0, "failed": 0}
    _any_orchestrated = False

    # --- Execute phases: serial first, parallel middle, serial last ---
    total_phases = len(phase_backends)
    step = 1

    # Step 1: Run architecture (serial)
    for phase, backend in serial_first:
        label = PHASE_LABELS.get(phase, phase)
        if phase in completed_phases:
            console.print(status_line(f"Preserved completed phase: {label}", accent="aqua"))
            step += 1
            continue
        console.print()
        console.print(
            make_step_panel(step, total_phases, label, detail=f"backend: {backend}", accent="aqua")
        )
        phase_prompt = next(p for ph, _, p in phase_prompts if ph == phase)
        effective_model = model or backend_models.get(backend)
        phase_idx = next(i for i, (p, _) in enumerate(phase_backends) if p == phase)
        phase_context[phase_idx]["status"] = "active"
        phase_start = time.monotonic()
        mark_phase(project_dir, phase, status="running")
        if agents:
            from projectforge.orchestrator import run_phase_orchestrated

            returncode, _phase_stats = run_phase_orchestrated(
                phase=phase,
                backend=backend,
                prompt=phase_prompt,
                project_dir=project_dir,
                stack=answers["stack"],
                conventions=conventions,
                model=effective_model,
                verbose=verbose,
                approval_mode=approval_mode,
                allow_unsafe=allow_unsafe,
            )
            _any_orchestrated = True
            for key in ("planned", "completed", "failed"):
                _agent_stats[key] += _phase_stats.get(key, 0)
        else:
            returncode = run_ai(
                backend,
                phase_prompt,
                project_dir,
                model=effective_model,
                verbose=verbose,
                label=label,
                phase_context=phase_context,
                approval_mode=approval_mode,
                allow_unsafe=allow_unsafe,
            )
        phase_context[phase_idx]["status"] = "completed"
        phase_elapsed = time.monotonic() - phase_start
        phase_context[phase_idx]["elapsed"] = phase_elapsed
        if returncode != 0:
            phase_context[phase_idx]["status"] = "failed"
            mark_phase(
                project_dir,
                phase,
                status="failed",
                duration_seconds=phase_elapsed,
                exit_code=returncode,
                failure_category=getattr(returncode, "failure_category", "unknown"),
            )
            _render_phase_failure(backend, label, returncode)
            raise typer.Exit(returncode)
        mark_phase(
            project_dir, phase, status="completed", duration_seconds=phase_elapsed, exit_code=0
        )
        console.print()
        console.print(make_file_tree(project_dir))
        step += 1

    # Step 2: Run middle phases (parallel if multiple, serial if single)
    if parallel_middle:
        remaining_middle = [
            (phase, backend) for phase, backend in parallel_middle if phase not in completed_phases
        ]
        if not agents:
            for phase, _backend in parallel_middle:
                if phase in completed_phases:
                    console.print(
                        status_line(
                            f"Preserved completed phase: {PHASE_LABELS.get(phase, phase)}",
                            accent="aqua",
                        )
                    )
                    step += 1
        if agents:
            # Orchestrator handles its own internal parallelism — run sequentially here
            from projectforge.orchestrator import run_phase_orchestrated

            for phase, backend in parallel_middle:
                label = PHASE_LABELS.get(phase, phase)
                if phase in completed_phases:
                    console.print(status_line(f"Preserved completed phase: {label}", accent="aqua"))
                    step += 1
                    continue
                console.print()
                console.print(
                    make_step_panel(
                        step, total_phases, label, detail=f"backend: {backend}", accent="violet"
                    )
                )
                phase_prompt = next(p for ph, _, p in phase_prompts if ph == phase)
                effective_model = model or backend_models.get(backend)
                phase_idx = next(i for i, (p, _) in enumerate(phase_backends) if p == phase)
                phase_context[phase_idx]["status"] = "active"
                phase_start = time.monotonic()
                mark_phase(project_dir, phase, status="running")
                returncode, _phase_stats = run_phase_orchestrated(
                    phase=phase,
                    backend=backend,
                    prompt=phase_prompt,
                    project_dir=project_dir,
                    stack=answers["stack"],
                    conventions=conventions,
                    model=effective_model,
                    verbose=verbose,
                    approval_mode=approval_mode,
                    allow_unsafe=allow_unsafe,
                )
                _any_orchestrated = True
                for key in ("planned", "completed", "failed"):
                    _agent_stats[key] += _phase_stats.get(key, 0)
                phase_elapsed = time.monotonic() - phase_start
                phase_context[phase_idx]["elapsed"] = phase_elapsed
                if returncode != 0:
                    phase_context[phase_idx]["status"] = "failed"
                    mark_phase(
                        project_dir,
                        phase,
                        status="failed",
                        duration_seconds=phase_elapsed,
                        exit_code=returncode,
                        failure_category=getattr(returncode, "failure_category", "unknown"),
                    )
                    _render_phase_failure(backend, label, returncode)
                    raise typer.Exit(returncode)
                phase_context[phase_idx]["status"] = "completed"
                mark_phase(
                    project_dir,
                    phase,
                    status="completed",
                    duration_seconds=phase_elapsed,
                    exit_code=0,
                )
                console.print()
                console.print(make_file_tree(project_dir))
                step += 1
        elif len(remaining_middle) > 1:
            labels = " + ".join(f"{PHASE_LABELS.get(p, p)} ({b})" for p, b in remaining_middle)
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
            label_to_phase: dict[str, str] = {}
            for phase, backend in remaining_middle:
                phase_prompt = next(p for ph, _, p in phase_prompts if ph == phase)
                effective_model = model or backend_models.get(backend)
                label = PHASE_LABELS.get(phase, phase)
                label_to_phase[label] = phase
                phase_idx = next(i for i, (p, _) in enumerate(phase_backends) if p == phase)
                phase_context[phase_idx]["status"] = "active"
                mark_phase(project_dir, phase, status="running")
                parallel_args.append(
                    {
                        "label": label,
                        "backend": backend,
                        "prompt": phase_prompt,
                        "model": effective_model,
                        "approval_mode": approval_mode,
                        "allow_unsafe": allow_unsafe,
                    }
                )

            parallel_started = time.monotonic()
            results = run_ai_parallel(parallel_args, project_dir, verbose=verbose)
            parallel_elapsed = time.monotonic() - parallel_started
            failed_results: list[tuple[str, int]] = []
            for label, returncode in results:
                phase = label_to_phase[label]
                phase_idx = next(i for i, (p, _) in enumerate(phase_backends) if p == phase)
                if returncode != 0:
                    phase_context[phase_idx]["status"] = "failed"
                    mark_phase(
                        project_dir,
                        phase,
                        status="failed",
                        duration_seconds=parallel_elapsed,
                        exit_code=returncode,
                        failure_category=getattr(returncode, "failure_category", "unknown"),
                    )
                    failed_results.append((label, returncode))
                else:
                    phase_context[phase_idx]["status"] = "completed"
                    mark_phase(
                        project_dir,
                        phase,
                        status="completed",
                        duration_seconds=parallel_elapsed,
                        exit_code=0,
                    )
            if failed_results:
                for label, returncode in failed_results:
                    _render_phase_failure("parallel backend", label, returncode)
                raise typer.Exit(failed_results[0][1])
            console.print()
            console.print(make_file_tree(project_dir))
            step += len(remaining_middle)
        else:
            for phase, backend in remaining_middle:
                label = PHASE_LABELS.get(phase, phase)
                console.print()
                console.print(
                    make_step_panel(
                        step, total_phases, label, detail=f"backend: {backend}", accent="violet"
                    )
                )
                phase_prompt = next(p for ph, _, p in phase_prompts if ph == phase)
                effective_model = model or backend_models.get(backend)
                phase_idx = next(i for i, (p, _) in enumerate(phase_backends) if p == phase)
                phase_context[phase_idx]["status"] = "active"
                phase_start = time.monotonic()
                mark_phase(project_dir, phase, status="running")
                returncode = run_ai(
                    backend,
                    phase_prompt,
                    project_dir,
                    model=effective_model,
                    verbose=verbose,
                    label=label,
                    phase_context=phase_context,
                    approval_mode=approval_mode,
                    allow_unsafe=allow_unsafe,
                )
                phase_elapsed = time.monotonic() - phase_start
                phase_context[phase_idx]["elapsed"] = phase_elapsed
                if returncode != 0:
                    phase_context[phase_idx]["status"] = "failed"
                    mark_phase(
                        project_dir,
                        phase,
                        status="failed",
                        duration_seconds=phase_elapsed,
                        exit_code=returncode,
                        failure_category=getattr(returncode, "failure_category", "unknown"),
                    )
                    _render_phase_failure(backend, label, returncode)
                    raise typer.Exit(returncode)
                phase_context[phase_idx]["status"] = "completed"
                mark_phase(
                    project_dir,
                    phase,
                    status="completed",
                    duration_seconds=phase_elapsed,
                    exit_code=0,
                )
                console.print()
                console.print(make_file_tree(project_dir))
                step += 1

    # Step 3: Run verify (serial)
    for phase, backend in serial_last:
        label = PHASE_LABELS.get(phase, phase)
        if phase in completed_phases:
            console.print(status_line(f"Preserved completed phase: {label}", accent="aqua"))
            step += 1
            continue
        console.print()
        console.print(
            make_step_panel(step, total_phases, label, detail=f"backend: {backend}", accent="plum")
        )
        phase_prompt = next(p for ph, _, p in phase_prompts if ph == phase)
        effective_model = model or backend_models.get(backend)
        phase_idx = next(i for i, (p, _) in enumerate(phase_backends) if p == phase)
        phase_context[phase_idx]["status"] = "active"
        phase_start = time.monotonic()
        mark_phase(project_dir, phase, status="running")
        if agents:
            from projectforge.orchestrator import run_phase_orchestrated

            returncode, _phase_stats = run_phase_orchestrated(
                phase=phase,
                backend=backend,
                prompt=phase_prompt,
                project_dir=project_dir,
                stack=answers["stack"],
                conventions=conventions,
                model=effective_model,
                verbose=verbose,
                approval_mode=approval_mode,
                allow_unsafe=allow_unsafe,
            )
            _any_orchestrated = True
            for key in ("planned", "completed", "failed"):
                _agent_stats[key] += _phase_stats.get(key, 0)
        else:
            returncode = run_ai(
                backend,
                phase_prompt,
                project_dir,
                model=effective_model,
                verbose=verbose,
                label=label,
                phase_context=phase_context,
                approval_mode=approval_mode,
                allow_unsafe=allow_unsafe,
            )
        phase_elapsed = time.monotonic() - phase_start
        phase_context[phase_idx]["elapsed"] = phase_elapsed
        if returncode != 0:
            phase_context[phase_idx]["status"] = "failed"
            mark_phase(
                project_dir,
                phase,
                status="failed",
                duration_seconds=phase_elapsed,
                exit_code=returncode,
                failure_category=getattr(returncode, "failure_category", "unknown"),
            )
            _render_phase_failure(backend, label, returncode)
            raise typer.Exit(returncode)
        phase_context[phase_idx]["status"] = "completed"
        mark_phase(
            project_dir,
            phase,
            status="completed",
            duration_seconds=phase_elapsed,
            exit_code=0,
        )
        console.print()
        console.print(make_file_tree(project_dir))
        step += 1

    # Post-scaffold: manifest, log, git init, verify, hooks, dashboard
    write_scaffold_manifest(
        answers,
        phase_backends,
        project_dir,
        conventions,
        model_override=model,
        backend_models=backend_models,
        approval_mode=approval_mode,
        convention_sources=convention_bundle.contributions,
    )

    git_ok = ensure_git_init(project_dir)

    verify_report = None
    if verify:
        verify_report = verify_scaffold(answers["stack"], project_dir, verbose=verbose)
        write_verification_report(verify_report, project_dir)

    append_quality_signal(
        stack=answers["stack"],
        phase_backends=phase_backends,
        verify_report=verify_report,
        project_dir=project_dir,
    )

    run_post_scaffold_hook(project_dir, answers)
    elapsed = time.monotonic() - scaffold_start
    append_scaffold_log(
        answers,
        phase_backends,
        project_dir,
        verify_report=verify_report,
        verification_requested=verify,
        duration_seconds=elapsed,
    )
    record_preferences(answers)

    render_dashboard(
        console=console,
        answers=answers,
        phase_backends=phase_backends,
        project_dir=project_dir,
        verify_report=verify_report,
        elapsed=elapsed,
        agent_stats=_agent_stats if _any_orchestrated else None,
    )

    scaffold_date = datetime.now(UTC).strftime("%Y-%m-%d")
    backends_used = sorted({b for _, b in phase_backends})
    write_card(
        project_dir,
        name=answers["name"],
        stack=answers["stack"],
        backends=backends_used,
        date=scaffold_date,
    )
    inject_badge_into_readme(project_dir)

    sound_enabled = forge_config.get("sound", False)
    play_completion_sound(success=True, enabled=sound_enabled)

    if not git_ok:
        console.print(
            muted('Run git init && git add -A && git commit -m "Initial commit" manually.')
        )

    if open_editor:
        preferred = forge_config.get("preferred_editor", "")
        open_in_editor(project_dir, preferred_editor=preferred)
