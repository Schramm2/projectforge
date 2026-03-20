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
- Writes a `.forge/scaffold.json` manifest into every generated project for provenance
- Logs every scaffold to `~/.forge/scaffold.log` for history
- Runs post-scaffold hooks from `~/.forge/hooks/post-scaffold.sh`
- Shell tab completion for all flags and options

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
- At least one installed AI CLI:
  - `claude`
  - `gemini`
  - `codex`

## Installation

### Homebrew

Homebrew already ships other formulae with `forge` in the name, so the Homebrew package for this project should be published as `ubundiforge` while still installing the `forge` command.

Once the tap is live:

```bash
brew tap matthewubundi/tap
brew install ubundiforge
forge --version
```

The formula in this repo is generated from `uv.lock`:

```bash
python3 scripts/generate_homebrew_formula.py
```

### pipx

For isolated global installs outside Homebrew:

```bash
pipx install ubundiforge
forge --version
```

To test the packaged CLI from a local checkout before publishing:

```bash
pipx install .
forge --version
```

### From source

For contributors working in the repo:

```bash
uv sync --dev
./forge --version
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

### Shell completions

Enable tab completion for all `forge` flags:

```bash
# Generate and install the completion script (zsh)
_FORGE_COMPLETE=source_zsh forge > ~/.zfunc/_forge

# Rebuild the completion cache
rm -f ~/.zcompdump*
exec zsh
```

After setup, `forge --<tab>` shows all available flags with descriptions.

### Scaffold manifest

Every scaffolded project gets a `.forge/scaffold.json` file recording how it was built:

```json
{
  "forge_version": "0.1.0",
  "name": "my-app",
  "stack": "nextjs",
  "backends": ["claude"],
  "routing": [{"phase": "architecture", "backend": "claude"}, ...],
  "design_template": "ubundi-brand-guide",
  "conventions_hash": "sha256:a1b2c3d4...",
  "timestamp": "2026-03-20T08:30:00+00:00"
}
```

This gives every generated project traceable provenance — stack, backends, model, conventions hash, and timestamp.

### Scaffold log

Forge appends a JSON-lines entry to `~/.forge/scaffold.log` after every scaffold. Each line records the project name, stack, backends used, directory, and timestamp.

```bash
# View your scaffold history
cat ~/.forge/scaffold.log | python -m json.tool --json-lines
```

### Post-scaffold hooks

Create `~/.forge/hooks/post-scaffold.sh` to run custom commands after every scaffold:

```bash
mkdir -p ~/.forge/hooks
cat > ~/.forge/hooks/post-scaffold.sh << 'EOF'
#!/bin/bash
# Example: set up git remote, copy secrets, configure pre-commit
echo "Post-scaffold hook running for $FORGE_PROJECT_NAME ($FORGE_STACK)"
EOF
chmod +x ~/.forge/hooks/post-scaffold.sh
```

The hook runs with the project directory as its working directory and receives these environment variables:

| Variable | Description |
|---|---|
| `FORGE_PROJECT_DIR` | Absolute path to the new project |
| `FORGE_PROJECT_NAME` | Project name |
| `FORGE_STACK` | Stack type (e.g. `nextjs`, `fastapi`) |
| `FORGE_DEMO_MODE` | `1` if demo mode, `0` otherwise |

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
7. It launches the selected AI CLI in a new project directory with a clean live loader.
8. After scaffolding, it writes a `.forge/scaffold.json` manifest into the project.
9. It ensures git is initialized and opens the project in your editor.
10. It runs your post-scaffold hook (if configured) and logs the scaffold to history.

## Project Structure

```text
forge/
├── src/
│   └── ubundiforge/
│       ├── cli.py               # Typer app, single command entry point
│       ├── config.py            # Backend availability checks
│       ├── conventions.py       # Loads conventions from ~/.forge/
│       ├── homebrew.py          # Formula generation helpers
│       ├── prompt_builder.py    # Assembles prompt from answers + conventions
│       ├── prompts.py           # Interactive question flow
│       ├── router.py            # AI backend routing + fallback
│       ├── runner.py            # Subprocess execution of AI CLIs
│       ├── scaffold_log.py      # Scaffold history log and per-project manifest
│       ├── safety.py            # Secret detection
│       ├── scaffold_options.py  # Auth provider and CI action definitions
│       ├── setup.py             # First-run setup wizard
│       ├── stacks.py            # Stack metadata and cross-recipe defaults
│       └── assets/              # Bundled package assets
├── Formula/                     # Generated Homebrew formula source
├── tests/                       # pytest suite
├── docs/                        # Specs, roadmap, diagrams
├── research/                    # Discovery research and archives
├── scripts/                     # Utility scripts
├── pyproject.toml
├── forge                        # Repo-local developer launcher
└── README.md
```

## Development

Set up the development environment:

```bash
uv sync --dev
```

Run tests:

```bash
uv run pytest
```

Run Ruff:

```bash
uv run ruff check src/ubundiforge tests
```

## Notes

- UbundiForge expects external AI CLIs to already be installed and available on `PATH`.
- Config and preferences are stored at `~/.forge/config.json`.
- Conventions are loaded from `~/.forge/conventions.md`. If that file does not exist, the setup wizard creates it with defaults.
- The bundled `CLAUDE.md` template is loaded from `src/ubundiforge/templates/claude-md-template.md`.
- Scaffold history is appended to `~/.forge/scaffold.log`.
- Post-scaffold hooks go in `~/.forge/hooks/post-scaffold.sh`.
- Homebrew release notes live in `docs/homebrew.md`.
