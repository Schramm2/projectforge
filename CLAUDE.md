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
  media_assets.py      Scan, manifest, and copy media/ collections into scaffolds
  scaffold_log.py     Append-only scaffold history + per-project manifest
  safety.py            Secret detection on user-supplied text
  scaffold_options.py  Auth provider and CI action definitions
  setup.py             First-run setup wizard
  config.py            Backend availability checks
  ui.py                Shared Rich UI primitives and Ubundi palette
  questionary_theme.py Themed questionary prompt wrappers
  logo.py              ASCII art banner
tests/                 pytest suite mirroring ubundiforge/ modules
docs/                  Specs, roadmap, reference docs
research/              Discovery research and archived notes
scripts/               install.sh and utility scripts
assets/                ASCII art and static assets
media/                 User media collections (media/<brand>/logo.svg etc.)
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

## Release Workflow

Before testing a true new-user install flow from Homebrew, publish the changes
as a new release first. Otherwise the brew install path will still serve the
previous version.

Release checklist:

1. Bump the version in both:
   - `pyproject.toml`
   - `src/ubundiforge/__init__.py`
2. Add a new entry to `CHANGELOG.md`.
3. Refresh `uv.lock` if runtime dependencies changed.
4. Verify locally:
   - `uv run pytest`
   - `uv run ruff check src/ubundiforge tests`
   - `./forge --dry-run --name release-smoke --stack fastapi --description "release smoke test"`
5. Commit and tag the release:
   - `git add .`
   - `git commit -m "release: vX.Y.Z"`
   - `git tag vX.Y.Z`
   - `git push origin main --tags`
6. Compute the GitHub release tarball checksum:
   - `curl -Ls https://github.com/matthewubundi/UbundiForge/archive/refs/tags/vX.Y.Z.tar.gz | shasum -a 256`
7. Regenerate `Formula/ubundiforge.rb`:
   - `python3 scripts/generate_homebrew_formula.py --source-url https://github.com/matthewubundi/UbundiForge/archive/refs/tags/vX.Y.Z.tar.gz --source-sha256 <sha256>`
8. Commit the updated formula in this repo.
9. Sync `Formula/ubundiforge.rb` into the Homebrew tap repo.
10. Validate the tap:
   - `brew install --build-from-source matthewubundi/tap/ubundiforge`
   - `brew test matthewubundi/tap/ubundiforge`
11. Push the tap update.

Only after that should you run a real new-user brew smoke test:

- `brew install ubundiforge`
- `forge --version`
- `forge`

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
