# UbundiForge

UbundiForge is a Python CLI that scaffolds new projects with AI coding tools while baking in your Ubundi conventions from the start. It collects a few project details, chooses an AI backend, assembles a structured prompt, and hands off generation to Claude Code, Gemini CLI, or Codex.

## What It Does

- Prompts for project name, stack, description, Docker preference, optional auth/CI choices, and extra instructions
- Routes to a preferred AI backend based on the selected stack
- Falls back to the next available backend if the primary isn't installed
- Injects shared conventions from `~/.forge/conventions.md`
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

By default, UbundiForge routes every stack to `claude` for now.

If the primary backend isn't installed, UbundiForge automatically falls back to the next available one (claude -> gemini -> codex).

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
./forge --version
```

The first run bootstraps a local `.venv`, installs the runtime dependencies, and creates a stable
`forge` launcher that points at the repo source. This avoids the editable-install issue that can
break the `forge` entrypoint on some Python/uv setups.

If you prefer to install manually:

```bash
./scripts/install.sh
source .venv/bin/activate
forge --version
```

## Usage

The examples below use `./forge`, which works from a repo checkout without activating `.venv`.
If you already activated the environment, you can replace `./forge` with `forge`.

### Interactive mode

Run the interactive scaffold flow:

```bash
./forge
```

Or, after activating the virtual environment:

```bash
forge
```

### Non-interactive mode

Skip the questions entirely by providing all required flags:

```bash
./forge --name pulse --stack fastapi --description "health check API" --docker
./forge --name storefront --stack nextjs --description "e-commerce site" --no-docker
./forge --name platform --stack both --description "fullstack SaaS app"
./forge --name studio --stack nextjs --description "client portal" --auth-provider clerk --ci --ci-template questionnaire --ci-actions lint,typecheck,unit-tests
```

Stack accepts aliases: `next`, `react`, `python`, `api`, `fullstack`, `monorepo`.

### Backend and model selection

Force a specific backend:

```bash
./forge --use claude
./forge --use gemini
./forge --use codex
```

Pass a model to the AI CLI:

```bash
./forge --model opus
./forge --use gemini --model flash
```

### Prompt inspection and export

Preview the generated prompt without executing:

```bash
./forge --dry-run
```

Export the prompt to a file:

```bash
./forge --export prompt.md
```

### Post-scaffold options

Open the project in your editor (Cursor or VS Code) after scaffolding:

```bash
./forge --open
```

### Debugging

Show detailed execution info (command, timing, file sizes):

```bash
./forge --verbose
```

Show the installed version:

```bash
./forge --version
```

## How It Works

1. UbundiForge collects answers through an interactive terminal flow (or CLI flags).
2. It loads your shared conventions and optional `CLAUDE.md` template.
3. It builds a single scaffold prompt tailored to the chosen stack.
4. It picks the best AI backend (with automatic fallback if needed).
5. It launches the selected AI CLI in a new project directory with a progress spinner.

## Project Structure

```text
forge/
├── ubundiforge/
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

Package code changes are picked up immediately because the launcher runs the source tree directly.
If you change dependencies or delete `.venv`, rerun the installer:

```bash
./scripts/install.sh
```

The repo-local launcher also does this automatically when needed, so `./forge` is the safest
command to use from a checkout.

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
- Conventions are loaded from `~/.forge/conventions.md`. If that file does not exist, UbundiForge creates it with defaults. UbundiForge warns if the conventions file is empty or very short.
- The bundled `CLAUDE.md` template is loaded from `ubundiforge/templates/claude-md-template.md`.
