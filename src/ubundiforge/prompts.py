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
from ubundiforge.ui import create_console, status_line

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


def _ask_services(stack: str) -> list[str]:
    """Ask the user which services to include, based on the stack's typical services."""
    meta = STACK_META.get(stack)
    if not meta or not meta.services:
        return []

    choices = [questionary.Choice(s, value=s) for s in meta.services]
    selected = prompt_checkbox(
        "Include any services?",
        choices=choices,
    ).ask()

    if selected is None:
        raise SystemExit(0)

    return selected


def _ask_auth_provider(stack: str) -> str | None:
    """Ask whether to include auth, then which provider to use."""
    choices = auth_provider_choices_for_stack(stack)
    if not choices:
        return None

    include_auth = prompt_confirm(
        "Add authentication scaffolding",
        default=False,
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
    ).ask()
    if provider is None:
        raise SystemExit(0)

    return provider


def _ask_design_template(stack: str) -> str | None:
    """Ask whether to apply a design template, then which one to use."""
    choices = design_template_choices_for_stack(stack)
    if not choices:
        return None

    include_design_template = prompt_confirm(
        "Apply a design template or brand guide",
        default=False,
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
    ).ask()
    if template_id is None:
        raise SystemExit(0)

    return template_id


def _ask_ci_config(stack: str) -> dict:
    """Ask whether to include CI and how detailed the scaffold should be."""
    include_ci = prompt_confirm(
        "Add GitHub Actions CI",
        default=False,
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


def collect_answers(docker_available: bool = True) -> dict:
    """Run the interactive prompt flow and return answers as a dict."""
    console = create_console()
    console.print()

    name = prompt_text(
        "Name the project",
        validate=_validate_project_name,
    ).ask()
    if name is None:
        raise SystemExit(0)

    stack = prompt_select(
        "Choose the primary stack",
        choices=STACK_CHOICES,
    ).ask()
    if stack is None:
        raise SystemExit(0)

    description = prompt_text("Brief description").ask()
    if description is None:
        raise SystemExit(0)

    meta = STACK_META.get(stack)
    if not docker_available:
        docker = False
        console.print(status_line("Docker not detected — skipping Docker setup.", accent="amber"))
    else:
        docker_default = meta.docker_default if meta else True
        docker = prompt_confirm(
            "Include Docker setup",
            default=docker_default,
        ).ask()
        if docker is None:
            raise SystemExit(0)

    design_template = _ask_design_template(stack)

    # Media assets from media/<collection>/
    media_collection: str | None = None
    collections = list_collections()
    if collections:
        if len(collections) == 1:
            c = collections[0]
            use_it = prompt_confirm(
                f"Use {c.name} media assets? ({c.file_count} files)",
                default=True,
            ).ask()
            if use_it is None:
                raise SystemExit(0)
            if use_it:
                media_collection = c.name
        else:
            choices = [
                questionary.Choice(
                    f"{c.name} ({c.file_count} files)",
                    value=c.name,
                )
                for c in collections
            ]
            choices.append(questionary.Choice("None", value=""))
            media_collection = prompt_select(
                "Which media collection?",
                choices=choices,
            ).ask()
            if media_collection is None:
                raise SystemExit(0)
            media_collection = media_collection or None

    customize = prompt_confirm(
        "Customize further? (auth, services, CI, extras)",
        default=False,
    ).ask()
    if customize is None:
        raise SystemExit(0)

    auth_provider = None
    services = []
    ci = {"include": False, "mode": None, "actions": []}
    extra = ""

    if customize:
        auth_provider = _ask_auth_provider(stack)
        services = _ask_services(stack)
        ci = _ask_ci_config(stack)

        extra = prompt_text(
            "Add any extra instructions",
            default="",
        ).ask()
        if extra is None:
            raise SystemExit(0)
        extra = extra.strip()

    demo_mode = prompt_confirm(
        "Enable demo mode? (runs without real API keys)",
        default=True,
    ).ask()
    if demo_mode is None:
        raise SystemExit(0)

    return {
        "name": name.strip(),
        "stack": stack,
        "description": description.strip(),
        "docker": docker,
        "design_template": design_template,
        "media_collection": media_collection,
        "auth_provider": auth_provider,
        "services": services,
        "ci": ci,
        "extra": extra,
        "demo_mode": demo_mode,
    }
