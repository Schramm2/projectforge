"""ProjectForge CLI — entry point."""

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
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
    load_design_template,
)
from projectforge.doctor import build_doctor_report, doctor_exit_code
from projectforge.evolutions import build_evolve_prompt, get_capabilities, get_capability
from projectforge.execution_policy import validate_approval_mode
from projectforge.execution_state import (
    ProgressContractError,
    initialize_progress,
)
from projectforge.execution_state import (
    mark_phase as _mark_phase,
)
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
from projectforge.project_context import extract_project_context_block
from projectforge.prompt_builder import build_phase_prompt
from projectforge.prompts import collect_answers
from projectforge.quality import append_quality_signal, compute_backend_scores, read_quality_signals
from projectforge.questionary_theme import prompt_confirm, prompt_select, prompt_text
from projectforge.router import (
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
from projectforge.scaffold_completion import (
    ScaffoldCompletionDependencies,
    ScaffoldCompletionSettings,
    ScaffoldRecordError,
    complete_scaffold,
)
from projectforge.scaffold_execution import (
    PhaseExecutionDependencies,
    PhaseExecutionError,
    PhaseExecutionSettings,
    PhaseRoutePlan,
    ScaffoldPhaseExecutor,
)
from projectforge.scaffold_log import (
    SCAFFOLD_LOG_PATH,
    append_scaffold_log,
    latest_scaffold_duration,
    write_scaffold_manifest,
)
from projectforge.scaffold_prompts import ScaffoldPromptPlan
from projectforge.scaffold_request import (
    NonInteractiveScaffoldRequest,
    ScaffoldRequestError,
)
from projectforge.setup import load_forge_config, needs_setup, run_setup, save_forge_config
from projectforge.sound import play_completion_sound
from projectforge.ui import (
    ACCENTS,
    TEXT_MUTED,
    TEXT_SECONDARY,
    bullet,
    create_console,
    grouped_lines,
    header_panel,
    make_panel,
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
_PROVIDER_QUOTA_NOTES = {
    "claude": "Claude Code plan limits or configured API billing",
    "antigravity": "Google account plan and Antigravity quota",
    "codex": "ChatGPT/Codex plan limits or configured API billing",
}


def mark_phase(*args, **kwargs) -> dict:
    """Persist phase progress while keeping filesystem failures user-safe."""
    try:
        return _mark_phase(*args, **kwargs)
    except ProgressContractError as exc:
        console.print(status_line(str(exc), accent="amber"))
        raise typer.Exit(1) from exc


def _validate_backend_override(backend: str | None) -> None:
    """Reject retired or unknown explicit backend names with migration guidance."""
    if backend is None:
        return
    if backend == "gemini":
        console.print(
            "[red]That AI tool option is no longer supported. Run `forge --help` and choose "
            "an available `--use` value.[/red]"
        )
        raise typer.Exit(1)
    if backend not in SUPPORTED_BACKENDS:
        console.print(
            "[red]That AI tool choice is not available. Run `forge --help` to see valid "
            "`--use` values.[/red]"
        )
        raise typer.Exit(1)


def _load_scaffold_record(path: Path) -> dict:
    """Load a project scaffold record without exposing parse or filesystem details."""
    import json

    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        console.print(
            status_line(
                "Forge could not read this project's scaffold record. Restore it from a "
                "trusted backup, or scaffold a new target.",
                accent="amber",
            )
        )
        raise typer.Exit(1) from exc
    if not isinstance(payload, dict):
        console.print(
            status_line(
                "Forge could not read this project's scaffold record. Restore it from a "
                "trusted backup, or scaffold a new target.",
                accent="amber",
            )
        )
        raise typer.Exit(1)
    return payload


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
            editor_label = "none found — install one or run `projectforge --setup`"
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


def _render_routing_plan(plan: PhaseRoutePlan) -> None:
    """Render the selected routing plan."""
    if not plan.parallel_middle and not plan.serial_last and len(plan.serial_first) == 1:
        console.print(
            status_line(
                f"Using {plan.serial_first[0].backend} for all scaffolding",
                accent="violet",
            )
        )
        return

    lines: list[Text] = []
    step = 1
    for route in plan.serial_first:
        lines.append(bullet(f"{step}. {route.label} -> {route.backend}", accent="aqua"))
        step += 1
    if plan.can_parallel:
        parts = [f"{route.label} -> {route.backend}" for route in plan.parallel_middle]
        lines.append(bullet(f"{step}. parallel: {' | '.join(parts)}", accent="amber"))
        step += 1
    else:
        for route in plan.parallel_middle:
            lines.append(bullet(f"{step}. {route.label} -> {route.backend}", accent="aqua"))
            step += 1
    for route in plan.serial_last:
        lines.append(bullet(f"{step}. {route.label} -> {route.backend}", accent="plum"))
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
    conventions_profile: str = "default",
    project_brief_added: bool = False,
    project_context_files: int = 0,
    verbose: bool = False,
) -> None:
    """Render loaded scaffold context."""
    lines: list[Text] = []
    for backend in sorted(required_backends):
        configured_model = model_override or backend_models.get(backend)
        lines.append(subtle(f"{backend} model: {configured_model or 'provider default'}"))
    lines.append(subtle(f"Approval mode: {approval_mode}"))

    profile_label = "Forge defaults" if conventions_profile == "default" else conventions_profile
    lines.append(subtle(f"Convention profile: {profile_label}"))
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
    brief_label = "added" if project_brief_added else "not added"
    lines.append(
        subtle(f"Project brief: {brief_label}; nearby context: {project_context_files} selected")
    )
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


def _backend_help_line(_backend: str, status: BackendStatus) -> Text:
    """Return a user-facing readiness line for a backend."""
    if status.ready is False:
        return subtle("A selected AI tool needs sign-in. Run `forge doctor` for the next step.")
    if not status.installed:
        return subtle("A selected AI tool is not available. Run `forge doctor` for setup steps.")
    return subtle(
        "Forge could not confirm that a selected AI tool is ready. Run `forge doctor` for the "
        "next step."
    )


def _render_backend_readiness_notice(
    backend_statuses: dict[str, BackendStatus],
    *,
    required_backends: set[str],
) -> None:
    """Render a panel when required backends are unavailable for routing."""
    lines: list[Text] = []
    seen_messages: set[str] = set()
    for backend in sorted(required_backends):
        status = backend_statuses.get(backend, BackendStatus(False, False))
        line = _backend_help_line(backend, status)
        message = line.plain
        if message not in seen_messages:
            lines.append(line)
            seen_messages.add(message)
    lines.append(muted("Run forge --setup after fixing login or install issues."))
    console.print(make_panel(grouped_lines(lines), title="Backend Readiness", accent="amber"))


def _render_phase_failure(_backend: str, label: str, _returncode: int) -> None:
    """Render helpful follow-up guidance when a scaffold phase fails."""
    lines: list[Text] = [
        subtle(f"Project generation stopped during {label}."),
        subtle("Your completed work is safe."),
        subtle("Run `forge doctor`, fix the reported issue, then repeat with `--resume`."),
        muted("Resume verifies the original contract and does not rerun completed phases."),
    ]
    console.print(make_panel(grouped_lines(lines), title="Execution", accent="amber"))


def _validate_project_name_for_collision(name: str) -> bool | str:
    """Validate a replacement project name when resolving collisions."""
    if not name.strip():
        return "Enter a project name, for example `customer-api`."
    if not _PROJECT_NAME_RE.match(name):
        return (
            "Start with a letter or number. Use only letters, numbers, dots, hyphens, "
            "or underscores."
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
                        Text("That project folder already contains files.", style="bold #F7F9FF"),
                        subtle(
                            "Choose a different name, or confirm overwrite to replace its contents."
                        ),
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
        raise ConventionValidationError(
            "Choose a stack or convention path, for example `stacks/fastapi`, then retry."
        )
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
        console.print(
            status_line(
                "Forge could not find that convention profile. Run `forge conventions list`, "
                "or create it with `forge conventions init NAME`.",
                accent="amber",
            )
        )
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
        console.print(
            status_line(
                "Forge could not load the active conventions. Run `forge conventions "
                "validate`, then fix or restore the convention files.",
                accent="amber",
            )
        )
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
        console.print(
            status_line(
                "Forge could not load the active conventions. Run `forge conventions "
                "validate`, then fix or restore the convention files.",
                accent="amber",
            )
        )
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
        console.print(
            status_line(
                "Forge could not load the active conventions. Fix or restore the convention "
                "files, then validate again.",
                accent="amber",
            )
        )
        raise typer.Exit(1) from exc
    secret_types = check_for_secrets(bundle.prompt_block)
    if secret_types:
        console.print(
            status_line(
                "Forge found content that looks like a credential. Remove secrets from the "
                "active convention files, then validate again.",
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
        console.print(
            status_line(
                "Forge could not find that convention profile. Run `forge conventions list`, "
                "or create it with `forge conventions init NAME`.",
                accent="amber",
            )
        )
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
        console.print(
            status_line("Choose one conventions action per command, then retry.", accent="amber")
        )
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
        console.print(
            status_line(
                "Forge could not load the bundled conventions. Reinstall Forge or restore its "
                "bundled conventions, then run `forge admin conventions --validate`.",
                accent="amber",
            )
        )
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
        try:
            repair_result = repair_history(
                scaffold_log_path=SCAFFOLD_LOG_PATH,
                quality_log_path=QUALITY_LOG_PATH,
            )
        except OSError as exc:
            console.print(
                status_line(
                    "Forge could not repair the saved scaffold history. Check that Forge's "
                    "data folder is readable and writable, then retry.",
                    accent="amber",
                )
            )
            raise typer.Exit(1) from exc
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
    try:
        if SCAFFOLD_LOG_PATH.exists():
            for line in SCAFFOLD_LOG_PATH.read_text().splitlines():
                line = line.strip()
                if line:
                    try:
                        scaffold_entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        quality_entries = read_quality_signals()
    except OSError as exc:
        console.print(
            status_line(
                "Forge could not read the saved scaffold history. Check that Forge's data "
                "folder is readable, then retry.",
                accent="amber",
            )
        )
        raise typer.Exit(1) from exc

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
                "Forge could not find this project's scaffold record. Run this command from "
                "the root of a project created by Forge.",
                accent="amber",
            )
        )
        raise typer.Exit(1)

    dna = _load_scaffold_record(manifest_path)
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
                "This project type has no add-on capabilities. Make the change manually, or "
                "use `forge evolve` in a supported project.",
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
                    f"That capability is not available for this stack. Choose one of: {valid}.",
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
            console.print(
                status_line(
                    "The selected AI tool is not available. Run `forge doctor`, complete the "
                    "recommended setup, then retry.",
                    accent="amber",
                )
            )
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
        try:
            manifest_path.write_text(json.dumps(dna, indent=2) + "\n")
        except OSError as exc:
            console.print(
                status_line(
                    "The change was applied, but Forge could not update the scaffold record. "
                    "Check that the project folder is writable before using `forge evolve` "
                    "again.",
                    accent="amber",
                )
            )
            raise typer.Exit(1) from exc
        console.print(status_line(f"Successfully added {cap['name']}", accent="aqua"))
    else:
        console.print(
            status_line(
                "Forge could not apply this change. Your existing project is unchanged where "
                "possible; run `forge doctor`, then retry.",
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
                try:
                    fixed = generate_fix(project_dir, c)
                except OSError as exc:
                    console.print(
                        status_line(
                            "Forge could not create that convention file. Check that the project "
                            "folder is writable, then run `forge check --fix` again.",
                            accent="amber",
                        )
                    )
                    raise typer.Exit(1) from exc
                if fixed:
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
        try:
            Path(export).write_text("\n".join(lines))
        except OSError as exc:
            console.print(
                status_line(
                    "Forge could not save the audit report at that location. Choose a writable "
                    "path, then export it again.",
                    accent="amber",
                )
            )
            raise typer.Exit(1) from exc
        console.print(status_line(f"Report exported to {export}", accent="aqua"))

    if fix:
        console.print(status_line("Run forge check again to verify fixes.", accent="violet"))


@dataclass(frozen=True)
class _ReplayPrompt:
    """A merged phase prompt reconstructed from scaffold evidence."""

    phases: tuple[str, ...]
    backend: str
    content: str

    @property
    def label(self) -> str:
        return " + ".join(self.phases)


@dataclass(frozen=True)
class _ReplayDiff:
    """Structural changes from the current project to replay output."""

    added: tuple[str, ...]
    removed: tuple[str, ...]
    changed: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed)


def _load_replay_conventions(project_dir: Path, stack: str) -> str:
    snapshot_path = project_dir / ".forge" / "conventions-snapshot.md"
    if snapshot_path.exists():
        try:
            return snapshot_path.read_text()
        except OSError as exc:
            console.print(
                status_line(
                    "Forge could not read the saved convention snapshot. Restore it from a "
                    "trusted backup, or remove it to use current conventions.",
                    accent="amber",
                )
            )
            raise typer.Exit(1) from exc

    replay_stack = stack or None
    if replay_stack and replay_stack not in STACK_PHASES:
        console.print(
            status_line(
                "The recorded project type is no longer available. Use the original Forge "
                "version to replay it, or scaffold a new target.",
                accent="amber",
            )
        )
        raise typer.Exit(1)
    try:
        conventions, warnings = load_bundled_conventions(stack=replay_stack)
    except ConventionValidationError as exc:
        console.print(
            status_line(
                "Forge could not load conventions for replay. Run `forge conventions "
                "validate`, then fix or restore the convention files.",
                accent="amber",
            )
        )
        raise typer.Exit(1) from exc
    for warning in warnings:
        console.print(f"[yellow]{warning}[/yellow]")
    console.print(
        status_line(
            "No saved convention snapshot was found. Forge will use current conventions, "
            "so replay results may differ.",
            accent="amber",
        )
    )
    return conventions


def _load_replay_context(project_dir: Path, scaffold_record: dict) -> str:
    snapshot_path = project_dir / ".forge" / "context-snapshot.md"
    if not snapshot_path.exists():
        if scaffold_record.get("context_hash"):
            console.print(
                status_line(
                    "The original scaffold used selected project context, but its local "
                    "snapshot is missing. Replay will continue without that context and may "
                    "differ.",
                    accent="amber",
                )
            )
        return ""

    try:
        context = extract_project_context_block(snapshot_path.read_text())
    except OSError as exc:
        console.print(
            status_line(
                "Forge could not read the saved project context. Restore it from a trusted "
                "backup, or remove it and accept that replay results may differ.",
                accent="amber",
            )
        )
        raise typer.Exit(1) from exc
    if context:
        return context
    console.print(
        status_line(
            "Forge could not find valid project context in the saved snapshot. Restore it "
            "from a trusted backup, or remove it and accept that replay may differ.",
            accent="amber",
        )
    )
    raise typer.Exit(1)


def _reconstruct_replay_answers(
    scaffold_record: dict,
    project_dir: Path,
    context_snapshot: str,
) -> dict:
    return {
        "name": scaffold_record.get("name", project_dir.name),
        "stack": scaffold_record.get("stack", ""),
        "description": scaffold_record.get("description", ""),
        "docker": any(project_dir.rglob("Dockerfile")),
        "design_template": scaffold_record.get("design_template"),
        "auth_provider": scaffold_record.get("auth_provider"),
        "demo_mode": scaffold_record.get("demo_mode", False),
        "project_brief": scaffold_record.get("project_brief") or {},
        "project_context_snapshot": context_snapshot,
        "extra": "",
        "services": [],
    }


def _resolve_replay_routes(
    scaffold_record: dict,
    *,
    stack: str,
    override: str | None,
) -> list[tuple[str, str]]:
    recorded_routing = scaffold_record.get("routing", [])
    phase_backends = []
    if isinstance(recorded_routing, list):
        phase_backends = [
            (item["phase"], normalize_legacy_backend(item["backend"]))
            for item in recorded_routing
            if isinstance(item, dict)
            and isinstance(item.get("phase"), str)
            and isinstance(item.get("backend"), str)
        ]
    if not phase_backends:
        return pick_phase_backends(stack, override=override)

    for _, backend in phase_backends:
        if check_backend_installed(override or backend):
            continue
        console.print(
            status_line(
                "A tool used by the original scaffold is unavailable. Run `forge doctor`; "
                "complete its setup before replaying for comparable results.",
                accent="amber",
            )
        )
        return pick_phase_backends(stack, override=override)
    return phase_backends


def _build_replay_prompts(
    answers: dict,
    conventions: str,
    phase_backends: list[tuple[str, str]],
) -> tuple[_ReplayPrompt, ...]:
    all_phases = STACK_PHASES.get(answers["stack"], ["architecture", "tests"])
    return tuple(
        _ReplayPrompt(
            phases=tuple(phases),
            backend=backend,
            content=build_phase_prompt(
                phases,
                all_phases,
                answers,
                conventions,
                backend=backend,
            ),
        )
        for phases, backend in merge_adjacent_phases(phase_backends)
    )


def _run_replay_prompts(
    prompts: tuple[_ReplayPrompt, ...],
    *,
    replay_dir: Path,
    scaffold_record: dict,
    model_override: str | None,
    verbose: bool,
    approval_mode: str,
    allow_unsafe: bool,
) -> None:
    for prompt in prompts:
        effective_model = model_override or scaffold_record.get("backend_models", {}).get(
            prompt.backend
        )
        returncode = run_ai(
            prompt.backend,
            prompt.content,
            replay_dir,
            model=effective_model,
            verbose=verbose,
            label=prompt.label,
            approval_mode=approval_mode,
            allow_unsafe=allow_unsafe,
        )
        if returncode == 0:
            continue
        console.print(
            status_line(
                "Replay stopped before it finished. Keep the partial project, fix the "
                "reported setup issue, then run replay again.",
                accent="amber",
            )
        )
        raise typer.Exit(returncode)


def _collect_replay_diff(project_dir: Path, replay_dir: Path) -> _ReplayDiff:
    import filecmp

    def collect(directory_diff, prefix: str = "") -> tuple[list[str], list[str], list[str]]:
        added = [f"{prefix}{name}" for name in directory_diff.right_only]
        removed = [f"{prefix}{name}" for name in directory_diff.left_only]
        changed = [f"{prefix}{name}" for name in directory_diff.diff_files]
        for subdir, nested_diff in directory_diff.subdirs.items():
            nested_added, nested_removed, nested_changed = collect(
                nested_diff,
                prefix=f"{prefix}{subdir}/",
            )
            added.extend(nested_added)
            removed.extend(nested_removed)
            changed.extend(nested_changed)
        return added, removed, changed

    directory_diff = filecmp.dircmp(
        str(project_dir),
        str(replay_dir),
        ignore=[".forge", ".git", "__pycache__", "node_modules", ".venv"],
    )
    added, removed, changed = collect(directory_diff)
    return _ReplayDiff(tuple(sorted(added)), tuple(sorted(removed)), tuple(sorted(changed)))


def _render_and_save_replay_diff(
    replay_diff: _ReplayDiff,
    *,
    project_dir: Path,
    project_name: str,
) -> None:
    console.print()
    for path in replay_diff.added:
        console.print(status_line(f"+ {path}", accent="aqua"))
    for path in replay_diff.changed:
        console.print(status_line(f"~ {path}", accent="amber"))
    for path in replay_diff.removed:
        console.print(status_line(f"- {path}", accent="plum"))
    if replay_diff.is_empty:
        console.print(status_line("No structural differences found.", accent="aqua"))

    diff_file = project_dir / ".forge" / f"replay-diff-{datetime.now(UTC).strftime('%Y-%m-%d')}.md"
    lines = [f"# Replay Diff — {project_name}\n"]
    for title, paths in (
        ("Added", replay_diff.added),
        ("Changed", replay_diff.changed),
        ("Removed", replay_diff.removed),
    ):
        if paths:
            lines.append(f"\n## {title}\n")
            lines.extend(f"- {path}" for path in paths)
    try:
        diff_file.write_text("\n".join(lines) + "\n")
    except OSError as exc:
        console.print(
            status_line(
                "Forge compared the projects but could not save the diff report. Check that "
                "the project folder is writable, then run replay with `--diff` again.",
                accent="amber",
            )
        )
        raise typer.Exit(1) from exc
    console.print(status_line(f"Diff saved to {diff_file}", accent="aqua"))


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
                "Forge could not find this project's scaffold record. Run this command from "
                "the root of a project created by Forge.",
                accent="amber",
            )
        )
        raise typer.Exit(1)

    scaffold_record = _load_scaffold_record(manifest_path)
    project_name = scaffold_record.get("name", project_dir.name)
    stack = scaffold_record.get("stack", "")
    console.print(header_panel(__version__))
    console.print(status_line(f"Replaying: {project_name}", accent="violet"))

    conventions = _load_replay_conventions(project_dir, stack)
    context_snapshot = _load_replay_context(project_dir, scaffold_record)
    answers = _reconstruct_replay_answers(scaffold_record, project_dir, context_snapshot)
    phase_backends = _resolve_replay_routes(scaffold_record, stack=stack, override=use)
    prompts = _build_replay_prompts(answers, conventions, phase_backends)

    if dry_run:
        for prompt in prompts:
            console.print(f"\n--- {prompt.label} ({prompt.backend}) ---\n")
            console.print(prompt.content)
        raise typer.Exit(0)

    replay_dir = Path(tempfile.mkdtemp(prefix=f"forge-replay-{project_name}-"))
    console.print(status_line(f"Replaying into {replay_dir}", accent="violet"))
    _run_replay_prompts(
        prompts,
        replay_dir=replay_dir,
        scaffold_record=scaffold_record,
        model_override=model,
        verbose=verbose,
        approval_mode=approval_mode,
        allow_unsafe=allow_unsafe,
    )
    console.print(status_line(f"Replay complete at {replay_dir}", accent="aqua"))

    if diff:
        _render_and_save_replay_diff(
            _collect_replay_diff(project_dir, replay_dir),
            project_dir=project_dir,
            project_name=project_name,
        )


@dataclass(frozen=True)
class _ScaffoldRouting:
    """Provider routes and execution windows selected for one scaffold."""

    phase_backends: list[tuple[str, str]]
    merged_groups: list[tuple[list[str], str]]
    all_phases: list[str]
    route_plan: PhaseRoutePlan
    available_backends: set[str] | None

    @property
    def required_backends(self) -> set[str]:
        return {backend for _, backend in self.phase_backends}


@dataclass(frozen=True)
class _LoadedScaffoldContext:
    """Conventions, templates, and media resolved before prompt assembly."""

    conventions: str
    convention_bundle: CompiledBundle
    claude_md_template: str | None
    conventions_profile: str
    warnings: tuple[str, ...]
    answer_extensions: dict[str, object]
    media_collection: str | None
    media_asset_count: int
    media_source_dir: Path | None


def _plan_scaffold_routing(
    answers: dict,
    *,
    override: str | None,
    prompt_only: bool,
    backend_statuses: dict[str, BackendStatus],
) -> _ScaffoldRouting:
    available_backends = (
        {backend for backend, status in backend_statuses.items() if status.usable}
        if backend_statuses
        else None
    )
    quality_signals = read_quality_signals()
    quality_scores: dict[str, dict[str, float]] = {}
    all_phases = STACK_PHASES.get(answers["stack"], ["architecture", "tests"])
    for phase in all_phases:
        scores = compute_backend_scores(quality_signals, stack=answers["stack"], phase=phase)
        if scores:
            quality_scores[phase] = scores

    phase_backends = pick_phase_backends(
        answers["stack"],
        override=override,
        description=answers.get("description", ""),
        prefer_installed_backends=not prompt_only,
        available_backends=available_backends,
        quality_scores=quality_scores or None,
    )
    return _ScaffoldRouting(
        phase_backends=phase_backends,
        merged_groups=merge_adjacent_phases(phase_backends),
        all_phases=all_phases,
        route_plan=PhaseRoutePlan.from_pairs(phase_backends),
        available_backends=available_backends,
    )


def _require_ready_backends(
    routing: _ScaffoldRouting,
    backend_statuses: dict[str, BackendStatus],
    *,
    prompt_only: bool,
) -> None:
    if prompt_only:
        return
    if not routing.available_backends:
        _render_backend_readiness_notice(
            backend_statuses,
            required_backends={
                backend for backend, status in backend_statuses.items() if status.installed
            },
        )
        raise typer.Exit(1)

    for backend in routing.required_backends:
        status = backend_statuses.get(backend, BackendStatus(False, False))
        if not status.installed:
            console.print(
                "\n[red]No ready AI tool is available.[/red]"
                "\n[dim]Run `forge doctor`, complete one recommended setup path, then retry.[/dim]"
            )
            raise typer.Exit(1)
        if status.ready is not True:
            _render_backend_readiness_notice(backend_statuses, required_backends={backend})
            raise typer.Exit(1)


def _load_scaffold_context(
    answers: dict,
    forge_config: dict,
) -> _LoadedScaffoldContext:
    conventions_profile = forge_config.get("conventions_profile", "default")
    if conventions_profile == "default":
        conventions, convention_warnings = load_conventions(stack=answers["stack"])
    else:
        conventions, convention_warnings = load_conventions(
            stack=answers["stack"],
            profile=conventions_profile,
        )
    convention_bundle = load_conventions_bundle(
        stack=answers["stack"],
        profile=conventions_profile,
    )
    claude_md_template = load_claude_md_template()

    warnings = list(convention_warnings)
    answer_extensions: dict[str, object] = {}
    selected_design_template = answers.get("design_template")
    if selected_design_template:
        design_content, design_warnings = load_design_template(selected_design_template)
        warnings.extend(design_warnings)
        if design_content:
            answer_extensions.update(
                {
                    "design_template_content": design_content,
                    "design_template_label": DESIGN_TEMPLATE_OPTIONS[
                        selected_design_template
                    ].label,
                }
            )

    media_asset_count = 0
    media_source_dir: Path | None = None
    selected_collection = answers.get("media_collection")
    if selected_collection:
        collection_dir = MEDIA_DIR / selected_collection
        media_files = scan_assets(collection_dir)
        if media_files:
            answer_extensions["media_assets_manifest"] = build_asset_manifest(
                media_files,
                target_asset_dir(answers["stack"]),
            )
            media_asset_count = len(media_files)
            media_source_dir = collection_dir

    return _LoadedScaffoldContext(
        conventions=conventions,
        convention_bundle=convention_bundle,
        claude_md_template=claude_md_template,
        conventions_profile=conventions_profile,
        warnings=tuple(warnings),
        answer_extensions=answer_extensions,
        media_collection=selected_collection,
        media_asset_count=media_asset_count,
        media_source_dir=media_source_dir,
    )


def _reject_secret_inputs(answers: dict) -> None:
    fields_to_scan = {
        "name": answers.get("name", ""),
        "description": answers.get("description", ""),
        "extra": answers.get("extra", ""),
    }
    services = answers.get("services", [])
    if services:
        fields_to_scan["services"] = " ".join(services)
    for key, value in (answers.get("project_brief") or {}).items():
        if isinstance(value, str) and value:
            fields_to_scan[f"project brief {key}"] = value

    for field_name, text in fields_to_scan.items():
        if text and check_for_secrets(text):
            console.print(
                f"\n[red bold]Forge found content in {field_name} that looks like a "
                "credential.[/red bold]"
                "\n[red]Remove it and use a placeholder before continuing.[/red]"
            )
            raise typer.Exit(1)


def _resolve_scaffold_target(
    answers: dict,
    forge_config: dict,
    *,
    resume: bool,
    prompt_only: bool,
) -> Path:
    base_dir = Path(forge_config.get("projects_dir") or Path.cwd())
    project_dir = base_dir / answers["name"]
    if resume and not project_dir.is_dir():
        console.print(
            status_line(
                "Forge could not find the partial project to resume. Use the original project "
                "name and working directory, then repeat the command.",
                accent="amber",
            )
        )
        raise typer.Exit(1)
    if not resume and not prompt_only:
        return _resolve_project_dir(base_dir, answers)
    return project_dir


def _render_execution_preflight(
    *,
    answers: dict,
    routing: _ScaffoldRouting,
    project_dir: Path,
    backend_models: dict[str, str],
    model_override: str | None,
    approval_mode: str,
    completed_phases: set[str],
    agents: bool,
    verify: bool,
) -> None:
    selected_backends = sorted(routing.required_backends)
    model_summary = ", ".join(
        f"{backend}={model_override or backend_models.get(backend) or 'provider default'}"
        for backend in selected_backends
    )
    minimum_minutes = max(1, routing.route_plan.execution_window_count * 2)
    maximum_minutes = max(5, routing.route_plan.execution_window_count * 15)
    remaining_provider_calls = len(routing.phase_backends) - len(completed_phases)
    provider_call_summary = (
        f"typically {remaining_provider_calls * 4}-{remaining_provider_calls * 8} "
        "(planner + 2-6 tasks + reconciliation per remaining phase)"
        if agents
        else f"{remaining_provider_calls} (one per remaining phase)"
    )
    previous_duration = latest_scaffold_duration(answers["stack"])
    history_summary = (
        f"Last {answers['stack']} scaffold: {_format_duration(previous_duration)} "
        "(local measurement)"
        if previous_duration is not None
        else f"Last {answers['stack']} scaffold: no measured duration yet"
    )

    lines = [
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
    lines.extend(
        _provider_commitment_lines(
            routing.phase_backends,
            completed_phases,
            agents=agents,
        )
    )
    lines.extend(
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
            grouped_lines(lines),
            title="Execution Preflight",
            accent="amber" if approval_mode == "unsafe" else "aqua",
        )
    )


def _copy_scaffold_media(answers: dict, source_dir: Path | None, project_dir: Path) -> None:
    if not answers.get("media_assets_manifest") or source_dir is None:
        return
    copy_result = copy_assets(source_dir, project_dir, answers["stack"])
    if copy_result.copied:
        console.print(
            status_line(
                f"Copied {copy_result.copied} media assets to {copy_result.target_dir}",
                accent="aqua",
            )
        )
    for warning in copy_result.warnings:
        console.print(f"[yellow]{warning}[/yellow]")


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
            help="Media collection name from the Forge media folder to import.",
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
        console.print(
            status_line(
                "Resume works only on a live run. Remove `--dry-run` or `--export`, then repeat "
                "the original command."
            )
        )
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

    if name and stack and description:
        request = NonInteractiveScaffoldRequest(
            name=name,
            stack=stack,
            description=description,
            docker=docker,
            design_template=design_template,
            media=media,
            no_media=no_media,
            auth_provider=auth_provider,
            services=services,
            ci=ci,
            ci_template=ci_template,
            ci_actions=ci_actions,
            extra=extra,
            demo_mode=demo,
        )
        try:
            answers = request.resolve(
                list_media_collection_names=lambda: tuple(
                    collection.name for collection in list_collections()
                )
            )
        except ScaffoldRequestError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from exc
    else:
        answers = collect_answers(
            docker_available=forge_config.get("docker_available", True),
        )
        if answers.get("agents"):
            agents = True

    routing = _plan_scaffold_routing(
        answers,
        override=use,
        prompt_only=prompt_only,
        backend_statuses=backend_statuses,
    )
    console.print()
    _render_routing_plan(routing.route_plan)
    _require_ready_backends(routing, backend_statuses, prompt_only=prompt_only)

    backend_models: dict[str, str] = forge_config.get("backend_models", {})
    try:
        scaffold_context = _load_scaffold_context(answers, forge_config)
    except ConventionValidationError as exc:
        console.print(
            status_line(
                "Forge could not load the active conventions. Run `forge conventions "
                "validate`, then fix or restore the convention files.",
                accent="amber",
            )
        )
        raise typer.Exit(1) from exc

    for warning in scaffold_context.warnings:
        console.print(f"[yellow]{warning}[/yellow]")
    answers.update(scaffold_context.answer_extensions)
    _render_loaded_context(
        routing.required_backends,
        backend_models,
        model_override=model,
        approval_mode=approval_mode,
        conventions=scaffold_context.conventions,
        claude_md_loaded=bool(scaffold_context.claude_md_template),
        design_template_label=answers.get("design_template_label"),
        media_collection=scaffold_context.media_collection,
        media_asset_count=scaffold_context.media_asset_count,
        convention_sources=scaffold_context.convention_bundle.contributions,
        conventions_profile=scaffold_context.conventions_profile,
        project_brief_added=any((answers.get("project_brief") or {}).values()),
        project_context_files=len(answers.get("context_sources", [])),
        verbose=verbose,
    )

    _reject_secret_inputs(answers)
    project_dir = _resolve_scaffold_target(
        answers,
        forge_config,
        resume=resume,
        prompt_only=prompt_only,
    )

    prompt_plan = ScaffoldPromptPlan.build(
        route_plan=routing.route_plan,
        merged_groups=routing.merged_groups,
        all_phases=routing.all_phases,
        answers=answers,
        conventions=scaffold_context.conventions,
        claude_md_template=scaffold_context.claude_md_template,
    )

    if dry_run or export:
        for preview in prompt_plan.previews:
            if dry_run:
                if len(prompt_plan.previews) > 1:
                    console.print()
                    console.print(
                        make_panel(
                            grouped_lines(
                                [
                                    Text(preview.label, style="bold #F7F9FF"),
                                    Text(f"Backend: {preview.backend}", style="#8893B3"),
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
                console.print(preview.content)

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
            try:
                export_path.parent.mkdir(parents=True, exist_ok=True)
                export_path.write_text(prompt_plan.export_text())
            except OSError as exc:
                console.print()
                console.print(
                    status_line(
                        "Forge could not save the prompt at that location. Choose a writable "
                        "path and run the export again.",
                        accent="amber",
                    )
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
            phase_prompts=prompt_plan.progress_records,
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
        console.print(
            status_line(
                f"Total prompt length: {prompt_plan.total_live_characters} chars across "
                f"{len(prompt_plan.live)} phase(s)",
                accent="violet",
            )
        )

    _render_execution_preflight(
        answers=answers,
        routing=routing,
        project_dir=project_dir,
        backend_models=backend_models,
        model_override=model,
        approval_mode=approval_mode,
        completed_phases=completed_phases,
        agents=bool(agents),
        verify=verify,
    )
    _copy_scaffold_media(
        answers,
        scaffold_context.media_source_dir,
        project_dir,
    )

    scaffold_start = time.monotonic()

    orchestrated_runner = None
    if agents:
        from projectforge.orchestrator import run_phase_orchestrated

        orchestrated_runner = run_phase_orchestrated

    phase_executor = ScaffoldPhaseExecutor(
        console=console,
        plan=routing.route_plan,
        phase_prompts=prompt_plan.progress_records,
        completed_phases=completed_phases,
        settings=PhaseExecutionSettings(
            project_dir=project_dir,
            stack=answers["stack"],
            conventions=scaffold_context.conventions,
            model_override=model,
            backend_models=backend_models,
            verbose=verbose,
            approval_mode=approval_mode,
            allow_unsafe=allow_unsafe,
            use_agents=bool(agents),
        ),
        dependencies=PhaseExecutionDependencies(
            run_phase=run_ai,
            run_parallel=run_ai_parallel,
            mark_phase=mark_phase,
            run_orchestrated=orchestrated_runner,
        ),
    )
    try:
        phase_execution = phase_executor.execute()
    except PhaseExecutionError as exc:
        for failure in exc.failures:
            _render_phase_failure(failure.backend, failure.label, failure.exit_code)
        raise typer.Exit(exc.failures[0].exit_code) from exc

    try:
        complete_scaffold(
            console=console,
            settings=ScaffoldCompletionSettings(
                answers=answers,
                phase_backends=routing.phase_backends,
                project_dir=project_dir,
                conventions=scaffold_context.conventions,
                model_override=model,
                backend_models=backend_models,
                approval_mode=approval_mode,
                convention_sources=scaffold_context.convention_bundle.contributions,
                verification_requested=verify,
                verbose=verbose,
                scaffold_started_at=scaffold_start,
                sound_enabled=forge_config.get("sound", False),
                open_editor=open_editor,
                preferred_editor=forge_config.get("preferred_editor", ""),
                agent_stats=phase_execution.agent_stats,
            ),
            dependencies=ScaffoldCompletionDependencies(
                write_manifest=write_scaffold_manifest,
                ensure_git=ensure_git_init,
                verify=verify_scaffold,
                write_verification=write_verification_report,
                append_quality=append_quality_signal,
                run_hook=run_post_scaffold_hook,
                append_log=append_scaffold_log,
                record_preferences=record_preferences,
                render_dashboard=render_dashboard,
                write_card=write_card,
                inject_readme_badge=inject_badge_into_readme,
                play_sound=play_completion_sound,
                open_project=open_in_editor,
            ),
        )
    except ScaffoldRecordError as exc:
        console.print(
            status_line(
                "Forge created the project files but could not save the scaffold record. Keep "
                "the generated files, make the project folder writable, then scaffold a new "
                "target.",
                accent="amber",
            )
        )
        raise typer.Exit(1) from exc
