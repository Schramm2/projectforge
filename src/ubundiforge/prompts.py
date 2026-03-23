"""Interactive question flow for gathering project details."""

import re

import questionary

from ubundiforge.design_templates import (
    DESIGN_TEMPLATE_OPTIONS,
    design_template_choices_for_stack,
)
from ubundiforge.media_assets import list_collections
from ubundiforge.questionary_theme import (
    prompt_checkbox,
    prompt_confirm,
    prompt_select,
    prompt_text,
)
from ubundiforge.scaffold_options import (
    AUTH_PROVIDER_OPTIONS,
    CI_ACTION_OPTIONS,
    auth_provider_choices_for_stack,
    ci_action_ids_for_stack,
)
from ubundiforge.stacks import STACK_META
from ubundiforge.ui import create_console, grouped_lines, make_panel, muted, status_line, subtle

STACK_CHOICES = [
    questionary.Choice("Next.js + React (frontend or fullstack)", value="nextjs"),
    questionary.Choice("Python API (FastAPI)", value="fastapi"),
    questionary.Choice("FastAPI + AI/LLM (OpenAI, pgvector, embeddings)", value="fastapi-ai"),
    questionary.Choice("Both (Next.js frontend + FastAPI backend)", value="both"),
    questionary.Choice("Python CLI Tool (Typer + Rich)", value="python-cli"),
    questionary.Choice("TypeScript npm Package", value="ts-package"),
    questionary.Choice("Python Worker / Scheduled Service", value="python-worker"),
]


def _validate_project_name(name: str) -> bool | str:
    """Validate that the project name is a valid directory name."""
    if not name.strip():
        return "Project name cannot be empty."
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$", name):
        return (
            "Must start with a letter/number and contain only"
            " letters, numbers, dots, hyphens, or underscores."
        )
    return True


def _stack_label(stack: str) -> str:
    """Return the display label for a stack identifier."""
    for choice in STACK_CHOICES:
        if choice.value == stack:
            return str(choice.title)
    return stack


def _has_customizations(answers: dict) -> bool:
    """Return whether the current answer set includes any advanced options."""
    ci = answers.get("ci", {})
    return bool(
        answers.get("auth_provider")
        or answers.get("services")
        or ci.get("include")
        or answers.get("extra")
    )


def _normalize_answers_for_stack(answers: dict) -> None:
    """Drop selections that no longer apply after a stack change."""
    stack = answers.get("stack", "")

    if not design_template_choices_for_stack(stack):
        answers["design_template"] = None

    if not auth_provider_choices_for_stack(stack):
        answers["auth_provider"] = None

    meta = STACK_META.get(stack)
    allowed_services = set(meta.services if meta else [])
    answers["services"] = [
        service for service in answers.get("services", []) if service in allowed_services
    ]

    ci = answers.get("ci", {}) or {}
    if not ci.get("include"):
        answers["ci"] = {"include": False, "mode": None, "actions": []}
        return

    filtered_actions = [
        action for action in ci.get("actions", []) if action in set(ci_action_ids_for_stack(stack))
    ]
    answers["ci"] = {
        "include": True,
        "mode": ci.get("mode") or "blank-template",
        "actions": filtered_actions,
    }


def _ask_services(stack: str, current: list[str] | None = None) -> list[str]:
    """Ask the user which services to include, based on the stack's typical services."""
    meta = STACK_META.get(stack)
    if not meta or not meta.services:
        return []

    current = current or []
    choices = [questionary.Choice(s, value=s, checked=s in current) for s in meta.services]
    selected = prompt_checkbox(
        "Include any services?",
        choices=choices,
    ).ask()

    if selected is None:
        raise SystemExit(0)

    return selected


def _ask_auth_provider(stack: str, current: str | None = None) -> str | None:
    """Ask whether to include auth, then which provider to use."""
    choices = auth_provider_choices_for_stack(stack)
    if not choices:
        return None

    include_auth = prompt_confirm(
        "Add authentication scaffolding",
        default=current is not None,
    ).ask()
    if include_auth is None:
        raise SystemExit(0)
    if not include_auth:
        return None

    provider = prompt_select(
        "Choose the auth provider",
        choices=[
            questionary.Choice(
                f"{label} — {AUTH_PROVIDER_OPTIONS[value].prompt_description}",
                value=value,
            )
            for value, label in choices
        ],
        default=current,
    ).ask()
    if provider is None:
        raise SystemExit(0)

    return provider


