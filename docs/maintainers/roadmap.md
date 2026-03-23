# Forge Roadmap — Current Status & Next Steps

Live roadmap for expanding Forge into a production-grade Ubundi project scaffolder. Organized by theme, not strict priority.

Items marked with [DONE] are implemented in this repository as of `0.4.0`. Planned items are intentionally aspirational; example commands below describe direction, not guaranteed current CLI flags.

---

## Setup & Onboarding

- [DONE] **Backend readiness checks**: Setup distinguishes between installed backends and backends that are actually ready to scaffold, and routing skips known-not-ready tools.
- [DONE] **First-run handoff**: After setup, new users can create a project immediately, review setup again, or exit cleanly and come back later.
- [DONE] **Inline git identity setup**: Setup offers to configure global `git user.name` and `git user.email` when they are missing.
- **Setup profiles**: Support different setup defaults for different working modes, such as "client delivery", "internal tool", and "prototype".

## Smarter AI Routing

- [DONE] **Quality-based routing**: Tracks which backend produces better results per stack over time. Stores success/failure signals after each scaffold in `~/.forge/quality.jsonl` and shifts routing weights using exponential moving average scoring. The router overrides the ideal backend when a clearly better alternative exists (>0.1 margin, minimum 8 data points).
- [DONE] **Model selection per backend**: `--model opus` passes the model flag through to the AI CLI subprocess.
- [DONE] **Fallback chain**: If the primary backend isn't installed, automatically try the next available (claude -> gemini -> codex).
- [DONE] **Multi-backend phase routing**: Different scaffold phases (architecture, frontend, tests, verify) route to the ideal AI backend based on strengths. Adjacent phases using the same backend are merged to reduce handoffs.
- [DONE] **Specialist prompt variants**: Each phase has a "best" prompt variant optimized for its ideal backend, plus a general fallback variant for other backends.
- **Cost-aware routing**: For backends with usage-based pricing, optionally prefer cheaper options for simple scaffolds.

---

## Scaffold Experience

- [DONE] **Phase timeline**: Persistent horizontal progress indicator showing completed, active, and pending phases with a color-coded progress bar during scaffold execution.
- [DONE] **Activity feed**: Scrolling log of completed scaffold activities with checkmarks, replacing the single-line status display. Shows what the AI backend is doing in real-time.
- [DONE] **File tree visualization**: Color-coded file tree rendered between phases showing what was created — directories in violet, source files in aqua, config files in plum, with file/line counts.
- [DONE] **Post-scaffold dashboard**: Project report card showing metadata (name, stack, backends, time), health check results, scaffold summary (files, lines, phases, deps), and contextual next steps.
- [DONE] **Completion sound**: Optional audio feedback on scaffold completion — macOS system sounds (Glass for success, Basso for failure) with terminal bell fallback. Opt-in via `~/.forge/config.json: {"sound": true}`.

---

## Multi-Convention Support

- **Named convention profiles**: `forge --conventions fintech-client` loads `~/.forge/conventions/fintech-client.md` instead of the default. Different clients, different standards.
- **Convention composition**: Stack multiple convention files — a base `ubundi.md` plus a client-specific overlay.
- [DONE] **Convention drift detection**: `forge check` audits any project against Ubundi conventions with a pass/warn/fail scorecard. Checks structure (required files/directories), tooling (Ruff config, MyPy strict, pre-commit, CI), and runtime (health endpoint, Docker non-root, HEALTHCHECK). Supports `--fix` for auto-generating missing files and `--export report.md` for sharing audits.
- [DONE] **Project-local conventions**: Checks `.forge/conventions.md` in the current directory first, falls back to `~/.forge/conventions.md`.
- [DONE] **Convention validation**: Warns if the conventions file is empty or suspiciously short.

---

## Stack Expansion

- **More stack options**:
  - React Native / Expo (mobile)
  - Django
  - Go (Chi / Gin)
  - Astro / static sites
  - Chrome extension
  - Turborepo monorepo
