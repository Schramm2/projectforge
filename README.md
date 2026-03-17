# Forge

Forge is a Python CLI that scaffolds new projects with AI coding tools while baking in your Ubundi conventions from the start. It collects a few project details, chooses an AI backend, assembles a structured prompt, and hands off generation to Claude Code, Gemini CLI, or Codex.

## What It Does

- Prompts for project name, stack, description, Docker preference, and extra instructions
- Routes to a preferred AI backend based on the selected stack
- Falls back to the next available backend if the primary isn't installed
- Injects shared conventions from `~/.forge/conventions.md`
- Optionally includes a `CLAUDE.md` template in generated projects
- Creates the target project directory and runs the selected AI CLI inside it

## Supported Stacks

- Next.js + React
- FastAPI
- Next.js + FastAPI monorepo

## Backend Routing

By default, Forge uses:

- `gemini` for Next.js projects
- `claude` for FastAPI projects
- `claude` for combined frontend/backend projects

If the primary backend isn't installed, Forge automatically falls back to the next available one (claude → gemini → codex).

You can override the routing with `--use`.

## Requirements

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) recommended for environment setup
- At least one installed AI CLI:
  - `claude`
  - `gemini`
  - `codex`

## Installation

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Usage

### Interactive mode

Run the interactive scaffold flow:

```bash
forge
```

### Non-interactive mode

Skip the questions entirely by providing all required flags:

```bash
forge --name pulse --stack fastapi --description "health check API" --docker
forge --name storefront --stack nextjs --description "e-commerce site" --no-docker
forge --name platform --stack both --description "fullstack SaaS app"
```

Stack accepts aliases: `next`, `react`, `python`, `api`, `fullstack`, `monorepo`.

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

### Post-scaffold options

Open the project in your editor (Cursor or VS Code) after scaffolding:

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

1. Forge collects answers through an interactive terminal flow (or CLI flags).
2. It loads your shared conventions and optional `CLAUDE.md` template.
3. It builds a single scaffold prompt tailored to the chosen stack.
4. It picks the best AI backend (with automatic fallback if needed).
5. It launches the selected AI CLI in a new project directory with a progress spinner.

## Project Structure

```text
forge/
├── forge/
│   ├── cli.py
│   ├── config.py
│   ├── conventions.py
│   ├── prompt_builder.py
│   ├── prompts.py
│   ├── router.py
│   ├── runner.py
│   └── templates/
├── tests/
├── docs/
├── pyproject.toml
└── README.md
```

## Development

Run tests:

```bash
uv run pytest
```

Run Ruff:

```bash
uv run ruff check forge/ tests/
```

## Notes

- Forge expects external AI CLIs to already be installed and available on `PATH`.
- Conventions are loaded from `~/.forge/conventions.md`. If that file does not exist, Forge creates it with defaults. Forge warns if the conventions file is empty or very short.
- The bundled `CLAUDE.md` template is loaded from `forge/templates/claude-md-template.md`.
