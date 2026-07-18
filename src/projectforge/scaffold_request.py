"""Validate non-interactive scaffold flags and assemble prompt-ready answers."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import NotRequired, TypedDict

from projectforge.design_templates import (
    DESIGN_TEMPLATE_OPTIONS,
    design_template_ids_for_stack,
    design_template_supported_for_stack,
)
from projectforge.scaffold_options import (
    AUTH_PROVIDER_OPTIONS,
    CI_TEMPLATE_MODES,
    auth_provider_ids_for_stack,
    auth_provider_supported_for_stack,
    ci_action_ids_for_stack,
)
from projectforge.stacks import STACK_META

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


class CiAnswers(TypedDict):
    """Normalized CI choices consumed by prompt assembly."""

    include: bool
    mode: str | None
    actions: list[str]


class ScaffoldAnswers(TypedDict):
    """Core answer schema shared by interactive and flag-driven scaffolds."""

    name: str
    stack: str
    description: str
    docker: bool
    design_template: str | None
    media_collection: str | None
    auth_provider: str | None
    services: list[str]
    ci: CiAnswers
    extra: str
    demo_mode: bool
    agents: NotRequired[bool]


class ScaffoldRequestError(ValueError):
    """A flag combination that cannot describe a supported scaffold."""


@dataclass(frozen=True)
class NonInteractiveScaffoldRequest:
    """Raw CLI values supplied for a flag-driven scaffold."""

    name: str
    stack: str
    description: str
    docker: bool | None = None
    design_template: str | None = None
    media: str | None = None
    no_media: bool = False
    auth_provider: str | None = None
    services: str | None = None
    ci: bool | None = None
    ci_template: str | None = None
    ci_actions: str | None = None
    extra: str | None = None
    demo_mode: bool = True

    def resolve(
        self,
        *,
        list_media_collection_names: Callable[[], Sequence[str]],
    ) -> ScaffoldAnswers:
        """Validate stack-specific options and return the canonical answer schema."""
        stack = self._resolve_stack()
        self._validate_auth_provider(stack)
        self._validate_design_template(stack)
        ci_answers = self._resolve_ci(stack)

        stack_meta = STACK_META[stack]
        docker = self.docker if self.docker is not None else stack_meta.docker_default
        return {
            "name": self.name.strip(),
            "stack": stack,
            "description": self.description.strip(),
            "docker": docker,
            "design_template": self.design_template,
            "media_collection": self._resolve_media_collection(list_media_collection_names),
            "auth_provider": self.auth_provider,
            "services": [service.strip() for service in self.services.split(",")]
            if self.services
            else [],
            "ci": ci_answers,
            "extra": (self.extra or "").strip(),
            "demo_mode": self.demo_mode,
        }

    def _resolve_stack(self) -> str:
        stack = STACK_ALIASES.get(self.stack.lower())
        if stack is not None:
            return stack
        valid = ", ".join(sorted(set(STACK_ALIASES.values())))
        raise ScaffoldRequestError(f"That stack is not available. Choose one of: {valid}.")

    def _validate_auth_provider(self, stack: str) -> None:
        if not self.auth_provider:
            return
        if self.auth_provider not in AUTH_PROVIDER_OPTIONS:
            valid = ", ".join(sorted(AUTH_PROVIDER_OPTIONS))
            raise ScaffoldRequestError(
                f"That authentication option is not available. Choose one of: {valid}."
            )
        if auth_provider_supported_for_stack(stack, self.auth_provider):
            return
        allowed = auth_provider_ids_for_stack(stack)
        if allowed:
            valid = ", ".join(allowed)
            raise ScaffoldRequestError(
                f"That authentication option does not work with this stack. Choose one of: {valid}."
            )
        raise ScaffoldRequestError(
            "This stack does not support an authentication option. Remove `--auth-provider` "
            "and try again."
        )

    def _validate_design_template(self, stack: str) -> None:
        if not self.design_template:
            return
        if self.design_template not in DESIGN_TEMPLATE_OPTIONS:
            valid = ", ".join(sorted(DESIGN_TEMPLATE_OPTIONS))
            raise ScaffoldRequestError(
                f"That design template is not available. Choose one of: {valid}."
            )
        if design_template_supported_for_stack(stack, self.design_template):
            return
        allowed = design_template_ids_for_stack(stack)
        if allowed:
            valid = ", ".join(allowed)
            raise ScaffoldRequestError(
                f"That design template does not work with this stack. Choose one of: {valid}."
            )
        raise ScaffoldRequestError(
            "This stack does not support a design template. Remove `--design-template` and "
            "try again."
        )

    def _resolve_ci(self, stack: str) -> CiAnswers:
        if self.ci_template and self.ci_template not in CI_TEMPLATE_MODES:
            valid = ", ".join(CI_TEMPLATE_MODES)
            raise ScaffoldRequestError(
                f"That CI template is not available. Choose one of: {valid}."
            )

        include = self.ci if self.ci is not None else bool(self.ci_template or self.ci_actions)
        mode: str | None = None
        actions: list[str] = []
        if include:
            mode = self.ci_template or ("questionnaire" if self.ci_actions else "blank-template")
            allowed_actions = set(ci_action_ids_for_stack(stack))
            if self.ci_actions:
                actions = [
                    action.strip() for action in self.ci_actions.split(",") if action.strip()
                ]
                if any(action not in allowed_actions for action in actions):
                    valid = ", ".join(sorted(allowed_actions))
                    raise ScaffoldRequestError(
                        f"Some CI checks do not work with this stack. Choose from: {valid}."
                    )
            elif mode == "questionnaire":
                actions = ci_action_ids_for_stack(stack)
        return {"include": include, "mode": mode, "actions": actions}

    def _resolve_media_collection(
        self,
        list_media_collection_names: Callable[[], Sequence[str]],
    ) -> str | None:
        if self.no_media:
            return None
        if self.media:
            return self.media
        collections = list_media_collection_names()
        return collections[0] if len(collections) == 1 else None
