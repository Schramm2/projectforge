"""Assembles the prompt string that gets piped into the AI CLI.

Supports both single-prompt (all phases merged) and phase-specific prompts
for multi-backend scaffolding.

Each phase has two prompt variants:
  - default: used when a non-ideal backend handles the phase (fallback)
  - best: used when the ideal/specialist backend handles the phase
"""

from ubundiforge.router import PHASE_IDEAL_BACKEND
from ubundiforge.scaffold_options import AUTH_PROVIDER_OPTIONS, CI_ACTION_OPTIONS
from ubundiforge.stacks import CROSS_RECIPE_DEFAULTS, STACK_META

STACK_LABELS = {
    "nextjs": "Next.js + React",
    "fastapi": "Python API (FastAPI)",
    "fastapi-ai": "FastAPI + AI/LLM (OpenAI, pgvector, embeddings)",
    "both": "Next.js frontend + FastAPI backend (monorepo)",
    "python-cli": "Python CLI Tool (Typer + Rich)",
    "ts-package": "TypeScript npm Package",
    "python-worker": "Python Worker / Scheduled Service",
}


def _format_env_hint(hint: str, project_name: str) -> str:
    """Render env hint placeholders using the current project name."""
    return hint.format(project_name=project_name)


def _build_stack_section(
    stack: str,
    services: list[str],
    project_name: str,
    auth_provider: str | None = None,
) -> str:
    """Build a stack-specific guidance section from metadata."""
    meta = STACK_META.get(stack)
    if not meta:
        return ""

    lines = ["STACK-SPECIFIC GUIDANCE:"]

    lines.append(f"\nPackage manager: {meta.package_manager}")

    lines.append("\nProject structure (follow this layout):")
    for entry in meta.default_structure:
        lines.append(f"  {entry}")

    if meta.common_libraries:
        lines.append("\nCore libraries to include:")
        for lib, desc in meta.common_libraries.items():
            lines.append(f"  - {lib}: {desc}")

    if meta.dev_commands:
        lines.append("\nDev commands (configure these in the project):")
        for cmd_name, cmd_val in meta.dev_commands.items():
            lines.append(f"  {cmd_name}: {cmd_val}")

    if services:
        lines.append("\nServices to integrate:")
        for svc in services:
            lines.append(f"  - {svc}")

    auth_meta = AUTH_PROVIDER_OPTIONS.get(auth_provider) if auth_provider else None
    if auth_meta:
        lines.append("\nAuthentication to scaffold:")
        lines.append(f"  - {auth_meta.label}: {auth_meta.prompt_description}")
        lines.append("\nAuth libraries to include:")
        for lib, desc in auth_meta.libraries.items():
            lines.append(f"  - {lib}: {desc}")

    env_hints = [_format_env_hint(hint, project_name) for hint in meta.env_hints]
    if auth_meta:
        env_hints.extend(_format_env_hint(hint, project_name) for hint in auth_meta.env_hints)

    if env_hints:
        lines.append("\n.env.example should include:")
        for hint in env_hints:
            lines.append(f"  {hint}")

    return "\n".join(lines)


def _build_ci_section(ci: dict) -> str:
    """Build GitHub Actions guidance when CI was requested."""
    if not ci or not ci.get("include"):
        return ""

    lines = [
        "CI GUIDANCE:",
        "",
        "- Generate a GitHub Actions workflow at .github/workflows/ci.yml",
    ]

    mode = ci.get("mode")
    if mode == "blank-template":
        lines.extend(
            [
                "- Keep it as a blank starter template with clear TODO comments",
                "  and placeholder jobs",
                "- Do not guess extra jobs beyond the starter skeleton",
            ]
        )
        return "\n".join(lines)

    lines.append("- Configure the workflow around these requested actions:")
    for action_id in ci.get("actions", []):
        action = CI_ACTION_OPTIONS.get(action_id)
        if not action:
            continue
        lines.append(f"  - {action.label}: {action.prompt_description}")

    return "\n".join(lines)


