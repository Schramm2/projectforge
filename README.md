<p align="center">
  <img src="assets/hero-banner.png" alt="UbundiForge" width="100%">
</p>

<h1 align="center">UbundiForge</h1>

<p align="center">
  <strong>AI-powered project scaffolding with your team's conventions baked in.</strong>
</p>

<p align="center">
  <a href="#installation">Installation</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;<a href="#quick-start">Quick Start</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;<a href="#supported-stacks">Stacks</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;<a href="docs/getting-started.md">Docs</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;<a href="CHANGELOG.md">Changelog</a>
</p>

---

UbundiForge is a CLI that collects a few project details, picks the best AI backend, assembles a structured prompt with your conventions, and hands off generation to **Claude Code**, **Gemini CLI**, or **Codex**. You get a production-ready project directory in minutes instead of hours.

<p align="center">
  <img src="assets/product-showcase.png" alt="UbundiForge product showcase" width="100%">
</p>

## Features

- **First-run setup wizard** -- detects installed AI CLIs, backend readiness, editors, git, and Docker
- **Multi-backend routing** -- picks your preferred AI backend per phase with automatic fallback
- **Interactive scaffold flow** -- review-and-edit screen before generation starts
- **Multi-phase parallel execution** -- live progress display across scaffold phases
- **Convention injection** -- loads shared standards from `~/.forge/conventions.md`
- **Secret scanning** -- checks user input for leaked credentials before passing to AI
- **Post-scaffold automation** -- manifest, git init, verification, hooks, editor launch
- **Design templates** -- selectable brand guides for frontend-capable scaffolds
- **Shell completion** -- tab completion for all flags and options

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

See [docs/stacks.md](docs/stacks.md) for detailed structure, libraries, and dev commands.

## Requirements

- Python 3.12+
- At least one AI CLI installed:
  - [`claude`](https://docs.anthropic.com/en/docs/claude-code) (Claude Code)
  - [`gemini`](https://github.com/google-gemini/gemini-cli) (Gemini CLI)
  - [`codex`](https://github.com/openai/codex) (Codex)

## Installation

### Homebrew (macOS)

```bash
brew tap matthewubundi/tap
brew install ubundiforge
```

### pipx

```bash
pipx install ubundiforge
```

### From source

```bash
git clone https://github.com/matthewubundi/UbundiForge.git
cd UbundiForge
uv sync --dev
```

Verify the installation:

```bash
forge --version
```

## Quick Start

### Interactive mode

```bash
forge
```

Forge walks you through the scaffold interactively, then shows a review screen before anything is generated.

<p align="center">
  <img src="assets/forge-interactive.png" alt="Forge interactive questionnaire and review screen" width="100%">
</p>

Once confirmed, Forge routes each phase to the best available backend and runs them with a live progress display.

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

## First-Run Experience

On first run, Forge launches a setup wizard that checks backend readiness, editor preference, git setup, Docker availability, and project-directory defaults, then saves your preferences to `~/.forge/config.json`.

After setup, Forge gives you a clean handoff -- create a project now, review setup again, or exit and come back later.

<details>
<summary>Testing a pristine first-run wizard</summary>

Temporarily move `~/.forge` out of the way instead of changing `HOME`:

```bash
mv ~/.forge ~/.forge.backup-$(date +%Y%m%d-%H%M%S)
forge
```

After testing, restore your original config:

```bash
rm -rf ~/.forge
mv ~/.forge.backup-YYYYMMDD-HHMMSS ~/.forge
```

Using `HOME="$(mktemp -d)"` can hide authentication files used by AI CLIs, causing scaffolding to fail even when the CLIs are installed.

</details>

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

## CLI Reference

| Flag | Description |
|------|-------------|
| `--name`, `-n` | Project name |
| `--stack`, `-s` | Stack identifier or alias |
| `--description`, `-d` | Project description |
| `--use` | Override AI backend (`claude`, `gemini`, `codex`) |
| `--model`, `-m` | Model to pass to the AI CLI |
| `--docker` / `--no-docker` | Include Docker setup |
| `--auth-provider` | Auth provider (`clerk`, `supabase-auth`, `authjs`, `better-auth`) |
| `--ci` / `--no-ci` | Include GitHub Actions CI workflow |
| `--design-template` | Brand/design guide for frontend stacks |
| `--media` | Media collection to import into the project |
| `--demo` / `--no-demo` | Demo mode (runs without real API keys) |
| `--dry-run` | Print assembled prompt without executing |
| `--export` | Export prompt to a file |
| `--verbose` | Show full subprocess output and timing |
| `--open` / `--no-open` | Open project in editor after scaffolding |
| `--verify` / `--no-verify` | Run post-scaffold verification checks |
| `--setup` | Re-run the setup wizard |
| `--version`, `-v` | Show version |

## How It Works

<p align="center">
  <img src="assets/forge-flow.png" alt="UbundiForge scaffolding flow" width="100%">
</p>

1. **Setup** -- First-run wizard detects backends, checks readiness, saves defaults.
2. **Collect** -- Interactive flow or CLI flags gather project details.
3. **Review** -- Edit selections before generation starts.
4. **Assemble** -- Loads conventions, templates, and scans for secrets.
5. **Route** -- Picks the best ready backend for each scaffold phase.
6. **Execute** -- Launches AI CLIs with live progress display.
7. **Finalize** -- Writes manifest, inits git, runs verification and hooks, opens editor.

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Installation, first run, first scaffold |
| [Configuration](docs/configuration.md) | Config files, conventions, hooks, media assets |
| [Stacks](docs/stacks.md) | Detailed reference for every supported stack |
| [Admin Playbook](docs/admin-playbook.md) | Maintaining conventions, adding stacks, shipping releases |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and fixes |
| [Homebrew Release](docs/homebrew.md) | Formula generation and release flow |

## Development

```bash
uv sync --dev                            # Install in dev mode
uv run pytest                            # Run tests
uv run ruff check src/ubundiforge tests  # Lint
uv run ruff format src/ubundiforge       # Format
```

## License

MIT -- see [LICENSE](LICENSE).