- [DONE] **Python CLI stack**: `python-cli` stack for building Typer-based CLI tools.
- [DONE] **TypeScript package stack**: `ts-package` stack for npm package scaffolding.
- [DONE] **Python worker stack**: `python-worker` stack for background workers and services.
- [DONE] **AI-powered API stack**: `fastapi-ai` stack for FastAPI services with LLM/embeddings integration.
- [DONE] **Scaffold options & auth providers**: Configurable auth providers (Clerk, Supabase Auth, Auth.js, Better Auth), CI template modes, and per-stack service selections via `scaffold_options.py`.
- **Sub-stack prompts**: After selecting "Next.js + React", ask follow-ups like "Auth provider?" (Supabase, Clerk, NextAuth), "Database?" (Postgres, SQLite, none), "UI library?" (shadcn/ui, Radix, none).
- **Stack detection from existing project**: Run `forge` inside an existing repo and have it detect the stack from package.json / pyproject.toml, then scaffold missing pieces (e.g. add Docker to an existing project).

---

## Design & Media

- [DONE] **Design templates**: Bundled, global (`~/.forge/design-templates/`), and project-local design template resolution. Includes Ubundi Brand Guide template. Templates are integrated into the scaffold prompt and selectable during the interactive flow.
- [DONE] **Media assets & collections**: Media asset detection and copying from repo-local `media/` collections. Supports images, fonts, and vectors across all stacks with manifest generation and prompt integration via `media_assets.py`.

---

## Project Augmentation

- [DONE] **Forge evolve**: `forge evolve` adds capabilities to existing Forge-scaffolded projects. Reads the project's `.forge/scaffold.json` DNA, presents a menu of stack-appropriate capabilities (auth, WebSockets, S3 uploads, Stripe, background workers, monitoring, analytics, i18n), assembles a context-aware prompt with file tree and key file contents (capped at 8K tokens), and routes through the standard backend system. Evolution records are appended to the manifest.
- **Scaffold templates**: Pre-built prompt fragments for common patterns — Stripe integration, Supabase auth, S3 uploads, WebSocket setup. User selects add-ons during the question flow.
- **Template registry**: `forge templates list` / `forge templates add stripe-checkout` to manage reusable scaffold fragments.
- **Community templates**: Pull templates from a shared repo or registry so teams can share patterns.
- **CLAUDE.md template variants**: Different CLAUDE.md templates per stack (frontend vs backend vs fullstack each get a tailored structure).

---

## Post-Scaffold Automation

- [DONE] **Auto-install dependencies**: The verify phase detects package.json / pyproject.toml and runs the appropriate install (npm install / uv sync) automatically.
- [DONE] **Auto-open in editor**: `forge --open` opens the new project in the configured editor after scaffolding.
- [DONE] **Auto-git-init**: Verifies git was initialized after scaffold; if not, runs `git init` and makes an initial commit.
- [DONE] **Health check**: The verify phase starts the dev server and probes `/health` or `/ready` endpoints to confirm the project boots.
- [DONE] **Post-scaffold verification**: `--verify/--no-verify` runs lint, typecheck, build, and test commands after scaffolding with a Rich table summary of results.
- [DONE] **Post-scaffold hooks**: User-defined scripts in `~/.forge/hooks/post-scaffold.sh` that run after every scaffold (e.g. configure git remote, set up pre-commit hooks, copy .env from a vault).
- [DONE] **Forge card**: Auto-generated SVG project card saved to `.forge/card.svg` and shields.io-style badge auto-injected into README.md after scaffolding. Shows project name, stack, backends, and scaffold date.

---

## Interactive Improvements

- [DONE] **Smart defaults**: Forge learns answer patterns across scaffolds and offers to pre-fill dominant choices. After 3+ scaffolds with >70% consistency on an answer, shows "Your usual setup: Auth: clerk, Docker: yes" with a confirm prompt. The review screen remains the final gate.
- **Saved presets**: `forge --save-preset api-starter` saves your current answers. Next time: `forge --preset api-starter` skips the questions entirely.
- **Recent projects**: `forge --last` repeats the most recent scaffold with the same settings but a new name.
- **Prompt editor**: `forge --edit-prompt` opens the assembled prompt in $EDITOR before sending it, so you can tweak it.
- [DONE] **Review-and-edit flow**: Interactive scaffolding ends with a review screen where users can edit basics, design/media, integrations, or demo mode before generation starts.
- [DONE] **Progress display**: Rich spinner with elapsed time while the AI CLI is working.
- [DONE] **Non-interactive mode**: `forge --name pulse --stack fastapi --description "health API" --no-docker` for scripting and CI.
- [DONE] **Demo mode**: `forge --demo` scaffolds projects that run without real API keys by using mock data and graceful fallbacks. Toggleable via `--demo/--no-demo`.

