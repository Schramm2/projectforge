# Forge Stack Selection

Choose the stack that best matches the delivered artifact and operating model.

## `nextjs`

Use for:

- frontend-heavy products
- marketing sites with app surfaces
- dashboard-style web apps
- cases where authentication or design templates matter

Aliases:

- `next`
- `react`

Notable options:

- supports `--auth-provider`
- supports `--design-template`
- default Docker is off

## `fastapi`

Use for:

- standard Python APIs
- internal services
- CRUD backends
- service-oriented apps without heavy LLM features

Aliases:

- `api`

Notable traits:

- strong Clean Architecture bias
- raw SQL via `asyncpg`, not ORM
- default Docker is on

## `fastapi-ai`

Use for:

- retrieval systems
- embedding pipelines
- LLM-backed APIs
- pgvector or OpenAI-centric backends

Aliases:

- `ai`
- `llm`

Notable traits:

- includes retrieval and extraction architecture
- expects OpenAI and pgvector patterns
- default Docker is on

## `both`

Use for:

- a true Next.js plus FastAPI monorepo
- products that need a distinct frontend and backend from day one
- teams that want one scaffold with shared conventions across both layers

Aliases:

- `fullstack`
- `monorepo`

Notable options:

- supports `--auth-provider`
- supports `--design-template`
- default Docker is on

## `python-cli`

Use for:

- internal developer tools
- operational CLIs
- terminal-based assistants or automations

Aliases:

- `cli`
- `typer`

Notable traits:

- Typer and Rich conventions
- default Docker is off

## `ts-package`

Use for:

- npm libraries
- SDKs
- reusable TypeScript modules
- typed shared packages

Aliases:

- `npm-package`
- `library`

Notable traits:

- ESM-only bias
- Vitest and strict TypeScript
- default Docker is off

## `python-worker`

Use for:

- scheduled jobs
- queue or batch workers
- integrations that run in the background
- AWS-oriented processing services

Aliases:

- `worker`
- `service`

Notable traits:

- AWS and Slack-friendly defaults
- Docker-oriented worker shape
- default Docker is on

## Selection Heuristics

- If the user asks for a browser UI, start with `nextjs` unless they clearly need a separate backend codebase.
- If the user asks for an API plus a separate web client, choose `both`.
- If the user wants embeddings, retrieval, vector search, or LLM service behavior, prefer `fastapi-ai` over plain `fastapi`.
- If the user wants a reusable package rather than an app, choose `ts-package` or `python-cli` based on ecosystem and distribution target.
- If the user wants a scheduled or event-driven service, prefer `python-worker`.