def _ask_design_template(stack: str, current: str | None = None) -> str | None:
    """Ask whether to apply a design template, then which one to use."""
    choices = design_template_choices_for_stack(stack)
    if not choices:
        return None

    include_design_template = prompt_confirm(
        "Apply a design template or brand guide",
        default=current is not None,
    ).ask()
    if include_design_template is None:
        raise SystemExit(0)
    if not include_design_template:
        return None

    template_id = prompt_select(
        "Choose the design direction",
        choices=[
            questionary.Choice(
                f"{label} — {DESIGN_TEMPLATE_OPTIONS[value].prompt_description}",
                value=value,
            )
            for value, label in choices
        ],
        default=current,
    ).ask()
    if template_id is None:
        raise SystemExit(0)

    return template_id


def _ask_ci_config(stack: str, current: dict | None = None) -> dict:
    """Ask whether to include CI and how detailed the scaffold should be."""
    current = current or {"include": False, "mode": None, "actions": []}
    include_ci = prompt_confirm(
        "Add GitHub Actions CI",
        default=bool(current.get("include")),
    ).ask()
    if include_ci is None:
        raise SystemExit(0)
    if not include_ci:
        return {
            "include": False,
            "mode": None,
            "actions": [],
        }

    mode = prompt_select(
        "Choose the CI starting point",
        choices=[
            questionary.Choice(
                "Questionnaire — choose the CI actions to include",
                value="questionnaire",
            ),
            questionary.Choice(
                "Blank template — scaffold a starter workflow with TODOs",
                value="blank-template",
            ),
        ],
        default=current.get("mode") or "questionnaire",
    ).ask()
    if mode is None:
        raise SystemExit(0)

    actions: list[str] = []
    if mode == "questionnaire":
        action_ids = ci_action_ids_for_stack(stack)
        actions = prompt_checkbox(
            "Choose the CI actions to include",
            choices=[
                questionary.Choice(
                    f"{CI_ACTION_OPTIONS[action_id].label} — "
                    f"{CI_ACTION_OPTIONS[action_id].prompt_description}",
                    value=action_id,
                    checked=action_id in current.get("actions", []),
                )
                for action_id in action_ids
            ],
        ).ask()
        if actions is None:
            raise SystemExit(0)

    return {
        "include": True,
        "mode": mode,
        "actions": actions,
    }


def _ask_project_basics(answers: dict, *, docker_available: bool) -> None:
    """Collect or edit the core project details."""
    console = create_console()

    name = prompt_text(
        "Name the project",
        default=answers.get("name", ""),
        validate=_validate_project_name,
    ).ask()
    if name is None:
        raise SystemExit(0)
    answers["name"] = name.strip()

    stack = prompt_select(
        "Choose the primary stack",
        choices=STACK_CHOICES,
        default=answers.get("stack"),
    ).ask()
    if stack is None:
        raise SystemExit(0)
    answers["stack"] = stack
    _normalize_answers_for_stack(answers)

    description = prompt_text(
        "Brief description",
        default=answers.get("description", ""),
    ).ask()
    if description is None:
        raise SystemExit(0)
    answers["description"] = description.strip()

    meta = STACK_META.get(stack)
    if not docker_available:
        answers["docker"] = False
        console.print(status_line("Docker not detected — skipping Docker setup.", accent="amber"))
        return

    docker_default = answers.get("docker")
    if docker_default is None:
        docker_default = meta.docker_default if meta else True
    docker = prompt_confirm(
        "Include Docker setup",
        default=bool(docker_default),
    ).ask()
    if docker is None:
        raise SystemExit(0)
    answers["docker"] = docker