---

## Output Quality

- **Scaffold validation**: After the AI finishes, run basic checks — does the expected file structure exist? Is there a package.json/pyproject.toml? Does it parse correctly?
- **Diff review**: Show a tree of created files with line counts before the AI starts writing, let the user approve.
- **Retry with feedback**: If the scaffold is bad, `forge retry "the auth setup is wrong, use Clerk not NextAuth"` re-runs with the original prompt plus correction.
- [DONE] **Multi-pass scaffolding**: Scaffold phases (architecture, frontend, tests, verify) run sequentially, each reviewing and building on the previous phase's output. The verify phase acts as a final QA pass.
- [DONE] **Multi-agent orchestration**: `--agents` decomposes each phase into 2-6 focused subagent tasks with dependency-aware parallel execution, live activity feed, and automatic reconciliation. Selectable interactively via the "Execution mode" prompt.

---

## Project Management

- [DONE] **Scaffold log**: Every scaffold appends a JSON-lines entry to `~/.forge/scaffold.log` — name, stack, backends, directory, demo mode, timestamp.
- [DONE] **Scaffold analytics**: `forge stats` renders a terminal dashboard showing total scaffolds, success rate, stack distribution bar chart, per-backend/phase performance rates, and recent scaffold history. Data sourced from `scaffold.log` and `quality.jsonl`.
- **Project registry**: Track active Ubundi projects with their locations, stacks, and status.

---

## Team & Sharing

- **Shared conventions via git**: `forge conventions pull git@github.com:ubundi/conventions.git` syncs team conventions from a shared repo.
- **Convention locking**: `forge conventions lock` snapshots the current conventions so scaffolds are reproducible even if the file changes later.
- [DONE] **Export scaffold prompt**: `forge --export prompt.md` saves the assembled prompt to a file for sharing or debugging.

---

## Governance & Guardrails

- **Ubundi standard packs**: `forge --standard api-service` or `forge --standard internal-tool` applies an approved bundle of stack choices, docs, CI, Docker, observability, and naming conventions with fewer questions.
- **Policy checks before handoff**: Validate the chosen scaffold against Ubundi rules before sending it to the AI CLI — required docs present, approved runtime versions, allowed dependency families, and required files like `.env.example`.
- **Dependency and license allowlists**: Warn or block when a scaffold asks for packages outside an approved set, or licenses that do not meet Ubundi policy.
- [DONE] **Safer existing-directory handling**: When the target directory already exists and is non-empty, Forge lets the user rename the project, overwrite the directory, or cancel.

---

## Reproducibility & Auditability

- [DONE] **Scaffold manifest**: Write a `.forge/scaffold.json` file containing stack, description, phase routing, model override, backend model preferences, selected options, conventions hash, and timestamp so every generated project has traceable provenance.
- [DONE] **Scaffold replay**: `forge replay` re-runs a scaffold using the project's original inputs from `.forge/scaffold.json` and locked conventions from `.forge/conventions-snapshot.md`. Supports `--diff` for comparing the replay against the current project to detect structural drift. Saves diff reports to `.forge/replay-diff-<date>.md`.
- [DONE] **Conventions snapshot**: `write_scaffold_manifest` saves a copy of the conventions content as `.forge/conventions-snapshot.md` alongside the manifest, ensuring replay uses the exact conventions from scaffold time.
- **Decision log**: Record which defaults were accepted, which were overridden, and which warnings were ignored so teams can understand why a project deviates from the golden path.
- **Prompt + output bundle**: `forge bundle` saves the assembled prompt, manifest, backend choice, and validation results into one artifact for review, support, or future audits.

---

## Security & Production Readiness

