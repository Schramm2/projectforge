"""Forge evolve — per-stack capability registry for augmenting existing projects."""

from __future__ import annotations

import json
from pathlib import Path

CAPABILITIES: dict[str, list[dict]] = {
    "fastapi": [
        {
            "name": "auth",
            "description": "Add authentication with Clerk",
            "prompt_fragment": (
                "Add Clerk authentication to this FastAPI project. "
                "Create auth middleware, protect routes, add user endpoints. "
                "Use pydantic-settings for CLERK_SECRET_KEY config."
            ),
            "typically_touches": ["api/app.py", "api/routes/", "dependencies.py", ".env.example"],
        },
        {
            "name": "websockets",
            "description": "Add WebSocket support",
            "prompt_fragment": (
                "Add WebSocket support to this FastAPI project. "
                "Create a WebSocket endpoint with connection management, "
                "room-based broadcasting, and reconnection handling."
            ),
            "typically_touches": ["api/app.py", "api/routes/", "domain/services/"],
        },
        {
            "name": "s3-uploads",
            "description": "Add S3 file uploads",
            "prompt_fragment": (
                "Add S3 file upload support. Create upload endpoints with "
                "presigned URLs, file validation, and a storage abstraction layer."
            ),
            "typically_touches": ["api/routes/", "infrastructure/external/", ".env.example"],
        },
        {
            "name": "stripe",
            "description": "Add Stripe billing",
            "prompt_fragment": (
                "Add Stripe billing integration. Create checkout sessions, "
                "webhook handlers, and subscription management endpoints."
            ),
            "typically_touches": [
                "api/routes/",
                "domain/services/",
                "infrastructure/external/",
                ".env.example",
            ],
        },
        {
            "name": "worker",
            "description": "Add background worker",
            "prompt_fragment": (
                "Add a background task worker using Python's asyncio. "
                "Create a task queue, worker process, and task status endpoints."
            ),
            "typically_touches": ["domain/services/", "infrastructure/", "api/routes/"],
        },
        {
            "name": "monitoring",
            "description": "Add monitoring and observability",
            "prompt_fragment": (
                "Add structured logging with structlog, request ID tracking, "
                "Prometheus metrics endpoint, and health/readiness probes."
            ),
            "typically_touches": ["api/app.py", "shared/", ".env.example"],
        },
    ],
    "nextjs": [
        {
            "name": "auth",
            "description": "Add authentication with Clerk",
            "prompt_fragment": (
                "Add Clerk authentication to this Next.js project. "
                "Set up ClerkProvider, sign-in/sign-up pages, "
                "middleware for protected routes, and user profile page."
            ),
            "typically_touches": [
                "src/app/layout.tsx",
                "src/app/",
                "middleware.ts",
                ".env.example",
            ],
        },
        {
            "name": "analytics",
            "description": "Add Segment analytics",
            "prompt_fragment": (
                "Add Segment analytics tracking. Set up the analytics provider, "
                "page view tracking, and custom event helpers."
            ),
            "typically_touches": ["src/app/layout.tsx", "src/lib/"],
        },
        {
            "name": "i18n",
            "description": "Add internationalization",
            "prompt_fragment": (
                "Add i18n support using next-intl. Set up locale routing, "
                "translation files, and language switcher component."
            ),
            "typically_touches": ["src/app/", "src/components/", "next.config.ts"],
        },
    ],
}

# Composite stacks inherit capabilities
CAPABILITIES["both"] = CAPABILITIES["fastapi"] + CAPABILITIES["nextjs"]
CAPABILITIES["fastapi-ai"] = CAPABILITIES["fastapi"]


def get_capabilities(stack: str) -> list[dict]:
    """Return available evolution capabilities for a stack."""
    return CAPABILITIES.get(stack, [])


def get_capability(stack: str, name: str) -> dict | None:
    """Return a specific capability by name, or None if not found."""
    for cap in get_capabilities(stack):
        if cap["name"] == name:
            return cap
    return None


_TOKEN_CAP = 8000
_CHARS_PER_TOKEN = 4
_CONTENT_CHAR_CAP = _TOKEN_CAP * _CHARS_PER_TOKEN

_HIDDEN_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".forge"}


def _read_project_dna(project_dir: Path) -> dict:
    """Read .forge/scaffold.json from the project."""
    manifest_path = project_dir / ".forge" / "scaffold.json"
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _collect_file_tree(project_dir: Path) -> str:
    """Generate a simple file tree string."""
    lines: list[str] = []
    for path in sorted(project_dir.rglob("*")):
        rel = path.relative_to(project_dir)
        if any(part in _HIDDEN_DIRS or part.startswith(".") for part in rel.parts):
            continue
        if path.is_file():
            lines.append(str(rel))
    return "\n".join(lines)


def _collect_file_contents(project_dir: Path, capability: dict) -> str:
    """Read key files for the evolve prompt, capped by token budget."""
    files_to_read: list[Path] = []

    for config in ("pyproject.toml", "package.json"):
        config_path = project_dir / config
        if config_path.exists():
            files_to_read.append(config_path)

    for entry in ("api/app.py", "src/app/layout.tsx", "src/cli.py", "src/main.py"):
        entry_path = project_dir / entry
        if entry_path.exists():
            files_to_read.append(entry_path)
            break

    for touch_path in capability.get("typically_touches", []):
        full = project_dir / touch_path
        if full.exists() and full.is_file() and full not in files_to_read:
            files_to_read.append(full)

    content_parts: list[str] = []
    total_chars = 0
    for file_path in files_to_read:
        try:
            text = file_path.read_text(errors="replace")
        except OSError:
            continue
        if total_chars + len(text) > _CONTENT_CHAR_CAP:
            remaining = _CONTENT_CHAR_CAP - total_chars
            if remaining > 200:
                text = text[:remaining] + "\n... (truncated)"
            else:
                break
        rel = file_path.relative_to(project_dir)
        content_parts.append(f"### {rel}\n```\n{text}\n```")
        total_chars += len(text)

    return "\n\n".join(content_parts)


def build_evolve_prompt(project_dir: Path, capability: dict) -> str:
    """Assemble the full evolve prompt for a capability."""
    dna = _read_project_dna(project_dir)
    file_tree = _collect_file_tree(project_dir)
    file_contents = _collect_file_contents(project_dir, capability)

    stack = dna.get("stack", "unknown")
    name = dna.get("name", project_dir.name)
    description = dna.get("description", "")

    return (
        "You are augmenting an existing project with a new capability.\n\n"
        f"PROJECT: {name}\n"
        f"STACK: {stack}\n"
        f"DESCRIPTION: {description}\n\n"
        f"CAPABILITY TO ADD: {capability.get('name', '')}\n"
        f"{capability.get('prompt_fragment', '')}\n\n"
        f"CURRENT FILE TREE:\n{file_tree}\n\n"
        f"KEY FILES:\n{file_contents}\n\n"
        "INSTRUCTIONS:\n"
        "- Add this capability to the existing project without breaking existing functionality\n"
        "- Follow the existing code patterns and conventions\n"
        "- Update .env.example with any new required variables\n"
        "- Add tests for the new functionality\n"
        "- Update the README if needed\n"
    )
