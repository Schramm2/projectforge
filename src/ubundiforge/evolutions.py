"""Forge evolve — per-stack capability registry for augmenting existing projects."""

from __future__ import annotations

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