- **Security baseline starter**: Offer an opinionated bundle with Dependabot or Renovate, basic secret scanning, pinned runtime versions, and a secure default `.gitignore` / `.env.example`.
- **Observability bootstrap**: Generate structured logging, request IDs, health endpoints, readiness checks, and a starter metrics/tracing setup for supported backend stacks.
- **Readiness scorecard**: After scaffolding, grade the project against a production checklist — tests, linting, CI, Docker health checks, docs, env file examples, logging, and error handling.
- [DONE] **Secrets-safe prompts**: Scans extra instructions for Stripe keys, GitHub tokens, AWS keys, Slack tokens, JWTs, and private keys. Blocks execution if detected.

---

## Internal Platform Integration

- **GitHub repo bootstrap**: `forge --create-repo` creates the repository, sets visibility, applies branch protection defaults, adds CODEOWNERS, and seeds labels or issue templates.
- **Ubundi project naming rules**: Enforce or suggest naming conventions for repos, packages, Docker images, and service names so new projects line up with internal standards automatically.
- **Internal service presets**: Pre-configured options for Ubundi's most common internal builds — API service, worker, CLI utility, research prototype, npm package — each with the right defaults and docs.
- **Environment bootstrap**: Generate environment-specific config scaffolds for `local`, `staging`, and `prod`, including example variable files and a clear promotion path between them.

---

## Developer Experience

- **Plugin system**: Third-party plugins that add new stacks, backends, or post-scaffold hooks. Simple Python entry points.
- [DONE] **Shell completions**: Built-in Typer completion support via `--install-completion` / `--show-completion`, plus value completion for typed options such as `--use` and `--stack`.
- [DONE] **Verbose mode**: `forge --verbose` shows the full subprocess command, conventions file size, prompt length, and execution timing.
- [DONE] **Config file**: `~/.forge/config.json` stores preferred editor, detected backends, per-backend model preferences, Docker availability, default project directory, and sound preference. Set up via the first-run setup wizard or `forge --setup`.
- **Update checker**: Notify when a new version of Forge is available.

---

## Testing & Reliability

- [DONE] **Integration tests**: Spin up a test scaffold with `--dry-run` and validate the prompt contains expected sections.
- [DONE] **Snapshot tests**: Store expected prompt outputs and diff against them on changes.
- [DONE] **CI pipeline**: GitHub Actions running Ruff, the full pytest suite, package builds, and a `forge --dry-run` smoke check on pushes and PRs.
- [DONE] **Mock backends**: Test the full flow without requiring actual AI CLIs installed.
- [DONE] **408 tests**: Comprehensive test coverage across all modules — dashboard, activity feed, phase timeline, file tree, quality memory, preferences, analytics, evolutions, checks, card, sound, scaffold log, protocol, subprocess utilities, adapters, and orchestration.

---

## Deployment & Distribution

Packaging groundwork is in place; release automation and wider distribution are the next layer.

The target workflow:
1. Team member runs `brew install ubundiforge`
2. Runs `forge` from any directory
3. Setup wizard runs on first use (detects tools, configures preferences)
4. Projects scaffold into their configured directory with Ubundi conventions baked in

Steps to ship:
- [DONE] **Homebrew formula**: The repo includes `Formula/ubundiforge.rb`, a formula generator, and documented Homebrew release steps.
- [DONE] **Automated Homebrew release flow**: Pushing a new version to `main` creates the release tag, GitHub release, regenerates the Homebrew formula, and syncs the tap. See `.github/workflows/release-homebrew.yml`.
- [DONE] **Buildable package metadata**: `pyproject.toml` is set up for versioned source/wheel builds.
- **Publish releases to PyPI**: optional later, if Forge needs a Python package distribution channel.
- Transfer repo from `matthewubundi/UbundiForge` to `Ubundi/ubundiforge` when ready
- **Auto-update**: `forge update` pulls the latest version.
- **Docker image**: Run Forge itself in a container with all three AI CLIs pre-installed.

---

## CLI Commands Summary (v0.4.0)

| Command | Description |
|---------|-------------|
| `forge` | Interactive scaffold flow (default) |
| `forge --agents` | Scaffold with multi-agent orchestration |
| `forge stats` | Scaffold analytics dashboard |
| `forge evolve [capability]` | Add capabilities to existing projects |
| `forge check` | Convention drift detection |
| `forge replay` | Reproduce past scaffolds |
| `forge conventions` | Manage bundled convention bundles |
