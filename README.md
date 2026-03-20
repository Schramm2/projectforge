# UbundiForge

<p align="center">
  <img src="assets/forge-flow.png" alt="UbundiForge AI Scaffolding Flow" width="100%">
</p>

UbundiForge is a Python CLI that scaffolds new projects with AI coding tools while baking in your Ubundi conventions from the start. It collects a few project details, chooses an AI backend, assembles a structured prompt, and hands off generation to Claude Code, Gemini CLI, or Codex.

## What It Does

- First-run setup wizard that detects installed AI CLIs, backend readiness, editors, git, and Docker
- Post-setup handoff that lets new users create a project now, review setup again, or exit cleanly
- Interactive scaffold flow with a review-and-edit step before generation starts
- Supports selectable design templates / brand guides for frontend-capable scaffolds
- Routes to your preferred AI backend (configurable during setup)
- Falls back to the next available backend if the primary isn't ready
- Multi-phase parallel execution with live progress display
- Injects shared conventions from `~/.forge/conventions.md`
- Scans user input for leaked secrets before passing to AI
- Optionally includes a `CLAUDE.md` template in generated projects
- Writes a `.forge/scaffold.json` manifest into every generated project for provenance
- Logs every scaffold to `~/.forge/scaffold.log` for history
- Runs post-scaffold hooks from `~/.forge/hooks/post-scaffold.sh`
- Shell tab completion for all flags and options

## Supported Stacks

| Stack | Identifier | Aliases |
|-------|-----------|---------|
| Next.js + React | `nextjs` | `next`, `react` |
| FastAPI | `fastapi` | `api` |
| FastAPI + AI/LLM | `fastapi-ai` | `ai`, `llm` |
| Next.js + FastAPI Monorepo | `both` | `fullstack`, `monorepo` |
| Python CLI Tool | `python-cli` | `cli`, `typer` |
| TypeScript npm Package | `ts-package` | `npm-package`, `library` |
| Python Worker | `python-worker` | `worker`, `service` |

See [docs/stacks.md](docs/stacks.md) for detailed structure, libraries, and dev commands for each stack.

## Requirements