def _is_ideal_backend(phase: str, backend: str) -> bool:
    """Return True if the backend is the ideal specialist for this phase."""
    return PHASE_IDEAL_BACKEND.get(phase) == backend


def build_prompt(
    answers: dict,
    conventions: str,
    claude_md_template: str | None = None,
) -> str:
    """Build the full prompt from user answers, conventions, and optional CLAUDE.md template.

    Used when all scaffold phases are handled by a single backend.

    Args:
        answers: Dict with keys: name, stack, description, docker, auth_provider,
            services, ci, extra.
        conventions: Contents of the conventions.md file.
        claude_md_template: Optional CLAUDE.md scaffold template content.

    Returns:
        The assembled prompt string.
    """
    stack_label = STACK_LABELS.get(answers["stack"], answers["stack"])
    docker_str = "Yes" if answers["docker"] else "No"
    extra = answers.get("extra", "").strip() or "None"
    services = answers.get("services", [])
    auth_provider = answers.get("auth_provider")
    ci = answers.get("ci", {})

    docker_instruction = ""
    if answers["docker"]:
        docker_instruction = "- Include Docker setup (Dockerfile + docker-compose.yml)\n"

    if claude_md_template:
        claude_md_instruction = (
            "- Include a CLAUDE.md at the project root using the template below "
            "as the base structure. Adapt the placeholders to match this project's "
            "actual name, stack, and structure.\n"
        )
    else:
        claude_md_instruction = (
            "- Include a CLAUDE.md at the root that describes this project "
            "for AI coding assistants\n"
        )

    stack_section = _build_stack_section(
        answers["stack"],
        services,
        answers["name"],
        auth_provider=auth_provider,
    )
    ci_section = _build_ci_section(ci)
    guidance_sections = "\n\n".join(section for section in (stack_section, ci_section) if section)

    prompt = f"""\
You are scaffolding a new project. Create the full project in the current directory.

PROJECT DETAILS:
- Name: {answers["name"]}
- Stack: {stack_label}
- Description: {answers["description"]}
- Docker: {docker_str}

{guidance_sections}

{CROSS_RECIPE_DEFAULTS}

CONVENTIONS (follow these exactly):
{conventions}

INSTRUCTIONS:
- Create a complete, working project structure with all config files
{claude_md_instruction}\
- Include an agent_docs/ directory with starter progressive-disclosure docs
  that align with CLAUDE.md
- Include appropriate .gitignore, .env.example, README.md
{docker_instruction}\
- Initialize with sensible defaults — the user should be able to run the project immediately
- Follow the stack-specific guidance above for structure, libraries, and commands
- Follow the conventions above strictly for all styling, structure, and coding patterns
- Initialize a git repository and make an initial commit

EXTRA INSTRUCTIONS FROM USER:
{extra}"""

    if claude_md_template:
        prompt += f"""

CLAUDE.MD TEMPLATE (use this as the base for the project's CLAUDE.md):
{claude_md_template}"""

    return prompt


# ---------------------------------------------------------------------------
# Phase-specific prompt builders — default variants
# Used when a non-ideal backend handles the phase (fallback).
# ---------------------------------------------------------------------------


