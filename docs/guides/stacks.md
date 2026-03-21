# Stacks

Forge currently supports 7 scaffold stacks. Each stack contributes structure, common libraries, default dev commands, optional services, and Docker defaults to the generated prompt.

All Python-oriented stacks share these broad defaults:

- `uv` for package management
- Ruff for linting and formatting
- MyPy `--strict` for type checking
- pytest-based test suites
- `.pre-commit-config.yaml`

All TypeScript-oriented stacks share these broad defaults:

- strict `tsconfig.json`
- ESM-first package setup
- Vitest-oriented testing guidance

## Next.js + React

**Identifier:** `nextjs`  
**Aliases:** `next`, `react`  
**Package manager:** `npm`  
**Docker default:** off

**Default structure:**

```text
src/app/          Next.js App Router pages
src/components/   React components
src/lib/          Shared helpers and utilities
public/           Static assets
agent_docs/       Progressive disclosure docs for AI assistants
```

**Common libraries:** Tailwind CSS, `@tailwindcss/postcss`

**Default dev commands:**

```bash
npm run dev
npm run build
npm run lint
npx tsc --noEmit
```

**Structured options available:** auth provider, CI workflow, design template, media import

## FastAPI

**Identifier:** `fastapi`  
**Aliases:** `api`  
**Package manager:** `uv`  
**Docker default:** on

**Default structure:**

```text
api/                         FastAPI routes, schemas, middleware
domain/                      Core business logic and interfaces
application/                 Use cases and orchestration
infrastructure/              Database and external integrations
shared/                      Cross-cutting helpers
tests/unit/                  Unit tests
tests/integration/           Integration tests
agent_docs/                  Progressive disclosure docs for AI assistants
```

**Common libraries:** Pydantic, `pydantic-settings`, `asyncpg`, `structlog`, `httpx`

**Default dev commands:**

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000
uv run ruff check .
uv run ruff format .
uv run mypy --strict .
uv run pytest tests/unit/ -v --tb=short
```

**Typical optional services:** PostgreSQL with pgvector, OpenAI API, AWS services

## FastAPI + AI/LLM

**Identifier:** `fastapi-ai`  
**Aliases:** `ai`, `llm`  
**Package manager:** `uv`  
**Docker default:** on

**Default structure:**

```text
api/                            FastAPI routes, schemas, middleware
domain/                         Core business logic
application/retrieve/           Retrieval pipeline use cases
application/extract/            Extraction pipeline use cases
infrastructure/persistence/     Database and vector-store integrations
infrastructure/external/        LLM and embedding providers
shared/                         Cross-cutting helpers
tests/unit/                     Unit tests
tests/integration/              Integration tests
agent_docs/                     Progressive disclosure docs for AI assistants
```

**Common libraries:** everything in `fastapi`, plus `pgvector`, `openai`, `tiktoken`, `rank-bm25`, `tenacity`, `numpy`

**Default dev commands:** same as `fastapi`

**Typical optional services:** PostgreSQL with pgvector, OpenAI API, AWS services

## Next.js + FastAPI

**Identifier:** `both`  
**Aliases:** `fullstack`, `monorepo`  
**Package manager:** `uv + npm`  
**Docker default:** on

**Default structure:**

```text
api/               FastAPI routes and schemas
frontend/          Next.js frontend
domain/            Core business logic
application/       Use cases and orchestration
infrastructure/    External integrations
shared/            Cross-cutting helpers
tests/             Python test suite
docker/            Docker-specific files
agent_docs/        Progressive disclosure docs for AI assistants
```

**Common libraries:** FastAPI, Pydantic, `asyncpg`, `structlog`, `httpx`, Tailwind CSS, `pytest-asyncio`, `pytest-cov`

**Default dev commands:**

```bash
uvicorn api.server:app --reload --port 8000
cd frontend && npm run dev
uv run ruff check . && cd frontend && npm run lint
uv run pytest tests/
```

**Structured options available:** auth provider, CI workflow, design template, media import

## Python CLI Tool

**Identifier:** `python-cli`  
**Aliases:** `cli`, `typer`  
**Package manager:** `uv`  
**Docker default:** off

**Default structure:**

```text
src/               Main package
src/__init__.py
src/cli.py         CLI entrypoint
tests/             pytest suite
agent_docs/        Progressive disclosure docs for AI assistants
pyproject.toml
```

**Common libraries:** Typer, Rich, Questionary, `pytest-cov`

**Default dev commands:**

```bash
uv run ruff check src
uv run ruff format src
uv run pytest tests/
```

## TypeScript npm Package

**Identifier:** `ts-package`  
**Aliases:** `npm-package`, `library`  
**Package manager:** `npm`  
**Docker default:** off

**Default structure:**

```text
src/               TypeScript source
src/index.ts       Public entrypoint
tests/             Test suite
tests/unit/        Unit tests
tests/integration/ Integration tests
dist/              Compiled output (gitignored)
agent_docs/        Progressive disclosure docs for AI assistants
tsconfig.json
vitest.config.ts
package.json
```

**Common libraries:** TypeScript, Vitest, Zod

**Default dev commands:**

```bash
tsc
vitest run
npx tsc --noEmit
```

## Python Worker

**Identifier:** `python-worker`  
**Aliases:** `worker`, `service`  
**Package manager:** `uv`  
**Docker default:** on

**Default structure:**

```text
src/               Main package
src/cli.py         CLI dispatcher
src/models.py      Data models
src/storage.py     Storage layer
src/services.py    Business logic
config/            Configuration files
infra/             Infrastructure definitions
tests/             Test suite
agent_docs/        Progressive disclosure docs for AI assistants
```

**Common libraries:** `boto3`, `requests`, `structlog`, `python-dotenv`, `pytest-cov`

**Default dev commands:**

```bash
uv run ruff check src
uv run pytest tests/
docker build -t worker .
```

**Typical optional services:** AWS DynamoDB, ECS Fargate, EventBridge, Slack API
