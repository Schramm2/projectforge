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
    docker_default: bool = True
    env_hints: list[str] = field(default_factory=list)


# Cross-recipe defaults injected into every prompt
CROSS_RECIPE_DEFAULTS = """\
CROSS-PROJECT STANDARDS (apply to all Ubundi projects):

Python projects:
- pyproject.toml with hatchling build system
- Ruff for linting and formatting with rules: ["E", "F", "I", "N", "W", "UP", "B"]
- Line length: 100
- Python target: 3.12
- Package manager: uv
- pytest for testing, pytest-cov for coverage
- Include a .pre-commit-config.yaml with ruff hooks
- No ORM — use raw SQL via asyncpg for database access
- API routes prefixed with /v1/ (e.g. /v1/users, /v1/items)
- Backend services must include a /health or /ready endpoint
- Structured error responses: use Pydantic models for error bodies
- FastAPI exception handlers for consistent error formatting across all routes
- Tests in three tiers: tests/unit/, tests/integration/, tests/manual/ (optional)

TypeScript projects:
- tsconfig.json with strict mode enabled
- ESM-only ("type": "module" in package.json)
- ES2022 target
- Vitest for testing

Docker (when included):
- Use python:3.12-slim base image
- Install uv in the image
- Run as non-root user (adduser --system appuser)
- Include HEALTHCHECK on /ready or /health
- Single uvicorn worker with --limit-max-requests 10000
- EXPOSE 8000"""


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
            "agent_docs/   # Progressive disclosure docs for AI assistants",
            ".env.example  # Environment template",
            "Dockerfile    # Docker image definition",
            "CLAUDE.md     # AI assistant instructions",
            "pyproject.toml # Project metadata + tool config",
            ".pre-commit-config.yaml # Git hooks for ruff",
        ],
        common_libraries={
            "pydantic": "Data validation and serialization",
            "pydantic-settings": "Environment-based config",
            "python-dotenv": "Local env file loading",
            "asyncpg": "Async PostgreSQL driver (raw SQL, no ORM)",
            "structlog": "Structured JSON logging",
            "httpx": "Async HTTP client",
            "pytest-asyncio": "Async test support (dev)",
            "pytest-cov": "Coverage reporting (dev)",
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
        docker_default=True,
        env_hints=[
            "POSTGRES_HOST=localhost",
            "POSTGRES_PORT=5432",
            "POSTGRES_DB={project_name}",
            "POSTGRES_USER=postgres",
            "POSTGRES_PASSWORD=",
            "ENV=development",
            "PORT=8000",
        ],
    ),
    "fastapi-ai": StackMeta(
        package_manager="uv",
        default_structure=[
            "api/          # FastAPI routes, schemas, middleware",
            "api/routes/   # Route modules",
            "src/          # Core runtime / domain logic",
            "src/shared/   # LLM wrapper, embeddings service",
            "src/retrieve/ # Retrieval pipeline",
            "src/extract/  # Extraction pipeline",
            "tests/        # Test suites",
            "tests/unit/   # Fast isolated tests",
            "tests/integration/  # Multi-component tests",
            "scripts/      # Utility scripts",
            "docs/         # Documentation",
            "agent_docs/   # Progressive disclosure docs for AI assistants",
            ".env.example  # Environment template",
            "Dockerfile    # Docker image definition",
            "CLAUDE.md     # AI assistant instructions",
            "pyproject.toml # Project metadata + tool config",
            ".pre-commit-config.yaml # Git hooks for ruff",
        ],
        common_libraries={
            "pydantic": "Data validation and serialization",
            "pydantic-settings": "Environment-based config",
            "python-dotenv": "Local env file loading",
            "asyncpg": "Async PostgreSQL driver (raw SQL, no ORM)",
            "pgvector": "Vector similarity search",
            "openai": "LLM API client",
            "tiktoken": "Token counting",
            "rank-bm25": "BM25 keyword search for hybrid retrieval",
            "structlog": "Structured JSON logging",
            "httpx": "Async HTTP client",
            "tenacity": "Retry logic for LLM calls",
            "numpy": "Vector operations",
            "pytest-asyncio": "Async test support (dev)",
            "pytest-cov": "Coverage reporting (dev)",
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
        docker_default=True,
        env_hints=[
            "POSTGRES_HOST=localhost",
            "POSTGRES_PORT=5432",
            "POSTGRES_DB={project_name}",
            "POSTGRES_USER=postgres",
            "POSTGRES_PASSWORD=",
            "OPENAI_API_KEY=sk-...",
            "OPENAI_MODEL=gpt-4o-mini",
            "EMBEDDING_MODEL=text-embedding-3-small",
            "EMBEDDING_DIMENSIONS=1536",
            "ENV=development",
            "PORT=8000",
        ],
    ),
    "nextjs": StackMeta(
        package_manager="npm",
        default_structure=[
            "src/app/       # Next.js App Router pages",
            "src/components/ # React components",
            "src/lib/       # Utility functions and helpers",
            "public/        # Static assets",
            "agent_docs/    # Progressive disclosure docs for AI assistants",
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
            "Segment (analytics)",
            "Intercom (support)",
        ],
        docker_default=False,
        env_hints=[
            "NEXT_PUBLIC_API_URL=http://localhost:8000",
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
            "agent_docs/    # Progressive disclosure docs for AI assistants",
            "docker-compose.yml",
            ".env.example",
            "CLAUDE.md",
            ".pre-commit-config.yaml # Git hooks for ruff",
        ],
        common_libraries={
            "fastapi": "Web framework",
            "pydantic": "Validation",
            "asyncpg": "PostgreSQL driver (raw SQL, no ORM)",
            "structlog": "Structured JSON logging",
            "httpx": "Async HTTP client",
            "tailwindcss": "Styling",
            "pytest-asyncio": "Async test support (dev)",
            "pytest-cov": "Coverage reporting (dev)",
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
            "Segment (analytics)",
            "AWS (S3, EC2)",
        ],
        docker_default=True,
        env_hints=[
            "POSTGRES_HOST=localhost",
            "POSTGRES_PORT=5432",
            "POSTGRES_DB={project_name}",
            "POSTGRES_USER=postgres",
            "POSTGRES_PASSWORD=",
            "NEXT_PUBLIC_API_URL=http://localhost:8000",
            "ENV=development",
            "PORT=8000",
        ],
    ),
    "python-cli": StackMeta(
        package_manager="uv",
        default_structure=[
            "src/           # Main package",
            "src/__init__.py",
            "src/cli.py     # CLI entrypoint",
            "tests/         # Test suite",
            "agent_docs/    # Progressive disclosure docs for AI assistants",
            "pyproject.toml",
            "README.md",
            "CLAUDE.md",
            ".gitignore",
            ".pre-commit-config.yaml # Git hooks for ruff",
        ],
        common_libraries={
            "typer": "CLI framework with auto-help",
            "rich": "Terminal styling and output",
            "questionary": "Interactive prompts",
            "pytest-cov": "Coverage reporting (dev)",
        },
        dev_commands={
            "lint": "uv run ruff check src",
            "format": "uv run ruff format src",
            "test": "uv run pytest tests/",
        },
        services=[],
        docker_default=False,
        env_hints=[],
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
            "agent_docs/    # Progressive disclosure docs for AI assistants",
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
        docker_default=False,
        env_hints=[],
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
            "agent_docs/    # Progressive disclosure docs for AI assistants",
            "Dockerfile",
            ".env.example",
            "pyproject.toml",
            "README.md",
            "CLAUDE.md",
            ".pre-commit-config.yaml # Git hooks for ruff",
        ],
        common_libraries={
            "boto3": "AWS SDK (DynamoDB, S3, etc.)",
            "requests": "HTTP client",
            "structlog": "Structured JSON logging",
            "python-dotenv": "Local env file loading",
            "pytest-cov": "Coverage reporting (dev)",
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
        docker_default=True,
        env_hints=[
            "AWS_REGION=us-east-1",
            "AWS_ACCESS_KEY_ID=",
            "AWS_SECRET_ACCESS_KEY=",
            "SLACK_WEBHOOK_URL=",
            "ENV=development",
        ],
    ),
}
