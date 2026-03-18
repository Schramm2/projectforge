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

DEMO_MODE_BLOCK = """\

DEMO MODE (critical — the project MUST run out of the box without real secrets):
- The project must start and render without any .env.local or real API keys
- For auth providers (Clerk, Auth0, etc.): wrap in a conditional that checks if the
  env var is set. When missing, bypass auth entirely and render the app without it.
  Add a visible banner like "Auth disabled — set CLERK_PUBLISHABLE_KEY to enable"
- For databases: use an in-memory fallback or mock data when the connection string
  is missing. The app should show sample/seed data, not crash
- For external APIs (OpenAI, Stripe, etc.): return mock responses when the key is
  missing. Never crash or block startup due to a missing optional secret
- .env.example should list all vars with placeholder values and comments explaining
  which are required vs optional
- The goal: `git clone && npm install && npm run dev` (or `uv sync && uv run ...`)
  must produce a working, visible app with no manual setup"""

STACK_LABELS = {
    "nextjs": "Next.js + React",
    "fastapi": "Python API (FastAPI)",
    "fastapi-ai": "FastAPI + AI/LLM (OpenAI, pgvector, embeddings)",
    "both": "Next.js frontend + FastAPI backend (monorepo)",
    "python-cli": "Python CLI Tool (Typer + Rich)",
    "ts-package": "TypeScript npm Package",
    "python-worker": "Python Worker / Scheduled Service",
}


