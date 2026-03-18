# UbundiForge — Ubundi Project Scaffolder

A Python CLI that wraps AI coding tools (Claude Code, Gemini CLI, Codex) to scaffold new projects with Ubundi conventions baked in.

## Stack

- Python 3.12+, Typer, Rich, questionary
- Packaged with hatchling, installed via `uv sync`
- Entry point: `forge` -> `ubundiforge.cli:app`

## Project structure

```
ubundiforge/           Core package
  cli.py               Typer app, single command entry point
  prompts.py           Interactive question flow (questionary)
  router.py            Picks AI backend based on stack selection
  prompt_builder.py    Assembles prompt from answers + conventions
  runner.py            Subprocess execution of AI CLIs
  stacks.py            Stack metadata and cross-recipe defaults
  conventions.py       Loads user conventions from ~/.forge/conventions.md
  safety.py            Secret detection on user-supplied text
  scaffold_options.py  Auth provider and CI action definitions
  setup.py             First-run setup wizard
  config.py            Backend availability checks
  logo.py              ASCII art banner
tests/                 pytest suite mirroring ubundiforge/ modules
docs/                  Specs, roadmap, reference docs
research/              Discovery research and archived notes
scripts/               install.sh and utility scripts
assets/                ASCII art and static assets
```

## How it works

User runs `forge` -> answers interactive questions -> router picks the best AI CLI -> prompt builder assembles answers + conventions into a brief -> runner executes the AI CLI as a subprocess in a new project directory.

## Dev commands

```bash
uv sync                          # Install in dev mode
uv run pytest                    # Run tests
uv run ruff check ubundiforge/   # Lint
uv run ruff format ubundiforge/  # Format
```

## Key flags

- `--use claude|gemini|codex` — override AI routing
- `--dry-run` — print assembled prompt without executing
- `--verbose` — show full subprocess output and timing
- `--export <file>` — save assembled prompt to a file
- `--open` — open project in editor after scaffolding
- `--setup` — re-run first-time setup wizard

## Deeper context

Read the relevant file before starting task-specific work:

- `agent_docs/architecture.md` — Full pipeline flow, module responsibilities, how stacks/conventions/scaffold_options interact
- `agent_docs/adding_a_stack.md` — Checklist for adding a new stack type (which files to touch and in what order)
- `docs/ROADMAP.md` — Current roadmap and feature status
- `docs/ForgeProjectSpec.md` — Original project specification
