"""Structured scaffold options shared by prompts, CLI validation, and prompt building."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthProviderOption:
    """Metadata for an optional auth provider."""

    label: str
    prompt_description: str
    libraries: dict[str, str]
    env_hints: list[str]


AUTH_PROVIDER_ORDER = ("clerk", "supabase-auth", "authjs", "better-auth")

AUTH_PROVIDER_OPTIONS: dict[str, AuthProviderOption] = {
    "clerk": AuthProviderOption(
        label="Clerk",
        prompt_description="Hosted auth with user management, sessions, and signup flows.",
        libraries={
            "@clerk/nextjs": "Hosted authentication and user management for Next.js",
        },
        env_hints=[
            "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=",
            "CLERK_SECRET_KEY=",
        ],
    ),
    "supabase-auth": AuthProviderOption(
        label="Supabase Auth",
        prompt_description="Supabase-backed authentication for email/password and social login.",
        libraries={
            "@supabase/supabase-js": "Supabase JavaScript client",
            "@supabase/ssr": "Supabase auth helpers for server-rendered Next.js apps",
        },
        env_hints=[
            "NEXT_PUBLIC_SUPABASE_URL=",
            "NEXT_PUBLIC_SUPABASE_ANON_KEY=",
            "SUPABASE_SERVICE_ROLE_KEY=",
        ],
    ),
    "authjs": AuthProviderOption(
        label="Auth.js / NextAuth",
        prompt_description="Flexible self-managed auth for Next.js with provider-based sign-in.",
        libraries={
            "next-auth": "Auth.js integration for Next.js applications",
        },
        env_hints=[
            "AUTH_SECRET=",
            "AUTH_URL=http://localhost:3000",
        ],
    ),
    "better-auth": AuthProviderOption(
        label="Better Auth",
        prompt_description="Self-hosted authentication with app-managed sessions and flows.",
        libraries={
            "better-auth": "Application-managed authentication for modern TypeScript apps",
        },
        env_hints=[
            "BETTER_AUTH_SECRET=",
            "BETTER_AUTH_URL=http://localhost:3000",
        ],
    ),
}

AUTH_SUPPORTED_STACKS = {"nextjs", "both"}


@dataclass(frozen=True)
class CiActionOption:
    """Metadata for a CI action the user can request."""

    label: str
    prompt_description: str


CI_TEMPLATE_MODES = ("questionnaire", "blank-template")

CI_ACTION_OPTIONS: dict[str, CiActionOption] = {
    "lint": CiActionOption(
        label="Lint",
        prompt_description="Run the repo lint command and fail on violations.",
    ),
    "format-check": CiActionOption(
        label="Format check",
        prompt_description="Verify formatting without auto-fixing in CI.",
    ),
    "typecheck": CiActionOption(
        label="Type check",
        prompt_description="Run static type checking for the selected stack.",
    ),
    "build": CiActionOption(
        label="Build",
        prompt_description="Build the project to catch packaging or compile issues.",
    ),
    "unit-tests": CiActionOption(
        label="Unit tests",
        prompt_description="Run the fast unit test suite.",
    ),
    "integration-tests": CiActionOption(
        label="Integration tests",
        prompt_description="Run broader integration coverage when configured.",
    ),
    "docker-build": CiActionOption(
        label="Docker build",
        prompt_description="Build Docker images to validate container setup.",
    ),
}

STACK_CI_ACTIONS: dict[str, list[str]] = {
    "nextjs": ["lint", "typecheck", "build", "unit-tests"],
    "fastapi": ["lint", "format-check", "typecheck", "unit-tests", "integration-tests"],
    "fastapi-ai": [
        "lint",
        "format-check",
        "typecheck",
        "unit-tests",
        "integration-tests",
    ],
    "both": [
        "lint",
        "format-check",
        "typecheck",
        "build",
        "unit-tests",
        "integration-tests",
        "docker-build",
    ],
    "python-cli": ["lint", "format-check", "typecheck", "unit-tests"],
    "ts-package": ["lint", "typecheck", "build", "unit-tests"],
    "python-worker": [
        "lint",
        "format-check",
        "typecheck",
        "unit-tests",
        "docker-build",
    ],
}


def auth_provider_choices_for_stack(stack: str) -> list[tuple[str, str]]:
    """Return ordered auth provider choices for a stack."""
    provider_ids = auth_provider_ids_for_stack(stack)
    return [(provider_id, AUTH_PROVIDER_OPTIONS[provider_id].label) for provider_id in provider_ids]


def auth_provider_ids_for_stack(stack: str) -> list[str]:
    """Return ordered auth provider ids supported by a stack."""
    if stack not in AUTH_SUPPORTED_STACKS:
        return []

    return list(AUTH_PROVIDER_ORDER)


def auth_provider_supported_for_stack(stack: str, auth_provider: str) -> bool:
    """Return whether a specific auth provider is supported for a stack."""
    return auth_provider in auth_provider_ids_for_stack(stack)


def ci_action_ids_for_stack(stack: str) -> list[str]:
    """Return ordered CI action ids for a stack."""
    return STACK_CI_ACTIONS.get(stack, ["lint", "typecheck", "unit-tests"])
