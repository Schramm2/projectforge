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
