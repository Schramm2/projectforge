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

### From source

```bash
git clone https://github.com/matthewubundi/UbundiForge.git
cd UbundiForge
uv sync --dev
./forge
```

## First run

Running `forge` for the first time launches the setup wizard. It checks for:

- **AI backends** -- which of claude, gemini, and codex are installed, and whether Forge can confirm they are ready to use.
- **Editor** -- your preferred editor for opening projects after scaffolding.
- **Git** -- whether git is installed (required for initializing new projects).
- **Git identity** -- whether `user.name` and `user.email` are configured for initial commits.
- **Docker** -- whether Docker is available (optional, used for stacks that default to containerized dev).

Results are saved to `~/.forge/config.json`. You can re-run the wizard at any time with:

```bash
forge --setup
```

After setup completes on first run, Forge gives you a short handoff instead of immediately dropping you into a scaffold. You can:

- create a project now
- review setup again
- exit and come back later

## Your first scaffold

1. Run `forge` with no arguments.
2. Enter a project name (e.g., `my-app`).
3. Choose a stack from the list (e.g., Next.js + React).
4. Add a short description of what the project does.
5. Accept the remaining defaults or customize auth, CI, Docker, design template, and media options.
6. Review your choices. Forge shows a summary screen where you can edit basics, design/media, integrations, or demo mode before generation starts.
7. Watch it build. During execution you will see:
   - A **phase timeline** showing which phases are completed, active, and pending
   - An **activity feed** with checkmarks scrolling through what the AI is doing
   - A **file tree** rendered between phases showing what was created
8. When all phases finish, Forge shows a **post-scaffold dashboard** with health check results, file/line counts, and next steps.

When complete, Forge will:
- Initialize a git repository in the new project directory.
- Write a `.forge/scaffold.json` manifest and conventions snapshot for provenance.
- Generate a `.forge/card.svg` project card and inject a badge into the README.
- Run verification checks if enabled (lint, typecheck, tests, build, health).
- Play a completion sound if enabled (`"sound": true` in `~/.forge/config.json`).
- Open the project in your editor (if configured).

If the target directory already exists, Forge will offer safer choices instead of only asking to overwrite it. You can rename the project, overwrite the directory, or cancel.

After 3+ scaffolds, Forge learns your preferences and offers to pre-fill dominant choices ("Your usual setup: ...") with a single confirm prompt.

## Non-interactive mode

For CI pipelines or scripting, pass all options as flags:

```bash
forge --name my-api --stack fastapi --description "REST API for inventory management" --no-docker
```

Use `--dry-run` to preview the assembled prompt without executing anything:

```bash
forge --name my-api --stack fastapi --description "REST API" --dry-run
```

Use `--use` if you want to force a single backend for the entire scaffold:

```bash
forge --use codex --name my-api --stack fastapi --description "REST API" --dry-run
```

## Beyond scaffolding

Once you have projects, Forge keeps working:

```bash
forge stats              # See your scaffold history and backend performance
forge check              # Audit any project against Ubundi conventions
forge check --fix        # Auto-generate missing CLAUDE.md, .env.example, agent_docs/
forge evolve auth        # Add authentication to an existing Forge project
forge evolve stripe      # Add Stripe billing
forge replay --diff      # Reproduce a past scaffold and compare against current state
```

Run these from inside a Forge-scaffolded project (one that has `.forge/scaffold.json`).

## What's next

- [configuration.md](configuration.md) -- Customize config files, conventions, hooks, and media assets.
- [stacks.md](stacks.md) -- Detailed reference for every supported stack.
- [troubleshooting.md](troubleshooting.md) -- Common issues and how to fix them.