def _demo_mode_section(answers: dict) -> str:
    """Return the demo mode instruction block if enabled, else empty string."""
    if answers.get("demo_mode"):
        return DEMO_MODE_BLOCK
    return ""


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

    stack_section = _build_stack_section(
        answers["stack"],
        services,
        answers["name"],
        auth_provider=auth_provider,
    )
    ci_section = _build_ci_section(ci)

    docker_block = ""
    if answers["docker"]:
        docker_block = (
            "\n<docker>\n"
            "Include Docker setup: Dockerfile + docker-compose.yml.\n"
            "Follow the Docker standards in cross-project conventions.\n"
            "</docker>"
        )

    claude_md_block = ""
    if claude_md_template:
        claude_md_block = (
            "\n<claude_md_template>\n"
            "Use this as the base for the project's CLAUDE.md. Adapt "
            "placeholders to match this project's actual name, stack, "
            "and structure.\n\n"
            f"{claude_md_template}\n"
            "</claude_md_template>"
        )

    ci_block = ""
    if ci_section:
        ci_block = f"\n<ci_guidance>\n{ci_section}\n</ci_guidance>"

    claude_md_hint = (
        "Use the template above as the base structure."
        if claude_md_template
        else "Cover stack, dev commands, project structure, and key patterns."
    )

    prompt = f"""\
You are an expert software architect specializing in production-grade project \
scaffolding. You excel at designing clean, well-reasoned project structures \
where every file has a clear purpose and every architectural decision is \
intentional.

Your task: scaffold a new project in the current directory. Go beyond a \
basic skeleton — create a fully-featured, immediately runnable project with \
thoughtful defaults that reflect real-world best practices.

<project>
<name>{answers["name"]}</name>
<stack>{stack_label}</stack>
<description>{answers["description"]}</description>
<docker>{docker_str}</docker>
</project>

<conventions>
These are the team's coding standards. Follow them exactly — they override \
any defaults you would normally use. They exist because the team has learned \
from experience that these patterns reduce bugs and speed up onboarding.

{conventions}
</conventions>

<stack_guidance>
{stack_section}
</stack_guidance>

<cross_project_standards>
{CROSS_RECIPE_DEFAULTS}
</cross_project_standards>{docker_block}{ci_block}{claude_md_block}

<instructions>
1. Create the complete project structure with all configuration files, \
following the stack guidance layout exactly.
2. Include a CLAUDE.md at the project root that describes this project for \
AI coding assistants. {claude_md_hint}
3. Include an agent_docs/ directory with starter progressive-disclosure docs \
that align with CLAUDE.md (architecture overview, getting started, etc.).
4. Include .gitignore, .env.example with real placeholder values, and a \
README.md with setup instructions.
5. Initialize with sensible defaults — the user should be able to clone, \
install, and run the project immediately with no manual config.
6. Initialize a git repository and make an initial commit.
</instructions>

<quality_criteria>
Before finishing, verify your work against these criteria:
- Every file in the project structure has real, meaningful content (no empty \
placeholder files).
- Configuration files (pyproject.toml, tsconfig.json, etc.) are complete and \
correct — they should pass validation.
- Import paths are consistent and all cross-references between modules resolve.
- The conventions are reflected in actual code patterns, not just documented.
- Dev commands listed in CLAUDE.md actually work with the project as scaffolded.
</quality_criteria>

<avoid>
- Do not over-engineer. Only include what the project description requires. \
A simple API does not need event sourcing or CQRS.
- Do not add features, abstractions, or configurability beyond what was asked.
- Do not create empty placeholder files — if a file exists, it should have \
real content.
- Do not add excessive comments or docstrings to boilerplate code. Only \
comment where the logic is non-obvious.
</avoid>
{_demo_mode_section(answers)}
<extra_instructions>
{extra}
</extra_instructions>"""

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

    stack_section = _build_stack_section(
        answers["stack"],
        services,
        answers["name"],
        auth_provider=auth_provider,
    )
    ci_section = "" if exclude_tests else _build_ci_section(ci)

    docker_block = ""
    if answers["docker"]:
        docker_block = (
            "\n<docker>\n"
            "Include Docker setup: Dockerfile + docker-compose.yml.\n"
            "Follow the Docker standards in cross-project conventions.\n"
            "</docker>"
        )

    claude_md_block = ""
    if claude_md_template:
        claude_md_block = (
            "\n<claude_md_template>\n"
            "Use this as the base for the project's CLAUDE.md. Adapt "
            "placeholders to match this project's actual name, stack, "
            "and structure.\n\n"
            f"{claude_md_template}\n"
            "</claude_md_template>"
        )

    exclusion_lines = []
    if exclude_frontend:
        exclusion_lines.append(
            "- Do NOT create frontend UI components or pages — "
            "a specialist frontend tool will handle those in the next step."
        )
    if exclude_tests:
        exclusion_lines.append(
            "- Do NOT create test files or CI configuration — "
            "a specialist testing tool will handle those in a later step."
        )
    exclusion_block = ""
    if exclusion_lines:
        exclusion_block = (
            "\n<scope_boundaries>\n" + "\n".join(exclusion_lines) + "\n</scope_boundaries>"
        )

    ci_block = ""
    if ci_section:
        ci_block = f"\n<ci_guidance>\n{ci_section}\n</ci_guidance>"

    claude_md_hint = (
        "Use the template above as the base structure."
        if claude_md_template
        else "Cover stack, dev commands, project structure, and key patterns."
    )

    prompt = f"""\
You are an expert software architect specializing in production-grade project \
scaffolding. You excel at designing clean, well-reasoned project structures \
where every file has a clear purpose and every architectural decision is \
intentional.

Your task: scaffold a new project in the current directory. Go beyond a \
basic skeleton — create a fully-featured, immediately runnable project with \
thoughtful defaults that reflect real-world best practices.

<project>
<name>{answers["name"]}</name>
<stack>{stack_label}</stack>
<description>{answers["description"]}</description>
<docker>{docker_str}</docker>
</project>

<conventions>
These are the team's coding standards. Follow them exactly — they override \
any defaults you would normally use. They exist because the team has learned \
from experience that these patterns reduce bugs and speed up onboarding.

{conventions}
</conventions>

<stack_guidance>
{stack_section}
</stack_guidance>

<cross_project_standards>
{CROSS_RECIPE_DEFAULTS}
</cross_project_standards>{docker_block}{ci_block}{exclusion_block}{claude_md_block}

<instructions>
1. Create the complete project structure with all configuration files, \
following the stack guidance layout exactly.
2. Include a CLAUDE.md at the project root that describes this project for \
AI coding assistants. {claude_md_hint}
3. Include an agent_docs/ directory with starter progressive-disclosure docs \
that align with CLAUDE.md (architecture overview, getting started, etc.).
4. Include .gitignore, .env.example with real placeholder values, and a \
README.md with setup instructions.
5. Initialize with sensible defaults — the user should be able to clone, \
install, and run the project immediately with no manual config.
6. Initialize a git repository and make an initial commit.
</instructions>

<quality_criteria>
Before finishing, verify your work against these criteria:
- Every file in the project structure has real, meaningful content (no empty \
placeholder files).
- Configuration files (pyproject.toml, tsconfig.json, etc.) are complete and \
correct — they should pass validation.
- Import paths are consistent and all cross-references between modules resolve.
- The conventions are reflected in actual code patterns, not just documented.
- Dev commands listed in CLAUDE.md actually work with the project as scaffolded.
</quality_criteria>

<avoid>
- Do not over-engineer. Only include what the project description requires. \
A simple API does not need event sourcing or CQRS.
- Do not add features, abstractions, or configurability beyond what was asked.
- Do not create empty placeholder files — if a file exists, it should have \
real content.
- Do not add excessive comments or docstrings to boilerplate code. Only \
comment where the logic is non-obvious.
</avoid>
{_demo_mode_section(answers)}
<extra_instructions>
{extra}
</extra_instructions>"""

    return prompt


