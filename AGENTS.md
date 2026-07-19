# ProjectForge — Project Scaffolder

A Python CLI that wraps AI coding tools (Claude Code, Google Antigravity CLI, Codex CLI) to scaffold new projects with organization conventions baked in.

## Stack

- Python 3.12+, Typer, Rich, questionary
- Packaged with hatchling, installed via `uv sync`
- Entry point: `forge` -> `projectforge.__main__:main`

## Project structure

```
src/projectforge/       Core package (src layout)
  cli.py               Typer command surface and top-level lifecycle composition
  config.py            Backend install + readiness checks (BackendStatus)
  prompts.py           Interactive questionnaire with review/edit screen
  router.py            Phase routing and claude -> antigravity -> codex fallback
  prompt_builder.py    Assembles prompt from answers + conventions
  scaffold_request.py  Typed non-interactive input normalization and validation
  scaffold_prompts.py  Per-phase prompt plan, previews, exports, and progress records
  scaffold_execution.py Serial, parallel, and orchestrated phase lifecycle
  scaffold_completion.py Manifest, verification, hook, dashboard, and editor lifecycle
  runner.py            Provider subprocess and parallel process execution
  orchestrator.py      Multi-agent task planning, task graphs, and reconciliation
  stacks.py            Stack metadata and cross-recipe defaults
  setup.py             First-run wizard (backends, editor, git, Docker)
  convention_*.py      Bundled convention registry, compiler, admin, and history
  conventions.py       Composes bundled, profile, user, and project conventions
  verify.py            Metadata-aware project verification
  progress.py          Durable phase state and resume contracts
  homebrew.py          Formula generation from uv.lock
  ui.py                Shared Rich primitives and theme palette
tests/                 pytest suite mirroring src/projectforge/ modules
conventions/           Bundled convention layers and manifests
docs/guides/           Maintained user documentation
docs/maintainers/      Maintainer runbooks, roadmap, and dated evidence
Formula/               Generated Homebrew formula
scripts/               Safety, docs, skill, artifact, and formula checks
skills/forge-scaffold/ Shipped agent operator skill
```

## How it works

User runs `forge` -> setup wizard on first live run -> request boundary resolves interactive or CLI
answers -> router picks backends per phase -> prompt plan assembles phase briefs -> phase executor
runs provider CLI subprocesses -> completion lifecycle records manifests and progress, initializes
git, verifies the result, runs the configured hook, records quality/preferences, and renders the
final project card/dashboard.

## Dev commands

```bash
uv sync --dev                                # Install in dev mode
uv run pytest                                # Run tests
uv run ruff check src/projectforge tests      # Lint
uv run ruff format src/projectforge tests     # Format
uv run python scripts/check_docs.py          # Validate maintained documentation links
uv run python scripts/validate_forge_skill.py # Validate the shipped agent skill
uv build && uv run python scripts/inspect_artifacts.py
./forge --dry-run --name smoke --stack fastapi --description "test" --no-docker --no-open --no-verify
```

## Deeper context

Read the relevant file before starting task-specific work:

- `docs/diagrams/forge-runtime-pipeline.md` — Main scaffold pipeline and outputs
- `docs/diagrams/forge-routing-and-execution.md` — Routing, fallback, and execution windows
- `docs/maintainers/adding-a-stack.md` — Checklist for adding a stack
- `docs/maintainers/admin-playbook.md` — Conventions administration and release flow
- `docs/maintainers/homebrew-release.md` — Homebrew publishing and recovery
- `docs/guides/stacks.md` — Supported structures, libraries, and commands
- `docs/guides/configuration.md` — Config and evidence files under `~/.forge/` and `.forge/`
- `docs/guides/troubleshooting.md` — Common issues and recovery
- `docs/maintainers/roadmap.md` — Current roadmap and feature status
