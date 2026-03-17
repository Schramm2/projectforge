"""Stack metadata — structures, libraries, commands, and services per stack."""

from dataclasses import dataclass, field


@dataclass
class StackMeta:
    """Metadata for a supported stack."""

    package_manager: str
    default_structure: list[str]
    common_libraries: dict[str, str]
    dev_commands: dict[str, str]
    services: list[str] = field(default_factory=list)


STACK_META: dict[str, StackMeta] = {
    "fastapi": StackMeta(
        package_manager="uv",
        default_structure=[
            "api/          # FastAPI routes, schemas, middleware",
            "api/routes/   # Route modules",
            "src/          # Core runtime / domain logic",
            "tests/        # Test suites",
            "tests/unit/   # Fast isolated tests",
            "tests/integration/  # Multi-component tests",
            "scripts/      # Utility scripts",
            "docs/         # Documentation",
            ".env.example  # Environment template",
            "Dockerfile    # Docker image definition",
            "CLAUDE.md     # AI assistant instructions",
            "pyproject.toml # Project metadata + tool config",
        ],
        common_libraries={
            "pydantic": "Data validation and serialization",
            "pydantic-settings": "Environment-based config",
            "python-dotenv": "Local env file loading",
            "asyncpg": "Async PostgreSQL driver",
            "structlog": "Structured logging",
            "httpx": "Async HTTP client",
        },
        dev_commands={
            "lint": "uv run ruff check src api",
            "format": "uv run ruff format src api",
            "typecheck": "uv run mypy src",
            "test": "uv run pytest tests/unit/ -v --tb=short",
            "run": "uvicorn api.app:app --host 0.0.0.0 --port 8000",
        },
        services=[
            "PostgreSQL (with pgvector extension)",
            "OpenAI API",
            "AWS (S3, ECS, Lambda, DynamoDB)",
        ],
    ),
    "nextjs": StackMeta(
        package_manager="npm",
        default_structure=[
            "src/app/       # Next.js App Router pages",
            "src/components/ # React components",
            "src/lib/       # Utility functions and helpers",
            "public/        # Static assets",
            "next.config.ts # Next.js configuration",
            "tailwind.config.ts # Tailwind configuration",
            "tsconfig.json  # TypeScript configuration",
            "package.json   # Dependencies and scripts",
        ],
        common_libraries={
            "tailwindcss": "Utility-first CSS",
            "@tailwindcss/postcss": "PostCSS integration",
        },
        dev_commands={
            "dev": "npm run dev",
            "build": "npm run build",
            "lint": "npm run lint",
            "typecheck": "npx tsc --noEmit",
        },
        services=[
            "Clerk (auth)",
            "Segment (analytics)",
            "Intercom (support)",
        ],
    ),
    "both": StackMeta(
        package_manager="uv + npm",
        default_structure=[
            "api/           # FastAPI backend",
            "frontend/      # Next.js frontend",
            "domain/        # Shared domain logic (Python)",
            "application/   # Business orchestration (Python)",
            "infrastructure/ # External service adapters (Python)",
            "tests/         # Backend tests",
            "scripts/       # Utility scripts",
            "docker/        # Docker configs",
            "docker-compose.yml",
            ".env.example",
            "CLAUDE.md",
        ],
        common_libraries={
            "fastapi": "Web framework",
            "pydantic": "Validation",
            "asyncpg": "PostgreSQL driver",
            "structlog": "Logging",
            "tailwindcss": "Styling",
        },
        dev_commands={
            "backend_run": "uvicorn api.server:app --reload --port 8000",
            "frontend_dev": "cd frontend && npm run dev",
            "lint": "uv run ruff check . && cd frontend && npm run lint",
            "test": "uv run pytest tests/",
        },
        services=[
            "PostgreSQL + pgvector",
            "OpenAI API",
            "Clerk (auth)",
            "Segment (analytics)",
            "AWS (S3, EC2)",
        ],
    ),
    "python-cli": StackMeta(
        package_manager="uv",
        default_structure=[
            "src/           # Main package",
            "src/__init__.py",
            "src/cli.py     # CLI entrypoint",
            "tests/         # Test suite",
            "pyproject.toml",
            "README.md",
            "CLAUDE.md",
            ".gitignore",
        ],
        common_libraries={
            "typer": "CLI framework with auto-help",
            "rich": "Terminal styling and output",
            "questionary": "Interactive prompts",
        },
        dev_commands={
            "lint": "uv run ruff check src",
            "format": "uv run ruff format src",
            "test": "uv run pytest tests/",
        },
        services=[],
    ),
    "ts-package": StackMeta(
        package_manager="npm",
        default_structure=[
            "src/           # TypeScript source",
            "src/index.ts   # Public entrypoint",
            "tests/         # Test suite",
            "tests/unit/    # Unit tests",
            "tests/integration/ # Integration tests",
            "dist/          # Compiled output (gitignored)",
            "tsconfig.json  # TypeScript config",
            "vitest.config.ts # Test config",
            "package.json",
            "README.md",
            "CLAUDE.md",
            "CHANGELOG.md",
            ".gitignore",
        ],
        common_libraries={
            "zod": "Schema validation",
            "vitest": "Test runner",
            "typescript": "Compiler",
        },
        dev_commands={
            "build": "tsc",
            "test": "vitest run",
            "typecheck": "npx tsc --noEmit",
        },
        services=[],
    ),
    "python-worker": StackMeta(
        package_manager="uv",
        default_structure=[
            "src/           # Main package",
            "src/__init__.py",
            "src/cli.py     # CLI dispatcher",
            "src/models.py  # Data models",
            "src/storage.py # Storage layer",
            "src/services.py # Business logic",
            "config/        # Configuration files",
            "infra/         # CloudFormation / Terraform",
            "tests/         # Test suite",
            "Dockerfile",
            ".env.example",
            "pyproject.toml",
            "README.md",
            "CLAUDE.md",
        ],
        common_libraries={
            "boto3": "AWS SDK (DynamoDB, S3, etc.)",
            "requests": "HTTP client",
        },
        dev_commands={
            "lint": "uv run ruff check src",
            "test": "uv run pytest tests/",
            "docker_build": "docker build -t worker .",
        },
        services=[
            "AWS DynamoDB",
            "AWS ECS Fargate",
            "AWS EventBridge (scheduling)",
            "Slack API",
        ],
    ),
}