def build_frontend_prompt(answers: dict) -> str:
    """Build prompt for the frontend/UI phase.

    Runs after the architecture phase has created the project skeleton.
    Focuses the AI on creating polished, production-quality frontend work.
    """
    stack_label = STACK_LABELS.get(answers["stack"], answers["stack"])
    extra = answers.get("extra", "").strip() or "None"

    return f"""\
You are an expert frontend engineer and visual designer who creates \
distinctive, production-quality interfaces. You build frontends that look \
and feel like they were crafted by a seasoned product designer.

A project has been scaffolded in the current directory. The backend code, \
configuration files, and project structure already exist. Your job is to \
create the complete frontend UI.

<project>
<name>{answers["name"]}</name>
<stack>{stack_label}</stack>
<description>{answers["description"]}</description>
</project>

<instructions>
1. Read the existing project structure first. Check CLAUDE.md, package.json \
or pyproject.toml, and any existing frontend files to understand what \
libraries, frameworks, and conventions are configured.
2. Create all pages, routes, and components that the project description implies.
   - Build responsive layouts that work across mobile, tablet, and desktop.
   - Use the styling framework already configured in the project.
   - Connect frontend to any existing API endpoints or data models.
   - Add meaningful loading states, error states, and empty states.
   - Use animations for page transitions and micro-interactions where appropriate.
3. Ensure accessibility: semantic HTML, alt text, keyboard navigation, \
sufficient color contrast, and visible focus indicators.
</instructions>

<aesthetics>
- Typography: Choose fonts that are beautiful and distinctive. Avoid generic \
fonts like Arial and Inter.
- Color and theme: Commit to a cohesive aesthetic. Use CSS variables for \
consistency. Dominant colors with sharp accents outperform timid palettes.
- Backgrounds: Create atmosphere and depth rather than defaulting to solid \
colors. Layer CSS gradients or contextual effects.
- Layout: Use visual hierarchy to guide the eye. Vary spacing, size, and \
weight to create rhythm.
</aesthetics>

<quality_criteria>
Before finishing, verify:
- Does every page serve the project description's intent?
- Is the visual design cohesive with a clear color palette and typography?
- Are interactive elements keyboard-navigable with visible focus states?
- Does the design feel distinctive and specific to this product?
</quality_criteria>

<scope_boundaries>
- Do NOT modify backend code, API routes, database models, or infrastructure.
- Do NOT modify configuration files (pyproject.toml, tsconfig.json, etc.).
- Do NOT create test files.
- Focus exclusively on frontend: pages, components, styles, client-side logic.
</scope_boundaries>

<avoid>
- Do not use overused font families (Inter, Roboto, Arial, system fonts).
- Do not use purple gradients on white backgrounds.
- Do not create predictable layouts or cookie-cutter component patterns.
- Do not create generic hero sections with stock-photo-style descriptions.
</avoid>

<extra_instructions>
{extra}
</extra_instructions>"""


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
You are a test engineer and automation specialist. A project has been \
scaffolded in the current directory. Your job is to add comprehensive tests \
and automation.

<project>
<name>{answers["name"]}</name>
<stack>{stack_label}</stack>
<description>{answers["description"]}</description>
</project>{ci_block}