def build_architecture_prompt(
    answers: dict,
    conventions: str,
    claude_md_template: str | None = None,
    exclude_frontend: bool = False,
    exclude_tests: bool = False,
) -> str:
    """Build prompt for the architecture/core scaffold phase.

    When frontend or tests are handled by separate backends, this prompt
    tells the AI to skip those and focus on structure, backend, and config.
    """
    stack_label = STACK_LABELS.get(answers["stack"], answers["stack"])
    docker_str = "Yes" if answers["docker"] else "No"
    extra = answers.get("extra", "").strip() or "None"
    services = answers.get("services", [])
    auth_provider = answers.get("auth_provider")
    ci = answers.get("ci", {})

    docker_instruction = ""
    if answers["docker"]:
        docker_instruction = "- Include Docker setup (Dockerfile + docker-compose.yml)\n"

    if claude_md_template:
        claude_md_instruction = (
            "- Include a CLAUDE.md at the project root using the template below "
            "as the base structure. Adapt the placeholders to match this project's "
            "actual name, stack, and structure.\n"
        )
    else:
        claude_md_instruction = (
            "- Include a CLAUDE.md at the root that describes this project "
            "for AI coding assistants\n"
        )

    stack_section = _build_stack_section(
        answers["stack"],
        services,
        answers["name"],
        auth_provider=auth_provider,
    )
    ci_section = "" if exclude_tests else _build_ci_section(ci)
    guidance_sections = "\n\n".join(section for section in (stack_section, ci_section) if section)

    exclusions = []
    if exclude_frontend:
        exclusions.append(
            "- Do NOT create frontend UI components or pages — "
            "a specialist frontend tool will handle those in the next step"
        )
    if exclude_tests:
        exclusions.append(
            "- Do NOT create test files or CI configuration — "
            "a specialist testing tool will handle those in a later step"
        )
    exclusion_block = "\n".join(exclusions) + "\n" if exclusions else ""

    prompt = f"""\
You are scaffolding a new project. Create the full project structure in the current directory.

PROJECT DETAILS:
- Name: {answers["name"]}
- Stack: {stack_label}
- Description: {answers["description"]}
- Docker: {docker_str}

{guidance_sections}

{CROSS_RECIPE_DEFAULTS}

CONVENTIONS (follow these exactly):
{conventions}

INSTRUCTIONS:
- Create a complete, working project structure with all config files
{claude_md_instruction}\
- Include an agent_docs/ directory with starter progressive-disclosure docs
  that align with CLAUDE.md
- Include appropriate .gitignore, .env.example, README.md
{docker_instruction}\
{exclusion_block}\
- Initialize with sensible defaults — the user should be able to run the project immediately
- Follow the stack-specific guidance above for structure, libraries, and commands
- Follow the conventions above strictly for all styling, structure, and coding patterns
- Initialize a git repository and make an initial commit

EXTRA INSTRUCTIONS FROM USER:
{extra}"""

    if claude_md_template:
        prompt += f"""

CLAUDE.MD TEMPLATE (use this as the base for the project's CLAUDE.md):
{claude_md_template}"""

    return prompt


def build_frontend_prompt(answers: dict) -> str:
    """Build prompt for the frontend/UI phase.

    Runs after the architecture phase has created the project skeleton.
    Focuses the AI on creating polished, production-quality frontend work.
    """
    stack_label = STACK_LABELS.get(answers["stack"], answers["stack"])
    extra = answers.get("extra", "").strip() or "None"

    return f"""\
A project has been scaffolded in the current directory. Your job is to create \
and enhance the frontend UI.

PROJECT DETAILS:
- Name: {answers["name"]}
- Stack: {stack_label}
- Description: {answers["description"]}

Review the existing project structure and code, then:
- Create polished, production-quality frontend components with strong visual design
- Build responsive, well-styled UI pages with modern aesthetics
- Implement proper routing and navigation
- Connect frontend to any existing API endpoints or data models
- Follow the project's existing conventions and patterns (check CLAUDE.md and conventions)
- Use the libraries and styling framework already configured in the project
- Ensure accessibility basics (semantic HTML, alt text, keyboard navigation)

Do NOT modify backend code, configuration files, tests, or infrastructure.
Focus exclusively on creating an excellent frontend user experience.

EXTRA INSTRUCTIONS FROM USER:
{extra}"""


def build_tests_prompt(answers: dict) -> str:
    """Build prompt for the tests/automation phase.

    Runs after architecture (and optionally frontend) phases.
    Focuses the AI on comprehensive test coverage and CI setup.
    """
    stack_label = STACK_LABELS.get(answers["stack"], answers["stack"])
    extra = answers.get("extra", "").strip() or "None"
    ci = answers.get("ci", {})
    ci_section = _build_ci_section(ci)
    ci_block = f"\n{ci_section}\n" if ci_section else ""

    return f"""\
A project has been scaffolded in the current directory. Your job is to add \
comprehensive tests and automation.

PROJECT DETAILS:
- Name: {answers["name"]}
- Stack: {stack_label}
- Description: {answers["description"]}
{ci_block}
Review the existing project structure and code, then:
- Create comprehensive unit tests for all modules and functions
- Add integration tests for API endpoints, data flows, and key workflows
- Ensure tests cover edge cases and error paths, not just happy paths
- Check for backward compatibility issues in any public interfaces
- Add CI configuration if requested above
- Follow the project's existing test patterns and conventions (check CLAUDE.md)
- Use the testing frameworks already configured in the project (check pyproject.toml / package.json)

Do NOT modify application code, frontend components, or infrastructure files.
Focus exclusively on test coverage, CI configuration, and automation.

EXTRA INSTRUCTIONS FROM USER:
{extra}"""