def _ask_design_and_media(answers: dict) -> None:
    """Collect or edit design template and media choices."""
    stack = answers["stack"]
    answers["design_template"] = _ask_design_template(stack, answers.get("design_template"))

    media_collection: str | None = None
    collections = list_collections()
    current_media = answers.get("media_collection")
    if collections:
        if len(collections) == 1:
            collection = collections[0]
            use_it = prompt_confirm(
                f"Use {collection.name} media assets? ({collection.file_count} files)",
                default=current_media == collection.name or current_media is None,
            ).ask()
            if use_it is None:
                raise SystemExit(0)
            if use_it:
                media_collection = collection.name
        else:
            choices = [
                questionary.Choice(
                    f"{collection.name} ({collection.file_count} files)",
                    value=collection.name,
                )
                for collection in collections
            ]
            choices.append(questionary.Choice("None", value=""))
            media_collection = prompt_select(
                "Which media collection?",
                choices=choices,
                default=current_media or "",
            ).ask()
            if media_collection is None:
                raise SystemExit(0)
            media_collection = media_collection or None

    answers["media_collection"] = media_collection


def _ask_customizations(answers: dict) -> None:
    """Collect or edit advanced integration options."""
    customize = prompt_confirm(
        "Customize further? (auth, services, CI, extras)",
        default=_has_customizations(answers),
    ).ask()
    if customize is None:
        raise SystemExit(0)

    if not customize:
        answers["auth_provider"] = None
        answers["services"] = []
        answers["ci"] = {"include": False, "mode": None, "actions": []}
        answers["extra"] = ""
        return

    answers["auth_provider"] = _ask_auth_provider(answers["stack"], answers.get("auth_provider"))
    answers["services"] = _ask_services(answers["stack"], answers.get("services"))
    answers["ci"] = _ask_ci_config(answers["stack"], answers.get("ci"))

    extra = prompt_text(
        "Add any extra instructions",
        default=answers.get("extra", ""),
    ).ask()
    if extra is None:
        raise SystemExit(0)
    answers["extra"] = extra.strip()


def _ask_demo_mode(answers: dict) -> None:
    """Collect or edit demo mode preference."""
    demo_mode = prompt_confirm(
        "Enable demo mode? (runs without real API keys)",
        default=bool(answers.get("demo_mode", True)),
    ).ask()
    if demo_mode is None:
        raise SystemExit(0)
    answers["demo_mode"] = demo_mode


def _ask_execution_mode(answers: dict) -> None:
    """Collect or edit execution mode preference."""
    current = answers.get("agents", False)
    default_value = "agents" if current else "standard"
    mode = prompt_select(
        "Execution mode",
        choices=[
            questionary.Choice(
                "Multi-agent (recommended): dispatches parallel subagents per phase for higher quality",
                value="agents",
            ),
            questionary.Choice(
                "Standard: single sequential execution, faster but less thorough",
                value="standard",
            ),
        ],
        default=default_value,
    ).ask()
    if mode is None:
        raise SystemExit(0)
    answers["agents"] = mode == "agents"


def _ci_summary(ci: dict) -> str:
    """Return a compact summary of the selected CI configuration."""
    if not ci.get("include"):
        return "No"
    mode = ci.get("mode") or "blank-template"
    actions = ci.get("actions", [])
    if mode == "questionnaire" and actions:
        return f"Questionnaire ({', '.join(actions)})"
    if mode == "questionnaire":
        return "Questionnaire"
    return "Blank template"