<dependency_checks>
Before writing any tests:
- Read the project structure, CLAUDE.md, and the package manager config \
(pyproject.toml or package.json) to understand what exists and what test \
frameworks are configured.
- Identify every module, class, and public function that needs test coverage.
- Check what test utilities or fixtures already exist before creating new ones.
</dependency_checks>

<instructions>
1. Create comprehensive unit tests for all modules and functions.
2. Add integration tests for API endpoints, data flows, and key workflows.
3. For each function or endpoint, test:
   - Happy path with typical inputs
   - Edge cases: empty inputs, boundary values, maximum sizes
   - Error paths: invalid inputs, missing data, permission failures
4. Add CI configuration if requested in ci_guidance above.
5. Use the testing frameworks already configured in the project.
6. Follow the project's existing test patterns and conventions (check CLAUDE.md).
</instructions>

<quality_criteria>
- Do not hard-code expected values that only match one specific input. \
Verify the logic, not memorized outputs.
- Use real objects where practical. Only mock external services, I/O, and \
slow dependencies.
- Do not write tests that test the framework itself.
</quality_criteria>

<verification>
Before finalizing:
- Run the test suite to confirm tests pass.
- Check that no test files have syntax errors or missing imports.
- Verify that test coverage touches every module identified above.
</verification>

<scope_boundaries>
- Do NOT modify application code, frontend components, or infrastructure.
- If you find bugs in application code, write a failing test that exposes \
the bug and add a comment explaining what is wrong. Do not fix the bug.
- Focus exclusively on: test files, CI configuration, and test utilities.
</scope_boundaries>

<extra_instructions>
{extra}
</extra_instructions>"""


# ---------------------------------------------------------------------------
# Phase-specific prompt builders — best variants
# Used when the ideal/specialist backend handles the phase.
# These apply prompt engineering best practices tuned to each backend's
# strengths: XML structure, role assignment, self-verification, explicit
# quality modifiers, and anti-overengineering guidance.
# ---------------------------------------------------------------------------


def build_architecture_prompt_best(
    answers: dict,
    conventions: str,
    claude_md_template: str | None = None,
    exclude_frontend: bool = False,
    exclude_tests: bool = False,
) -> str:
    """Build specialist architecture prompt for Claude (ideal backend).

    Applies Claude prompting best practices: XML-structured sections, role
    assignment, long context at top, self-verification, and explicit quality
    modifiers tuned for Claude's strengths in reasoning and architecture.
    """
    stack_label = STACK_LABELS.get(answers["stack"], answers["stack"])
    docker_str = "Yes" if answers["docker"] else "No"
    extra = answers.get("extra", "").strip() or "None"
    services = answers.get("services", [])
    auth_provider = answers.get("auth_provider")
    ci = answers.get("ci", {})

    stack_section = _build_stack_section(
        answers["stack"],
        services,
        answers["name"],
        auth_provider=auth_provider,
    )
    ci_section = "" if exclude_tests else _build_ci_section(ci)

    docker_block = ""
    if answers["docker"]:
        docker_block = (
            "\n<docker>\n"
            "Include Docker setup: Dockerfile + docker-compose.yml.\n"
            "Follow the Docker standards in cross-project conventions.\n"
            "</docker>"
        )

    claude_md_block = ""
    if claude_md_template:
        claude_md_block = (
            "\n<claude_md_template>\n"
            "Use this as the base for the project's CLAUDE.md. Adapt "
            "placeholders to match this project's actual name, stack, "
            "and structure.\n\n"
            f"{claude_md_template}\n"
            "</claude_md_template>"
        )

    exclusion_lines = []
    if exclude_frontend:
        exclusion_lines.append(
            "- Do NOT create frontend UI components or pages — "
            "a specialist frontend tool will handle those in the next step."
        )
    if exclude_tests:
        exclusion_lines.append(
            "- Do NOT create test files or CI configuration — "
            "a specialist testing tool will handle those in a later step."
        )
    exclusion_block = ""
    if exclusion_lines:
        exclusion_block = (
            "\n<scope_boundaries>\n" + "\n".join(exclusion_lines) + "\n</scope_boundaries>"
        )

    ci_block = ""
    if ci_section:
        ci_block = f"\n<ci_guidance>\n{ci_section}\n</ci_guidance>"

    claude_md_hint = (
        "Use the template above as the base structure."
        if claude_md_template
        else "Cover stack, dev commands, project structure, and key patterns."
    )

    prompt = f"""\