# ---------------------------------------------------------------------------
# Phase-specific prompt builders — best variants
# Used when the ideal/specialist backend handles the phase.
# These are duplicates of the default variants for now — customize them to
# lean into each backend's strengths.
# ---------------------------------------------------------------------------


def build_architecture_prompt_best(
    answers: dict,
    conventions: str,
    claude_md_template: str | None = None,
    exclude_frontend: bool = False,
    exclude_tests: bool = False,
) -> str:
    """Build specialist architecture prompt for Claude (ideal backend).

    TODO: Customize to lean into Claude's strengths — complex reasoning,
    multi-file architecture, self-correction, security awareness.
    """
    return build_architecture_prompt(
        answers,
        conventions,
        claude_md_template,
        exclude_frontend,
        exclude_tests,
    )


def build_frontend_prompt_best(answers: dict) -> str:
    """Build specialist frontend prompt for Gemini (ideal backend).

    TODO: Customize to lean into Gemini's strengths — richer aesthetics,
    sophisticated UI components, visual design quality, animations.
    """
    return build_frontend_prompt(answers)


def build_tests_prompt_best(answers: dict) -> str:
    """Build specialist tests prompt for Codex (ideal backend).

    TODO: Customize to lean into Codex's strengths — mechanical precision,
    backward compatibility checks, refactoring, exhaustive coverage.
    """
    return build_tests_prompt(answers)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def build_phase_prompt(
    phases: list[str],
    all_phases: list[str],
    answers: dict,
    conventions: str,
    backend: str = "",
    claude_md_template: str | None = None,
) -> str:
    """Build a prompt for a merged group of scaffold phases.

    When all phases are in one group (single backend), returns the standard
    full prompt identical to the original behavior. When phases are split
    across backends, returns a targeted prompt — using the "best" variant
    if the backend is the ideal specialist for that phase, or the default
    variant otherwise.

    Args:
        phases: The phases in this group.
        all_phases: All phases for this stack.
        answers: User answers dict.
        conventions: Conventions text.
        backend: The backend that will execute this prompt.
        claude_md_template: Optional CLAUDE.md template.
    """
    phase_set = set(phases)
    all_set = set(all_phases)

    # All phases merged → standard full prompt (identical to pre-multi-backend behavior)
    if phase_set == all_set:
        return build_prompt(answers, conventions, claude_md_template)

    # Architecture phase (possibly merged with others)
    if "architecture" in phase_set:
        exclude_frontend = "frontend" in all_set and "frontend" not in phase_set
        exclude_tests = "tests" in all_set and "tests" not in phase_set
        if _is_ideal_backend("architecture", backend):
            return build_architecture_prompt_best(
                answers,
                conventions,
                claude_md_template,
                exclude_frontend,
                exclude_tests,
            )
        return build_architecture_prompt(
            answers,
            conventions,
            claude_md_template,
            exclude_frontend,
            exclude_tests,
        )

    # Standalone frontend phase
    if "frontend" in phase_set:
        if _is_ideal_backend("frontend", backend):
            return build_frontend_prompt_best(answers)
        return build_frontend_prompt(answers)

    # Standalone tests phase
    if "tests" in phase_set:
        if _is_ideal_backend("tests", backend):
            return build_tests_prompt_best(answers)
        return build_tests_prompt(answers)

    # Shouldn't happen, but fallback to full prompt
    return build_prompt(answers, conventions, claude_md_template)
