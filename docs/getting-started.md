# Getting Started

## Prerequisites

- **Python 3.12+** installed and on your PATH.
- **At least one AI CLI tool** installed:
  - [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (`claude`)
  - [Gemini CLI](https://github.com/google-gemini/gemini-cli) (`gemini`)
  - [Codex](https://github.com/openai/codex) (`codex`)

Forge will detect which tools are available and route to the best one automatically.

## Installation

### Homebrew (recommended for macOS)

```bash
brew tap matthewubundi/tap
brew install ubundiforge
```

### pipx (isolated global install)

```bash
pipx install ubundiforge
```

### From source

```bash
git clone https://github.com/matthewubundi/UbundiForge.git
cd forge
uv sync --dev
./forge
```

## First run

Running `forge` for the first time launches the setup wizard. It checks for:

- **AI CLIs** -- which of claude, gemini, and codex are installed and on PATH.
- **Editor** -- your preferred editor for opening projects after scaffolding.
- **Git** -- whether git is installed (required for initializing new projects).
- **Docker** -- whether Docker is available (optional, used for stacks that default to containerized dev).

Results are saved to `~/.forge/config.json`. You can re-run the wizard at any time with:

```bash
forge --setup
```

## Your first scaffold

1. Run `forge` with no arguments.
2. Enter a project name (e.g., `my-app`).
3. Choose a stack from the list (e.g., Next.js + React).
4. Add a short description of what the project does.
5. Accept the remaining defaults or customize auth, CI, Docker, and design template options.
6. Watch it build. You will see live progress as Forge routes your brief to the AI backend, which generates the project in phases.

When complete, Forge will:
- Initialize a git repository in the new project directory.
- Write a `.forge/scaffold.json` manifest for provenance.
- Open the project in your editor (if configured).

## Non-interactive mode

For CI pipelines or scripting, pass all options as flags:

```bash
forge --name my-api --stack fastapi --description "REST API for inventory management" --no-docker
```

Use `--dry-run` to preview the assembled prompt without executing anything:

```bash
forge --name my-api --stack fastapi --description "REST API" --dry-run
```

## What's next

- [configuration.md](configuration.md) -- Customize config files, conventions, hooks, and media assets.
- [stacks.md](stacks.md) -- Detailed reference for every supported stack.
- [troubleshooting.md](troubleshooting.md) -- Common issues and how to fix them.