You are an expert software architect specializing in production-grade project \
scaffolding. You excel at designing clean, well-reasoned project structures \
where every file has a clear purpose and every architectural decision is \
intentional.

Your task: scaffold a new project in the current directory. Go beyond a \
basic skeleton — create a fully-featured, immediately runnable project with \
thoughtful defaults that reflect real-world best practices.

<project>
<name>{answers["name"]}</name>
<stack>{stack_label}</stack>
<description>{answers["description"]}</description>
<docker>{docker_str}</docker>
</project>

<conventions>
These are the team's coding standards. Follow them exactly — they override \
any defaults you would normally use. They exist because the team has learned \
from experience that these patterns reduce bugs and speed up onboarding.

{conventions}
</conventions>

<stack_guidance>
{stack_section}
</stack_guidance>

<cross_project_standards>
{CROSS_RECIPE_DEFAULTS}
</cross_project_standards>{docker_block}{ci_block}{exclusion_block}{claude_md_block}

<instructions>
1. Create the complete project structure with all configuration files, \
following the stack guidance layout exactly.
2. Include a CLAUDE.md at the project root that describes this project for \
AI coding assistants. {claude_md_hint}
3. Include an agent_docs/ directory with starter progressive-disclosure docs \
that align with CLAUDE.md (architecture overview, getting started, etc.).
4. Include .gitignore, .env.example with real placeholder values, and a \
README.md with setup instructions.
5. Initialize with sensible defaults — the user should be able to clone, \
install, and run the project immediately with no manual config.
6. Initialize a git repository and make an initial commit.
</instructions>

<quality_criteria>
Before finishing, verify your work against these criteria:
- Every file in the project structure has real, meaningful content (no empty \
placeholder files).
- Configuration files (pyproject.toml, tsconfig.json, etc.) are complete and \
correct — they should pass validation.
- Import paths are consistent and all cross-references between modules resolve.
- The conventions are reflected in actual code patterns, not just documented.
- Dev commands listed in CLAUDE.md actually work with the project as scaffolded.
</quality_criteria>

<avoid>
- Do not over-engineer. Only include what the project description requires. \
A simple API does not need event sourcing or CQRS.
- Do not add features, abstractions, or configurability beyond what was asked.
- Do not create empty placeholder files — if a file exists, it should have \
real content.
- Do not add excessive comments or docstrings to boilerplate code. Only \
comment where the logic is non-obvious.
</avoid>
{_demo_mode_section(answers)}
<extra_instructions>
{extra}
</extra_instructions>"""

    return prompt


def build_frontend_prompt_best(answers: dict) -> str:
    """Build specialist frontend prompt for Gemini (ideal backend).

    Applies Gemini 3 prompting best practices: role in <role> tags, context
    before instructions, plan-execute-validate workflow, self-critique,
    negative constraints at the end, and XML-structured sections.
    """
    stack_label = STACK_LABELS.get(answers["stack"], answers["stack"])
    extra = answers.get("extra", "").strip() or "None"

    return f"""\
<role>
You are an expert frontend engineer and visual designer who creates \
distinctive, production-quality interfaces. You build frontends that look \
and feel like they were crafted by a seasoned product designer. You are \
precise, creative, and persistent.
</role>

<context>
A project has been scaffolded in the current directory. The backend code, \
configuration files, and project structure already exist. Your job is to \
create the complete frontend UI.

Project name: {answers["name"]}
Stack: {stack_label}
Description: {answers["description"]}
</context>

<task>
Before writing any code, follow these steps:

1. Plan: Read the existing project structure. Check CLAUDE.md, package.json \
or pyproject.toml, and any existing frontend files to understand what \
libraries, frameworks, and conventions are configured. Identify what pages \
and components the project description implies a real user would need.

2. Execute: Create all pages, routes, and components.
   - Build responsive layouts that work across mobile, tablet, and desktop.
   - Use the styling framework already configured in the project.
   - Connect frontend to any existing API endpoints or data models found in \
