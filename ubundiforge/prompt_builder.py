"""Assembles the prompt string that gets piped into the AI CLI."""

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


def build_prompt(
    answers: dict,
    conventions: str,
    claude_md_template: str | None = None,
) -> str:
    """Build the full prompt from user answers, conventions, and optional CLAUDE.md template.

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
        docker_instruction = (
            "- Include Docker setup (Dockerfile + docker-compose.yml)\n"
        )

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
    guidance_sections = "\n\n".join(
        section for section in (stack_section, ci_section) if section
    )

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
