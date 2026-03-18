"""Loads and manages convention and template files from ~/.forge/."""

from pathlib import Path

FORGE_DIR = Path.home() / ".forge"
CONVENTIONS_PATH = FORGE_DIR / "conventions.md"
CLAUDE_MD_TEMPLATE_PATH = Path(__file__).parent / "templates" / "claude-md-template.md"

DEFAULT_CONVENTIONS = """\
# Ubundi Project Conventions

Follow these conventions when generating any project files.

## Brand & Styling (Frontend Projects)

- Use Tailwind CSS for all styling
- Ubundi brand palette:
  - Backgrounds: dark blue-grey (#1A2332 to #2A3444)
  - Accents: cyan-teal (#0FA5A5, #0CC5C5)
  - Text: white on dark backgrounds
  - Cards/panels: glassmorphism (backdrop-blur, semi-transparent bg)
- Fonts: Inter for UI text, JetBrains Mono for code blocks
- Configure fonts in tailwind.config
- Dark mode is the default theme
- Components should be modern, clean, minimal
- No heavy shadows. Use subtle borders with opacity

## Frontend Communication Patterns

- One user action = one API call. Combine related sequential calls into single endpoints.
- Use response data directly — don't discard it and refetch the same information.
- Atomic state updates: update all related state from a single response to prevent flickering.
- API client methods named after user actions, not backend structure.

## Coding Standards

### TypeScript / Next.js
- TypeScript strict mode. No 'any' types.
- App router (app/ directory)
- Components in src/components/
- Utilities in src/lib/
- ESLint + Prettier configured

### Python / FastAPI
- Type hints on all functions and variables
- Pydantic models for all data structures
- Async endpoints where possible
- No ORM — use raw SQL via asyncpg
- API routes prefixed with /v1/
- Structured error responses using Pydantic models for error bodies
- FastAPI exception handlers for consistent error formatting
- Ruff for linting and formatting
- Docstrings (triple double quotes) on all public modules, functions, classes, and methods
- Imports ordered: stdlib → third-party → local application. No wildcard imports.

## Python Architecture

Follow Clean Architecture (Onion Architecture). Dependencies point inward.

### Layer Structure
- domain/: Core business logic — entities, value objects, domain services,
  interfaces (Protocols). Depends on NOTHING (stdlib only).
- application/: Use cases and orchestration. Depends only on domain.
- infrastructure/: External implementations — DB repositories, API clients,
  config loading. Implements interfaces defined in domain.
- api/: Presentation layer — FastAPI routes, request/response schemas.
  Depends on application.
- shared/: Cross-cutting utilities used across layers. Keep minimal.

### Dependency Flow
Presentation (api/) → Application → Domain ← Infrastructure

### Service Layer Pattern
- Encapsulate business logic in Service Classes (e.g., UserService), not standalone functions.
- Inject dependencies via __init__ (database sessions, external clients).
- No global state — all state passed through constructor or method params.

### FastAPI Patterns
- Use @lru_cache for singleton services in a dedicated dependencies.py file.
- Load state once per request: load → process → persist. No repeated DB queries for the same data.
- Inject services into route handlers — never instantiate inline.
- Combined endpoints: if the frontend always calls two endpoints in sequence, combine them.

### File Naming
- Models: *_model.py (e.g., user_model.py)
- Services: *_service.py (e.g., payment_service.py)
- Repositories: *_repository.py (e.g., user_repository.py)
- Tests: test_*.py (e.g., test_payment_service.py)

## Always Include
- .gitignore appropriate to the stack
- .env.example showing all required environment variables
- README.md with project name, description, setup instructions, and how to run
- CLAUDE.md at root — a briefing for AI coding assistants containing:
  project name, description, stack, folder structure, conventions, and any
  project-specific notes. Write it as a direct briefing, not documentation.

## Git

- GitHub Flow: main branch always deployable, short-lived feature branches
- Branch naming: type/description (e.g., feat/user-login, fix/header-alignment, docs/update-readme)
- Conventional commit messages (e.g., feat: add login, fix: resolve crash)
- Initialize git on project creation
- PR template: Summary, Type of Change, Testing, Screenshots (if UI)
"""


MIN_CONVENTIONS_LENGTH = 50


LOCAL_CONVENTIONS_PATH = Path.cwd() / ".forge" / "conventions.md"


def load_conventions() -> tuple[str, list[str]]:
    """Load conventions, checking local .forge/conventions.md first, then ~/.forge/.

    Returns:
        Tuple of (conventions_content, warnings).
    """
    warnings: list[str] = []

    # Check for project-local conventions first
    if LOCAL_CONVENTIONS_PATH.exists():
        source = LOCAL_CONVENTIONS_PATH
        warnings.append(f"Using local conventions from {LOCAL_CONVENTIONS_PATH}")
    else:
        source = CONVENTIONS_PATH
        if not source.exists():
            FORGE_DIR.mkdir(parents=True, exist_ok=True)
            source.write_text(DEFAULT_CONVENTIONS)
            warnings.append("Created default conventions at ~/.forge/conventions.md")

    content = source.read_text()

    if not content.strip():
        warnings.append("Conventions file is empty — scaffolds will lack guidance.")
    elif len(content.strip()) < MIN_CONVENTIONS_LENGTH:
        warnings.append("Conventions file is very short — consider adding more detail.")

    return content, warnings


def load_claude_md_template() -> str | None:
    """Load the CLAUDE.md template from ~/.forge/claude-md-template.md.

    Returns None if the file doesn't exist — the prompt builder will
    fall back to its generic instruction.
    """
    if CLAUDE_MD_TEMPLATE_PATH.exists():
        return CLAUDE_MD_TEMPLATE_PATH.read_text()
    return None