the codebase.
   - Add meaningful loading states, error states, and empty states.
   - Use animations for page transitions and micro-interactions. Focus on \
high-impact moments: one well-orchestrated page load with staggered reveals \
creates more delight than scattered micro-interactions.

3. Validate: Review your output against these criteria before finishing:
   - Does every page serve the project description's intent, not just a \
generic landing page?
   - Is the visual design cohesive with a clear color palette and typography?
   - Are interactive elements keyboard-navigable with visible focus states?
   - Does the design feel distinctive and specific to this product?

4. Format: Ensure all files follow the project's existing conventions and \
directory structure.
</task>

<aesthetics>
Typography: Choose fonts that are beautiful and distinctive. Avoid generic \
fonts like Arial and Inter. Use choices that elevate the design.

Color and theme: Commit to a cohesive aesthetic. Use CSS variables for \
consistency. Dominant colors with sharp accents outperform timid, evenly \
distributed palettes.

Backgrounds: Create atmosphere and depth rather than defaulting to solid \
colors. Layer CSS gradients, use geometric patterns, or add contextual \
effects that match the aesthetic.

Layout: Use visual hierarchy to guide the eye. Vary spacing, size, and \
weight to create rhythm. Avoid uniform grids of identical cards.
</aesthetics>

<accessibility>
- Semantic HTML elements (nav, main, article, section, aside)
- Alt text on all images
- Keyboard navigation for all interactive elements
- Sufficient color contrast ratios
- Focus indicators on interactive elements
</accessibility>

<extra_instructions>
{extra}
</extra_instructions>

<constraints>
- Do NOT modify backend code, API routes, database models, or infrastructure.
- Do NOT modify configuration files (pyproject.toml, tsconfig.json, etc.).
- Do NOT create test files.
- Focus exclusively on frontend: pages, components, styles, client-side logic.
- Do NOT use overused font families (Inter, Roboto, Arial, system fonts).
- Do NOT use purple gradients on white backgrounds.
- Do NOT create predictable layouts or cookie-cutter component patterns.
- Do NOT create generic hero sections with stock-photo-style descriptions.
</constraints>

<final_instruction>
Based on the project context above, create a complete, visually impressive \
frontend. Make unexpected design choices that feel genuinely crafted for \
this specific product. Vary between light and dark themes, different fonts, \
different aesthetics. Think step-by-step before writing code.
</final_instruction>"""


def build_tests_prompt_best(answers: dict) -> str:
    """Build specialist tests prompt for Codex (ideal backend).

    Applies GPT-5.4/Codex prompting best practices: XML-structured blocks,
    completeness contracts, verification loops, dependency checks, autonomy
    and persistence, compact output, and terminal tool hygiene.
    """
    stack_label = STACK_LABELS.get(answers["stack"], answers["stack"])
    extra = answers.get("extra", "").strip() or "None"
    ci = answers.get("ci", {})
    ci_section = _build_ci_section(ci)
    ci_block = ""
    if ci_section:
        ci_block = f"\n<ci_guidance>\n{ci_section}\n</ci_guidance>"

    return f"""\
You are a test engineer and automation specialist. A project has been \
scaffolded in the current directory. Add comprehensive tests and automation.

<project>
<name>{answers["name"]}</name>
<stack>{stack_label}</stack>
<description>{answers["description"]}</description>
</project>{ci_block}

<output_contract>
- Create test files in the test directory matching project conventions.
- Create CI configuration if requested in ci_guidance above.
- Do not produce prose explanations. Write code.
- Keep progress updates to 1-2 sentences between actions.
</output_contract>

<dependency_checks>
- Before writing any tests, read the project structure, CLAUDE.md, and the \
package manager config (pyproject.toml or package.json) to understand what \
exists, what test frameworks are configured, and what patterns are in use.
- Identify every module, class, and public function that needs test coverage.
- Check what test utilities or fixtures already exist before creating new ones.
- Do not skip this discovery step just because the intended tests seem obvious.
</dependency_checks>

