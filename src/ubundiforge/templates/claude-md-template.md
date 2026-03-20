# {Project Name}

## WHY

{One to three sentences explaining what this project does and why it exists. Focus on the problem it solves, not implementation details.}

## WHAT

### Tech Stack

- {Language + version} (`pyproject.toml` / `package.json`)
- Package manager: {uv / npm / etc.}
- {Framework} for {purpose}
- {Database} for {persistence/search/etc.}
- {External services: LLM provider, cloud provider, etc.}

### Project Structure

```
{root}/
├── src/              # Core runtime
│   ├── module_a/     # {responsibility}
│   ├── module_b/     # {responsibility}
│   └── ...
├── api/              # HTTP/API surface
├── tests/            # Test suites
│   ├── unit/         # Fast isolated tests
│   ├── integration/  # Multi-component tests (may need env vars)
│   └── manual/       # Manual runners (not auto-collected)
├── docs/             # Documentation
├── scripts/          # Build/deploy/utility scripts
└── agent_docs/       # Task-specific deep dives (progressive disclosure)
```

### Key Entrypoints

{List the 5-8 most important files with line references. These are the files someone should read first to understand the system.}

- `src/core.py:61` — {What it does}
- `src/config.py:131` — {What it does}
- `api/app.py:39` — {What it does}

### Architecture

{One sentence on the architectural pattern, e.g. "Clean architecture with strict dependency direction: api → application → domain ← infrastructure." or "Thin lifecycle facade delegating to feature-based services."}

## HOW

### Setup

```bash
# Install dependencies
{uv sync / npm ci}

# Run the project
{uvicorn api.app:app / npm start}
```

### Verify Changes

{Run all checks before committing. These mirror CI — failures here will fail the pipeline.}

```bash
# Lint
{uv run ruff check src api / npm run lint}

# Format
{uv run ruff format --check src api / npx prettier --check .}

# Type check (if applicable)
{npx tsc --noEmit}

# Unit tests
{uv run pytest tests/unit/ / npm test}

# Coverage (optional)
{uv run pytest --cov=src}
```

If lint or format fails, auto-fix with `{ruff check --fix / npm run lint:fix}` and re-run all checks.

### Required Environment Variables

- `{VAR_NAME}` — {what it's for}
- `{DATABASE_URL}` — {connection details, defaults}

### Git Workflow

- {Branch strategy, e.g. "Merging dev → main: git merge dev --no-ff"}
- {Sync strategy, e.g. "Syncing main → dev: git rebase main"}
- {PR policy, e.g. "Prefer PRs via gh pr create for merges into main"}

### Commit Convention

{e.g. "Conventional Commits (feat:, fix:, docs:, chore:)" or describe your convention.}

## Key Patterns

{Document non-obvious architectural decisions and patterns that would trip someone up. These are the things you'd explain to a new team member in their first week.}

- **{Pattern name}**: {Explanation + pointer to code, e.g. "Hook registration uses registerHookCompat() which prefers api.on() over api.registerHook() — see src/plugin/index.ts:161"}
- **{Pattern name}**: {Explanation}

## Non-Obvious Things

{Gotchas, traps, and surprising behaviors. Things that look wrong but are intentional, or things that look right but will break.}

- {e.g. "Dual-instance runtime: The framework runs two plugin instances — only one gets start() called. All initialization must happen in register(), not start()."}
- {e.g. "1 uvicorn worker only — multiple workers cause memory exhaustion and deadlock storms"}

## Infrastructure

{Only include if the project is deployed. Remove this section for libraries or local-only tools.}

- **Deployment**: {e.g. "ECS Fargate, cluster: my-cluster, service: my-service"}
- **Logs**: {e.g. "CloudWatch /ecs/my-service"}
- **API base URL**: {URL}
- **Region**: {e.g. us-east-1}

### Deploy Workflow

```bash
# {Step-by-step deploy commands}
```

### Operational Safeguards

{Lessons from production incidents. What to check first when things break.}

- {e.g. "If API routes return intermittent 500s while /health returns 200, check logs for InvalidPasswordError first."}
- {e.g. "If crash-looping, check for DeadlockDetectedError and TimeoutError — indicates pool exhaustion."}

## Documentation Update Rules

When behavior changes, update the docs that describe it:

- `README.md`
- `docs/` (architecture, API docs)
- `agent_docs/` (task-specific guides)

## Versioning

{Only include if the project is versioned/released. Remove for internal tools.}

This project follows [semver](https://semver.org/).

- **patch**: Bug fixes, refactors, doc updates. No new features. No config changes.
- **minor**: New features, new config options, new commands. Non-breaking additions.
- **major**: Breaking changes requiring users to update config or integration.

## Skills

{Custom slash commands available in this project.}

- `/{command}` — {what it does}

## Progressive Disclosure

Read only the docs relevant to your current task before coding:

- `agent_docs/{topic_a}.md` — {when to read it}
- `agent_docs/{topic_b}.md` — {when to read it}
- `agent_docs/{topic_c}.md` — {when to read it}

---

## Subdirectory CLAUDE.md Template

{Use this template for module-level CLAUDE.md files inside subdirectories like src/feature_a/CLAUDE.md. These provide local context without duplicating root-level info.}

```markdown
# {Module Name}

Local contract for `{path/to/module}/`.

## Owns

- {responsibility 1}
- {responsibility 2}

## Key Entrypoints

- `{file}:{line}` — {class/function and what it does}

## Integration Points

- {upstream}: `{file}:{line}`
- {downstream}: `{file}:{line}`

## Validate Changes

- Run targeted tests in `tests/unit/{module}/`
- Re-run {related} tests when {condition}

## Deep Dive

See `agent_docs/{relevant_doc}.md`.
```