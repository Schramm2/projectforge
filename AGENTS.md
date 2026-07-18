# ProjectForge — Project Scaffolder

A Python CLI that wraps AI coding tools (Claude Code, Google Antigravity CLI, Codex CLI) to scaffold new projects with organization conventions baked in.

## Stack

- Python 3.12+, Typer, Rich, questionary
- Packaged with hatchling, installed via `uv sync`
- Entry point: `forge` -> `ubundiforge.__main__:main`

## Project structure

```
src/ubundiforge/       Core package (src layout)
  cli.py               Orchestration: flags, validation, phase execution
  config.py            Backend install + readiness checks (BackendStatus)
  prompts.py           Interactive questionnaire with review/edit screen
  router.py            Multi-phase backend routing with fallback
  prompt_builder.py    Assembles prompt from answers + conventions
  runner.py            Subprocess execution (serial + parallel phases)
  stacks.py            Stack metadata and cross-recipe defaults
  setup.py             First-run wizard (backends, editor, git, Docker)
  conventions.py       Loads ~/.forge/conventions.md
  homebrew.py          Formula generation from uv.lock
  ui.py                Shared Rich primitives and theme palette
tests/                 pytest suite mirroring src/ubundiforge/ modules
docs/                  User guides, stacks reference, troubleshooting
Formula/               Generated Homebrew formula
scripts/               Formula generator and utilities
```

## How it works

User runs `forge` -> setup wizard on first run -> answers interactive questions -> router picks backends per phase -> prompt builder assembles brief -> runner executes AI CLI(s) as subprocesses -> post-scaffold: manifest, git init, verification, hooks.

## Dev commands

```bash
uv sync --dev                                # Install in dev mode
uv run pytest                                # Run tests
uv run ruff check src/ubundiforge tests      # Lint
uv run ruff format src/ubundiforge           # Format
./forge --dry-run --name smoke --stack fastapi --description "test" --no-docker  # Smoke test
```

## Deeper context

Read the relevant file before starting task-specific work:

- `agent_docs/architecture.md` — Full pipeline flow, module responsibilities, key data structures
- `agent_docs/adding_a_stack.md` — Checklist for adding a new stack (which files in what order)
- `agent_docs/releasing.md` — Manual release checklist (automated by `/release` command)
- `docs/stacks.md` — Supported stacks with structures, libraries, dev commands
- `docs/configuration.md` — All config files under ~/.forge/
- `docs/troubleshooting.md` — Common issues and fixes
- `docs/maintainers/roadmap.md` — Current roadmap and feature status