<completeness_contract>
- Treat the task as incomplete until every module has test coverage.
- Keep an internal checklist of modules and functions to cover.
- Track which modules have been tested as you go.
- For each module, confirm unit tests exist before moving to the next.
- If any module cannot be tested due to missing dependencies or unclear \
interfaces, mark it [blocked] and state exactly what is missing.
</completeness_contract>

<test_quality>
- For every function or endpoint, test:
  1. Happy path with typical inputs
  2. Edge cases: empty inputs, boundary values, maximum sizes
  3. Error paths: invalid inputs, missing data, permission failures
  4. State transitions: before/after side effects, cleanup
- Do not hard-code expected values that only match one specific input. \
Verify the logic, not memorized outputs.
- Do not write tests that test the framework itself.
- Use real objects where practical. Only mock external services, I/O, and \
slow dependencies.
</test_quality>

<backward_compatibility>
- Check for backward compatibility issues in public interfaces:
  1. API endpoints: do request/response schemas match what the code produces?
  2. Exported functions: do type signatures match their documentation?
  3. Configuration: are all env vars referenced in code documented in \
.env.example?
  4. Dependencies: are version constraints in the package config consistent?
- If you find issues, write a failing test that exposes the problem with a \
clear description. Do not silently fix application code.
</backward_compatibility>

<scope_boundaries>
- Do not modify application code, frontend components, or infrastructure.
- Do not modify configuration files unless adding test-specific config \
(e.g., pytest markers, vitest config).
- If you find bugs in application code, write a failing test that exposes \
the bug and add a comment explaining what is wrong. Do not fix the bug.
- Focus exclusively on: test files, CI configuration, and test utilities.
</scope_boundaries>

<verification_loop>
Before finalizing:
- Run the test suite using the dev commands from CLAUDE.md or the package \
config to confirm tests pass.
- Check that no test files have syntax errors or missing imports.
- Verify that test coverage touches every module identified in the \
dependency_checks step.
- If any tests fail unexpectedly, investigate and fix the test (not the \
application code) or mark [blocked] with an explanation.
</verification_loop>

<extra_instructions>
{extra}
</extra_instructions>"""


def build_verify_prompt(answers: dict) -> str:
    """Build prompt for the verify/fix phase.

    Runs as the final phase. Reviews the entire project, fixes integration
    issues, and optionally ensures demo mode works.
    """
    stack_label = STACK_LABELS.get(answers["stack"], answers["stack"])
    extra = answers.get("extra", "").strip() or "None"
    demo = answers.get("demo_mode", False)

    if demo:
        goal = (
            "Your job is to review the entire project, fix any issues, "
            "and ensure it runs out of the box without real API keys or secrets."
        )
        demo_instructions = """\
5. Ensure the project runs WITHOUT any real API keys or .env.local:
   - Auth providers (Clerk, Auth0, etc.) must be wrapped in conditionals \
that gracefully skip auth when env vars are missing. Show a visible banner \
like "Auth disabled — set CLERK_PUBLISHABLE_KEY to enable" instead of crashing.
   - Database connections must fall back to mock/seed data when the \
connection string is missing.
   - External API calls must return mock responses when keys are missing.
6. Verify that .env.example documents all required and optional vars.
7. Make a final git commit with all fixes."""
        quality_items = """\
- The dev server starts without errors and without .env.local
- The app renders visible content in the browser (not a crash page)"""
    else:
        goal = (
            "Your job is to review the entire project, fix any integration "
            "issues between phases, and ensure all checks pass."
        )
        demo_instructions = """\
5. Verify that .env.example documents all required vars.
6. Make a final git commit with all fixes."""
        quality_items = """\
- The dev server starts without errors (with .env.local configured)"""

    return f"""\
A project has been scaffolded in the current directory by multiple AI tools. \
{goal}

<project>
<name>{answers["name"]}</name>
<stack>{stack_label}</stack>
<description>{answers["description"]}</description>
</project>

<instructions>
1. Read CLAUDE.md, package.json or pyproject.toml, and scan the full project \
structure to understand what was built.
2. Try to start the project using the dev command from CLAUDE.md. If it \
fails, fix the issue and try again.
3. Run the test suite. Fix any failing tests caused by integration issues \
between phases (broken imports, missing dependencies, type errors).
4. Run lint and typecheck. Fix any errors.
{demo_instructions}
</instructions>

