# Stacks

Forge supports 7 project stacks. Each stack defines a default project structure, libraries, dev commands, and conventions that get encoded into the scaffold prompt.

All stacks share cross-recipe defaults:

- **Python stacks:** Ruff for linting and formatting, pytest for tests, structlog for logging, pyproject.toml for packaging.
- **TypeScript stacks:** Strict tsconfig, ESLint with recommended rules, Prettier for formatting.

---

## Next.js + React

**Identifier:** `nextjs`
**Aliases:** `next`, `react`
**Docker default:** off

Full-stack React application using the Next.js App Router.

**Project structure:**

```
app/              App Router pages and layouts
components/       Reusable React components
lib/              Utility functions and shared logic
public/           Static assets
```

**Key libraries:** Tailwind CSS, shadcn/ui, Zustand, React Hook Form, Zod.

**Dev commands:**

```bash
npm run dev       # Start dev server
npm run build     # Production build
npm run lint      # ESLint
npm run test      # Vitest
```

---

## FastAPI

**Identifier:** `fastapi`
**Aliases:** `api`
**Docker default:** on

Python REST API with clean architecture and layered separation of concerns.

**Project structure:**

```
api/routes/                  Route handlers
domain/models/               Pydantic domain models
domain/services/             Business logic
infrastructure/persistence/  Database and external service adapters
tests/unit/                  Unit tests
tests/integration/           Integration tests
```

**Key libraries:** Pydantic, asyncpg, structlog, httpx.

**Dev commands:**

```bash
uv run uvicorn api.main:app --reload   # Start dev server
uv run pytest                           # Run tests
uv run ruff check .                     # Lint
uv run ruff format .                    # Format
```

---

## FastAPI + AI/LLM

**Identifier:** `fastapi-ai`
**Aliases:** `ai`, `llm`
**Docker default:** on

FastAPI backend with AI and LLM integration. Extends the base FastAPI stack with AI-specific tooling.

**Project structure:**

Same as FastAPI, plus:

```
domain/agents/       Agent definitions and orchestration
domain/prompts/      Prompt templates and management
infrastructure/vectorstore/  Vector store integration
```

**Key libraries:** Everything in FastAPI, plus LangChain or LlamaIndex, vector store support (Pinecone, Weaviate, or pgvector), prompt management utilities.

**Dev commands:** Same as FastAPI.

---

## Next.js + FastAPI Monorepo

**Identifier:** `both`
**Aliases:** `fullstack`, `monorepo`
**Docker default:** on

Monorepo combining a Next.js frontend and FastAPI backend, managed with Turborepo.

**Project structure:**

```
apps/
  web/             Next.js application (same structure as nextjs stack)
  api/             FastAPI application (same structure as fastapi stack)
packages/          Shared packages (types, utilities)
turbo.json         Turborepo configuration
```

**Key libraries:** Combines both the Next.js and FastAPI library sets. Turborepo for build orchestration.

**Dev commands:**

```bash
turbo dev          # Start all services
turbo build        # Build all packages
turbo lint         # Lint all packages
turbo test         # Test all packages
```

---

## Python CLI Tool

**Identifier:** `python-cli`
**Aliases:** `cli`, `typer`
**Docker default:** off

Command-line application with Typer for argument parsing and Rich for terminal output.

**Project structure:**

```
src/<package>/     Source package
  __init__.py
  __main__.py
  cli.py           Typer app definition
tests/             pytest test suite
pyproject.toml     Package configuration
```

**Key libraries:** Typer, Rich, pytest.

**Dev commands:**

```bash
uv run python -m <package>    # Run CLI
uv run pytest                  # Run tests
uv run ruff check .            # Lint
uv run ruff format .           # Format
```

---

## TypeScript npm Package

**Identifier:** `ts-package`
**Aliases:** `npm-package`, `library`
**Docker default:** off

Publishable npm package with TypeScript, bundled for distribution.

**Project structure:**

```
src/              Source TypeScript files
dist/             Compiled output (generated)
tests/            Test suite
tsconfig.json     TypeScript configuration
package.json      Package manifest
```

**Key libraries:** tsup for bundling, Vitest for testing.

**Dev commands:**

```bash
npm run build      # Bundle with tsup
npm run test       # Run Vitest
npm run lint       # ESLint
npm run prepublishOnly  # Build before publish
```

---

## Python Worker

**Identifier:** `python-worker`
**Aliases:** `worker`, `service`
**Docker default:** on

Background worker or scheduled service. Shares the FastAPI clean architecture minus the HTTP API layer.

**Project structure:**

```
domain/models/               Domain models
domain/services/             Business logic and task definitions
infrastructure/persistence/  Database and external service adapters
worker/                      Worker entry point and scheduling
tests/unit/                  Unit tests
tests/integration/           Integration tests
```

**Key libraries:** APScheduler or Celery for task scheduling, structlog for logging, Pydantic for data validation.

**Dev commands:**

```bash
uv run python -m worker       # Start worker
uv run pytest                  # Run tests
uv run ruff check .            # Lint
uv run ruff format .           # Format
```
