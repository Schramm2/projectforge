# Forge Command Recipes

Use these as starting points. Prefer the repo-local `./forge` when inside the Forge repository; otherwise use `forge`.

## Core Pattern

```bash
forge --name <project-name> --stack <stack-id> --description "<brief>" [options...]
```

Required non-interactive fields:

- `--name`
- `--stack`
- `--description`

Useful shared options:

- `--docker` or `--no-docker`
- `--use claude|gemini|codex`
- `--model <model-id>`
- `--extra "<instruction>"`
- `--dry-run`
- `--export <path>`
- `--verify` or `--no-verify`
- `--open` or `--no-open`
- `--demo` or `--no-demo`

## Prompt Preview First

```bash
forge \
  --name pulse \
  --stack fastapi \
  --description "Health-check API for service monitoring" \
  --docker \
  --no-open \
  --dry-run
```

Use this when you want prompt inspection without running a backend.

## Next.js Product Scaffold

```bash
forge \
  --name studio \
  --stack nextjs \
  --description "Client portal with a polished marketing surface and authenticated dashboard" \
  --no-docker \
  --auth-provider clerk \
  --ci \
  --ci-template questionnaire \
  --ci-actions lint,typecheck,unit-tests \
  --design-template ubundi-brand-guide \
  --extra "Use a premium, editorial visual direction and include realistic starter content." \
  --no-open
```

## FastAPI Service Scaffold

```bash
forge \
  --name atlas-api \
  --stack fastapi \
  --description "Internal service for customer and subscription operations" \
  --docker \
  --ci \
  --ci-template questionnaire \
  --ci-actions lint,format-check,typecheck,unit-tests,integration-tests \
  --no-open
```

## FastAPI AI Service Scaffold

```bash
forge \
  --name recall \
  --stack fastapi-ai \
  --description "Retrieval API with embeddings, pgvector, and OpenAI-backed answer generation" \
  --docker \
  --extra "Favor a retrieval pipeline that is easy to extend and test." \
  --no-open
```

## Fullstack Monorepo Scaffold

```bash
forge \
  --name orbit \
  --stack both \
  --description "Operations platform with Next.js frontend and FastAPI backend" \
  --docker \
  --auth-provider better-auth \
  --ci \
  --ci-template questionnaire \
  --ci-actions lint,format-check,typecheck,build,unit-tests,integration-tests,docker-build \
  --design-template ubundi-brand-guide \
  --no-open
```

## Python CLI Tool

```bash
forge \
  --name forge-audit \
  --stack python-cli \
  --description "CLI for checking scaffold quality across generated repos" \
  --no-docker \
  --ci \
  --ci-template questionnaire \
  --ci-actions lint,format-check,typecheck,unit-tests \
  --no-open
```

## TypeScript Package

```bash
forge \
  --name ui-contracts \
  --stack ts-package \
  --description "Typed SDK for internal frontend-backend contracts" \
  --no-docker \
  --ci \
  --ci-template questionnaire \
  --ci-actions lint,typecheck,build,unit-tests \
  --no-open
```

## Python Worker

```bash
forge \
  --name digest-worker \
  --stack python-worker \
  --description "Scheduled worker that compiles customer digests and ships notifications" \
  --docker \
  --ci \
  --ci-template questionnaire \
  --ci-actions lint,format-check,typecheck,unit-tests,docker-build \
  --no-open
```

## Single-Backend Override

```bash
forge \
  --name reviewbot \
  --stack python-cli \
  --description "Automation tool for repository review workflows" \
  --use codex \
  --model gpt-5.4 \
  --no-docker \
  --no-open
```

Use this when the user wants a specific backend or when you need deterministic routing.

## Export a Multi-Phase Prompt

```bash
forge \
  --name studio \
  --stack nextjs \
  --description "Branded client portal" \
  --no-docker \
  --export /tmp/studio-prompt.md \
  --no-open
```

This is useful for prompt review, audits, and backend comparison before a real run.