<scope>
You CAN modify any file in the project — application code, frontend, tests, \
config. This is the integration and QA phase.
</scope>

<quality_gate>
The project is not done until ALL of these pass:
{quality_items}
- The test suite passes (or failures are documented with clear reasons)
- Lint and typecheck pass
- No orphaned imports or missing dependencies
</quality_gate>

<extra_instructions>
{extra}
</extra_instructions>"""


def build_verify_prompt_best(answers: dict) -> str:
    """Build specialist verify prompt for Claude (ideal backend).

    Applies Claude prompting best practices for the QA/verification phase.
    """
    stack_label = STACK_LABELS.get(answers["stack"], answers["stack"])
    extra = answers.get("extra", "").strip() or "None"
    demo = answers.get("demo_mode", False)

    if demo:
        goal = (
            "Your job is to integrate everything, fix cross-phase issues, "
            "and ensure the project runs out of the box in a demo state "
            "without real API keys."
        )
        demo_instructions = """\
5. Critical: ensure the project runs WITHOUT any real API keys or .env.local:
   - Auth providers (Clerk, Auth0, etc.) must be conditionally loaded. When \
the publishable key env var is missing, bypass auth entirely and render the \
app without it. Add a visible dev banner: "Auth disabled — set \
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY to enable".
   - Database connections must fall back to in-memory mock data or seed data \
when connection strings are missing. The app should display sample content.
   - External API calls (OpenAI, Stripe, analytics, etc.) must return mock \
responses when keys are missing. Never crash or block startup.
6. Verify .env.example lists all vars with comments marking required vs \
optional.
7. Make a final git commit with all integration fixes."""
        quality_items = """\
- Dev server starts without errors and without .env.local present
- The app renders visible, meaningful content (not a crash or blank page)"""
    else:
        goal = (
            "Your job is to integrate everything, fix cross-phase issues, "
            "and ensure all checks pass."
        )
        demo_instructions = """\
5. Verify .env.example lists all required vars.
6. Make a final git commit with all integration fixes."""
        quality_items = """\
- Dev server starts without errors (with .env.local configured)"""

    return f"""\
You are a senior QA engineer reviewing a freshly scaffolded project. Multiple \
AI tools built different parts of this project — architecture, frontend, and \
tests were each created by a different tool. {goal}

<project>
<name>{answers["name"]}</name>
<stack>{stack_label}</stack>
<description>{answers["description"]}</description>
</project>

<conventions>
Read the project's CLAUDE.md for conventions, dev commands, and structure. \
That file is the source of truth for how this project should work.
</conventions>

<instructions>
1. Read CLAUDE.md, the package manager config, and scan the full project \
structure. Build a mental model of what exists.
2. Start the project using the dev command from CLAUDE.md. If it fails, \
diagnose and fix the root cause. Repeat until it starts.
3. Run the test suite. Fix any failures caused by integration issues \
between the phases (broken imports, missing deps, type mismatches, stale \
references to files that were renamed or moved).
4. Run lint and typecheck. Fix all errors.
{demo_instructions}
</instructions>

<scope>
You have full permission to modify ANY file: application code, frontend \
components, tests, configuration, styles. This is the integration phase — \
fix whatever is broken across phase boundaries.
</scope>

<quality_criteria>
Before finishing, verify ALL of these pass:
{quality_items}
- The test suite passes (document any legitimate failures with reasons)
- Lint passes with zero errors
- Typecheck passes with zero errors
- No orphaned imports, missing dependencies, or unresolved references
- .env.example is complete and accurate
</quality_criteria>

<avoid>
- Do not add new features or refactor working code. Only fix what is broken.
- Do not remove tests that were created by the testing phase. Fix them \
instead, or add a skip with a clear reason.
- Do not change the project's visual design or styling.
- Keep fixes minimal and targeted.
</avoid>

<extra_instructions>
{extra}
</extra_instructions>"""


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

    # Standalone verify phase
    if "verify" in phase_set:
        if _is_ideal_backend("verify", backend):
            return build_verify_prompt_best(answers)
        return build_verify_prompt(answers)

    # Shouldn't happen, but fallback to full prompt
    return build_prompt(answers, conventions, claude_md_template)
