# UbundiForge — Ubundi Project Scaffolder

A Python CLI that wraps AI coding tools (Claude Code, Gemini CLI, Codex) to scaffold new projects with Ubundi conventions baked in.

## Stack

- Python 3.12+, Typer, Rich, questionary
- Packaged with hatchling, installed via `uv pip install -e .`
- Entry point: `forge` -> `ubundiforge.cli:app`

## Structure

```
ubundiforge/
  cli.py           — Typer app, single command entry point
  prompts.py       — Interactive question flow (questionary)
  router.py        — Picks AI backend based on stack selection
  prompt_builder.py — Assembles the prompt from answers + conventions
  runner.py        — Subprocess execution of AI CLIs
  conventions.py   — Loads ~/.forge/conventions.md
  config.py        — Backend availability checks
tests/
  test_router.py   — Routing logic tests
```

## How it works

1. User runs `forge`
2. Answers 4-5 questions (name, stack, description, docker, extras)
3. Router picks best AI CLI (gemini for frontend, claude for backend/complex)
4. Prompt builder combines answers + conventions file into a detailed brief
5. Runner executes the chosen CLI as a subprocess in a new project directory

## Dev commands

```bash
uv pip install -e .              # Install in dev mode
uv run pytest                    # Run tests
uv run ruff check ubundiforge/   # Lint
uv run ruff format ubundiforge/  # Format
```

## Key flags

- `--use claude|gemini|codex` — override AI routing
- `--dry-run` — print assembled prompt without executing