def _review_answers(answers: dict) -> str:
    """Show a review panel and ask what to do next."""
    console = create_console()
    design_id = answers.get("design_template")
    design_label = (
        DESIGN_TEMPLATE_OPTIONS[design_id].label if design_id in DESIGN_TEMPLATE_OPTIONS else "None"
    )
    auth_provider = answers.get("auth_provider")
    auth_label = AUTH_PROVIDER_OPTIONS[auth_provider].label if auth_provider else "None"
    services = ", ".join(answers.get("services", [])) or "None"
    extra = answers.get("extra", "")
    extra_summary = extra if not extra else (extra[:97] + "..." if len(extra) > 100 else extra)

    console.print()
    console.print(
        make_panel(
            grouped_lines(
                [
                    subtle(f"Name: {answers.get('name')}"),
                    subtle(f"Stack: {_stack_label(answers.get('stack', ''))}"),
                    subtle(f"Description: {answers.get('description')}"),
                    subtle(f"Docker: {'Yes' if answers.get('docker') else 'No'}"),
                    subtle(f"Design template: {design_label}"),
                    subtle(f"Media collection: {answers.get('media_collection') or 'None'}"),
                    subtle(f"Auth: {auth_label}"),
                    subtle(f"Services: {services}"),
                    subtle(f"CI: {_ci_summary(answers.get('ci', {}))}"),
                    subtle(f"Demo mode: {'Yes' if answers.get('demo_mode') else 'No'}"),
                    subtle(f"Execution: {'Multi-agent' if answers.get('agents') else 'Standard'}"),
                    muted(f"Extra instructions: {extra_summary or 'None'}"),
                ]
            ),
            title="Review Choices",
            accent="amber",
        )
    )

    action = prompt_select(
        "What would you like to do?",
        choices=[
            questionary.Choice("Scaffold project", value="scaffold"),
            questionary.Choice("Edit basics", value="basics"),
            questionary.Choice("Edit design and media", value="appearance"),
            questionary.Choice("Edit auth, services, CI, and extras", value="integrations"),
            questionary.Choice("Edit demo mode", value="demo"),
            questionary.Choice("Edit execution mode", value="execution"),
            questionary.Choice("Cancel", value="cancel"),
        ],
        default="scaffold",
    ).ask()
    if action is None:
        raise SystemExit(0)
    return action


def collect_answers(docker_available: bool = True) -> dict:
    """Run the interactive prompt flow and return answers as a dict."""
    console = create_console()
    console.print()

    answers: dict = {
        "name": "",
        "stack": "nextjs",
        "description": "",
        "docker": None,
        "design_template": None,
        "media_collection": None,
        "auth_provider": None,
        "services": [],
        "ci": {"include": False, "mode": None, "actions": []},
        "extra": "",
        "demo_mode": True,
        "agents": False,
    }

    _ask_project_basics(answers, docker_available=docker_available)

    # Smart defaults — offer to skip remaining questions if patterns detected
    from ubundiforge.preferences import get_defaults

    defaults = get_defaults()
    # Filter to questions that haven't been answered yet (not basics)
    applicable = {
        k: v for k, v in defaults.items() if k not in ("name", "description", "stack", "docker")
    }

    if applicable:
        # Format as human-readable labels
        label_map = {
            "auth_provider": "Auth",
            "demo_mode": "Demo mode",
            "design_template": "Design template",
        }
        display_parts = []
        for k, v in applicable.items():
            label = label_map.get(k, k)
            display_val = v if v not in ("True", "False") else ("yes" if v == "True" else "no")
            display_parts.append(f"{label}: {display_val}")

        console.print(subtle(f"  Your usual setup: {', '.join(display_parts)}"))
        use_defaults = prompt_confirm(
            "Use your usual setup?",
            default=True,
        ).ask()
        if use_defaults:
            # Pre-fill answers with defaults but still go to review screen
            for k, v in applicable.items():
                if v == "True":
                    answers[k] = True
                elif v == "False":
                    answers[k] = False
                else:
                    answers[k] = v
            # Skip to review screen — DO NOT return early
            # Jump past _ask_design_and_media, _ask_customizations, _ask_demo_mode
            # and go straight to the review loop
        else:
            # User declined defaults — proceed with full question flow
            _ask_design_and_media(answers)
            _ask_customizations(answers)
            _ask_demo_mode(answers)
            _ask_execution_mode(answers)
    else:
        _ask_design_and_media(answers)
        _ask_customizations(answers)
        _ask_demo_mode(answers)
        _ask_execution_mode(answers)

    while True:
        action = _review_answers(answers)
        if action == "scaffold":
            return answers
        if action == "basics":
            _ask_project_basics(answers, docker_available=docker_available)
            continue
        if action == "appearance":
            _ask_design_and_media(answers)
            continue
        if action == "integrations":
            _ask_customizations(answers)
            continue
        if action == "demo":
            _ask_demo_mode(answers)
            continue
        if action == "execution":
            _ask_execution_mode(answers)
            continue
        raise SystemExit(0)
