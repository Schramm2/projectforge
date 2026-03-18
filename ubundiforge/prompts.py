"""Interactive question flow for gathering project details."""

import re

import questionary

from ubundiforge.scaffold_options import (
    AUTH_PROVIDER_OPTIONS,
    CI_ACTION_OPTIONS,
    auth_provider_choices_for_stack,
    ci_action_ids_for_stack,
)
from ubundiforge.stacks import STACK_META

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
    selected = questionary.checkbox(
        "Include any of these services? (space to select, enter to confirm):",
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

    include_auth = questionary.confirm(
        "Include authentication?",
        default=False,
    ).ask()
    if include_auth is None:
        raise SystemExit(0)
    if not include_auth:
        return None

    provider = questionary.select(
        "Which auth provider should Forge scaffold?",
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


def _ask_ci_config(stack: str) -> dict:
    """Ask whether to include CI and how detailed the scaffold should be."""
    include_ci = questionary.confirm(
        "Include GitHub Actions CI?",
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

    mode = questionary.select(
        "How should Forge scaffold CI?",
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
        actions = questionary.checkbox(
            "Which CI actions should the workflow include?",
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
    name = questionary.text(
        "Project name:",
        validate=_validate_project_name,
    ).ask()
    if name is None:
        raise SystemExit(0)

    stack = questionary.select(
        "What are we building?",
        choices=STACK_CHOICES,
    ).ask()
    if stack is None:
        raise SystemExit(0)

    description = questionary.text("Brief description:").ask()
    if description is None:
        raise SystemExit(0)

    meta = STACK_META.get(stack)
    if not docker_available:
        docker = False
        from rich.console import Console

        Console().print("[dim]Docker not detected — skipping Docker setup.[/dim]")
    else:
        docker_default = meta.docker_default if meta else True
        docker = questionary.confirm("Include Docker setup?", default=docker_default).ask()
        if docker is None:
            raise SystemExit(0)

    customize = questionary.confirm(
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

        extra = questionary.text(
            "Any extra instructions? (optional, press Enter to skip):",
            default="",
        ).ask()
        if extra is None:
            raise SystemExit(0)
        extra = extra.strip()

    demo_mode = questionary.confirm(
        "Enable demo mode? (project runs without real API keys/secrets)",
        default=True,
    ).ask()
    if demo_mode is None:
        raise SystemExit(0)

    return {
        "name": name.strip(),
        "stack": stack,
        "description": description.strip(),
        "docker": docker,
        "auth_provider": auth_provider,
        "services": services,
        "ci": ci,
        "extra": extra,
        "demo_mode": demo_mode,
    }
