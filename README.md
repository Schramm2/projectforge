# UbundiForge

UbundiForge is a Python CLI that scaffolds new projects with AI coding tools while baking in your Ubundi conventions from the start. It collects a few project details, chooses an AI backend, assembles a structured prompt, and hands off generation to Claude Code, Gemini CLI, or Codex.

## What It Does

- First-run setup wizard that detects installed AI CLIs and editors
- Prompts for project name, stack, description, Docker preference, optional auth/CI choices, and extra instructions
- Supports selectable design templates / brand guides for frontend-capable scaffolds
- Routes to your preferred AI backend (configurable during setup)
- Falls back to the next available backend if the primary isn't installed
- Injects shared conventions from `~/.forge/conventions.md`
- Scans user input for leaked secrets before passing to AI
- Optionally includes a `CLAUDE.md` template in generated projects
- Scaffolds `agent_docs/` starter docs to match the `CLAUDE.md` progressive-disclosure flow
- Creates the target project directory and runs the selected AI CLI inside it

## Supported Stacks

- Next.js + React
- FastAPI
- FastAPI + AI/LLM
- Next.js + FastAPI monorepo
- Python CLI Tool
- TypeScript npm Package
- Python Worker / Scheduled Service

## Backend Routing

By default, UbundiForge uses the backend you chose during setup (or `claude` if unconfigured).

If the primary backend isn't installed, UbundiForge automatically falls back to the next available one (claude -> gemini -> codex).

You can override the routing with `--use`.

## Requirements

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) for environment setup
- At least one installed AI CLI:
  - `claude`
  - `gemini`
  - `codex`

## Installation

```bash
uv sync
source .venv/bin/activate
forge --version
```

On first run, Forge launches a setup wizard that checks for installed AI CLIs and editors, then saves your preferences to `~/.forge/config.json`.

## Usage

### First-run setup

The setup wizard runs automatically on first use. To re-run it:

```bash
forge --setup
```

This detects installed tools, lets you pick a default AI backend and editor, and creates a conventions file if one doesn't exist.

### Interactive mode

```bash
forge
```

### Non-interactive mode

Skip the questions entirely by providing all required flags:

```bash
forge --name pulse --stack fastapi --description "health check API" --docker
forge --name storefront --stack nextjs --description "e-commerce site" --no-docker
forge --name platform --stack both --description "fullstack SaaS app"
forge --name studio --stack nextjs --description "client portal" --auth-provider clerk --ci --ci-template questionnaire --ci-actions lint,typecheck,unit-tests
forge --name ubundi-site --stack nextjs --description "brand site" --design-template ubundi-brand-guide
```

Stack accepts aliases: `next`, `react`, `api`, `ai`, `fullstack`, `monorepo`, `cli`, `worker`, `library`.

### Backend and model selection

Force a specific backend:

```bash
forge --use claude
forge --use gemini
forge --use codex
```

Pass a model to the AI CLI:

```bash
forge --model opus
forge --use gemini --model flash
```

### Prompt inspection and export

Preview the generated prompt without executing:

```bash
forge --dry-run
```

Export the prompt to a file:

```bash
forge --export prompt.md
```

### Design templates

Forge can inject a reusable design template / brand guide into scaffold prompts for `nextjs` and `both` stacks.

- Built-in template: `ubundi-brand-guide`
- CLI flag: `--design-template ubundi-brand-guide`
- Interactive mode: choose `Apply a design template / brand guide?`
- Override the built-in template locally for your own machine or repo:
  - `~/.forge/design-templates/ubundi-brand-guide.md`
  - `.forge/design-templates/ubundi-brand-guide.md`

The intended workflow is to encode the brand guide as prompt-ready tokens and rules in that markdown file, so every new scaffold inherits the same palette, typography, components, and layout language by default.

### Post-scaffold options

Open the project in your editor after scaffolding (uses the editor chosen during setup):

```bash
forge --open
```

### Debugging

Show detailed execution info (command, timing, file sizes):

```bash
forge --verbose
```

Show the installed version:

```bash
forge --version
```

## How It Works

1. On first run, the setup wizard detects AI CLIs and editors, saves preferences.
2. UbundiForge collects answers through an interactive terminal flow (or CLI flags).
3. It loads your shared conventions and optional `CLAUDE.md` template.
4. It scans user-provided text for secrets before proceeding.
5. It builds a single scaffold prompt tailored to the chosen stack.
6. It picks the best AI backend (with automatic fallback if needed).
7. It launches the selected AI CLI in a new project directory with a progress spinner.
8. After scaffolding, it ensures git is initialized and opens the project in your editor.

## Project Structure

```text
forge/
├── ubundiforge/
│   ├── cli.py               # Typer app, single command entry point
│   ├── config.py             # Backend availability checks
│   ├── conventions.py        # Loads conventions from ~/.forge/
│   ├── forge_entry.py        # Bootstrap entry point (bypasses uv .pth bug)
│   ├── prompt_builder.py     # Assembles prompt from answers + conventions
│   ├── prompts.py            # Interactive question flow
│   ├── router.py             # AI backend routing + fallback
│   ├── runner.py             # Subprocess execution of AI CLIs
│   ├── safety.py             # Secret detection
│   ├── scaffold_options.py   # Auth provider and CI action definitions
│   ├── setup.py              # First-run setup wizard
│   ├── stacks.py             # Stack metadata and cross-recipe defaults
│   └── logo.py               # ASCII art banner
├── tests/                    # pytest suite
├── docs/                     # Specs, roadmap, diagrams
├── research/                 # Discovery research and archives
├── scripts/                  # Utility scripts
├── assets/                   # ASCII art and static assets
├── pyproject.toml
└── README.md
```

## Development

Code changes are picked up immediately (editable install). If you change dependencies or delete `.venv`:

```bash
uv sync
```

Run tests:

```bash
uv run pytest
```

Run Ruff:

```bash
uv run ruff check ubundiforge/ tests/
```

## Notes

- UbundiForge expects external AI CLIs to already be installed and available on `PATH`.
- Config and preferences are stored at `~/.forge/config.json`.
- Conventions are loaded from `~/.forge/conventions.md`. If that file does not exist, the setup wizard creates it with defaults.
- The bundled `CLAUDE.md` template is loaded from `ubundiforge/templates/claude-md-template.md`.