- Python 3.12+
- At least one installed AI CLI:
  - `claude` ([Claude Code](https://docs.anthropic.com/en/docs/claude-code))
  - `gemini` ([Gemini CLI](https://github.com/google-gemini/gemini-cli))
  - `codex` ([Codex](https://github.com/openai/codex))

## Installation

### Homebrew (macOS)

```bash
brew tap matthewubundi/tap
brew install ubundiforge
forge --version
```

### pipx

```bash
pipx install ubundiforge
forge --version
```

### From source

```bash
git clone https://github.com/matthewubundi/UbundiForge.git
cd UbundiForge
uv sync --dev
./forge --version
```

On first run, Forge launches a setup wizard that checks backend readiness, editor preference, git setup, Docker availability, and project-directory defaults, then saves your preferences to `~/.forge/config.json`.

After setup, Forge does not immediately force you into a scaffold. It shows a short handoff screen so you can:

- create a project now
- review setup again
- exit and come back later

### Testing a pristine first-run wizard

If you want to test Forge as if you were a brand new user on a machine that
already has Forge or AI CLIs installed, prefer temporarily moving `~/.forge`
out of the way instead of changing `HOME`.

```bash
mv ~/.forge ~/.forge.backup-$(date +%Y%m%d-%H%M%S)
forge
```

After testing, restore your original Forge config:

```bash
rm -rf ~/.forge
mv ~/.forge.backup-YYYYMMDD-HHMMSS ~/.forge
```

Why this is recommended:

- It forces Forge to show the true first-run setup wizard.
- It preserves your normal Claude, Gemini, and Codex login state.
- It avoids false failures where the AI CLI is installed but appears logged out.

Using `HOME="$(mktemp -d)" forge` can also produce a clean Forge config, but it
may hide authentication files used by `claude`, `gemini`, or `codex`, which can
cause scaffolding to fail even though the CLIs are installed.

## Quick Start

### Interactive mode

```bash
forge
```

Forge will walk you through the scaffold interactively, then show a review screen before anything is generated so you can edit basics, design/media, integrations, or demo mode without restarting the whole flow.

<p align="center">
  <img src="assets/forge-interactive.png" alt="Forge interactive questionnaire and review screen" width="100%">
</p>

Once you confirm, Forge routes each phase to the best available backend and runs them with a live progress display, followed by post-scaffold verification.

<p align="center">
  <img src="assets/forge-execution.png" alt="Forge multi-phase execution and verification" width="100%">
</p>

### Non-interactive mode

```bash
forge --name pulse --stack fastapi --description "health check API" --docker
forge --name storefront --stack nextjs --description "e-commerce site" --no-docker
forge --name platform --stack both --description "fullstack SaaS app"
```

### Dry run

Preview the assembled prompt without executing:

```bash
forge --dry-run
```

### Backend override

```bash
forge --use claude
forge --use gemini --model flash
```

See [docs/getting-started.md](docs/getting-started.md) for a full walkthrough.

## Configuration

All user config lives under `~/.forge/`:

| File | Purpose |
|------|---------|
| `config.json` | Backend, editor, and project directory preferences |
| `conventions.md` | Team coding standards injected into every scaffold prompt |
| `hooks/post-scaffold.sh` | Custom script run after every scaffold |
| `scaffold.log` | Append-only JSON-lines scaffold history |

Re-run setup at any time:

```bash
forge --setup
```

See [docs/configuration.md](docs/configuration.md) for the full reference.

## CLI Flags

| Flag | Description |
|------|-------------|
| `--name`, `-n` | Project name |
| `--stack`, `-s` | Stack identifier or alias |
| `--description`, `-d` | Project description |
| `--use` | Override AI backend (`claude`, `gemini`, `codex`) |
| `--model`, `-m` | Model to pass to the AI CLI |
| `--docker` / `--no-docker` | Include Docker setup |
| `--auth-provider` | Auth provider for frontend stacks (`clerk`, `supabase-auth`, `authjs`, `better-auth`) |
| `--ci` / `--no-ci` | Include GitHub Actions CI workflow |
| `--design-template` | Brand/design guide for frontend stacks |
| `--media` | Media collection to import into the project |
| `--demo` / `--no-demo` | Demo mode (projects run without real API keys) |
| `--dry-run` | Print assembled prompt without executing |
| `--export` | Export prompt to a file |
| `--verbose` | Show full subprocess output and timing |
| `--open` / `--no-open` | Open project in editor after scaffolding |
| `--verify` / `--no-verify` | Run post-scaffold verification checks |
| `--setup` | Re-run the setup wizard |
| `--version`, `-v` | Show version |

## Documentation

- [Getting Started](docs/getting-started.md) -- Installation, first run, first scaffold
- [Admin Playbook](docs/admin-playbook.md) -- Maintaining conventions, adding stacks, and shipping Homebrew releases
- [Configuration](docs/configuration.md) -- Config files, conventions, hooks, media assets
- [Stacks](docs/stacks.md) -- Detailed reference for every supported stack
- [Troubleshooting](docs/troubleshooting.md) -- Common issues and fixes
- [Homebrew Release Notes](docs/homebrew.md) -- Formula generation and release flow
- [Changelog](CHANGELOG.md) -- Version history

## How It Works

1. On first run, the setup wizard detects installed backends, checks whether they are ready to use, and saves your defaults.
2. Forge gives new users a clean handoff: create a project now, review setup again, or exit.
3. UbundiForge collects answers through an interactive terminal flow or CLI flags.
4. In interactive mode, Forge shows a review screen so you can edit selections before generation starts.
5. It loads your shared conventions and optional `CLAUDE.md` template.
6. It scans user-provided text for secrets before proceeding.
7. It picks the best ready AI backend plan for each scaffold phase.
8. It launches the selected AI CLI in a new project directory with a live progress display.
9. After scaffolding, it writes a `.forge/scaffold.json` manifest into the project.
10. It ensures git is initialized, runs verification, runs your post-scaffold hook, and opens the project in your editor if configured.

## Project Structure

```text
UbundiForge/
├── src/ubundiforge/        Core package
│   ├── cli.py              Typer app, single command entry point
│   ├── config.py           Backend availability checks
│   ├── conventions.py      Loads conventions from ~/.forge/
│   ├── homebrew.py         Formula generation helpers
│   ├── prompt_builder.py   Assembles prompt from answers + conventions
│   ├── prompts.py          Interactive question flow
│   ├── router.py           AI backend routing + fallback
│   ├── runner.py           Subprocess execution of AI CLIs
│   ├── scaffold_log.py     Scaffold history and per-project manifest
│   ├── safety.py           Secret detection
│   ├── scaffold_options.py Auth provider and CI action definitions
│   ├── setup.py            First-run setup wizard
│   ├── stacks.py           Stack metadata and cross-recipe defaults
│   ├── assets/             Bundled ASCII art
│   └── templates/          CLAUDE.md and design templates
├── Formula/                Homebrew formula
├── tests/                  pytest suite
├── docs/                   User guides and reference docs
├── scripts/                Utility scripts
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
├── forge                   Repo-local developer launcher
└── README.md
```

## Development

```bash
uv sync --dev                            # Install in dev mode
uv run pytest                            # Run tests
uv run ruff check src/ubundiforge tests  # Lint
uv run ruff format src/ubundiforge       # Format
```

## License

MIT -- see [LICENSE](LICENSE).
