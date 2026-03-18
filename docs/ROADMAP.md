# Forge Roadmap — Feature Ideas & Improvements

Ideas for expanding Forge into a production-grade Ubundi project scaffolder. Organized by theme, not priority.

Items marked with [DONE] have been implemented.

---

## Smarter AI Routing

- **Quality-based routing**: Track which backend produces better results per stack over time. Store simple success/failure signals after each scaffold and shift routing weights accordingly.
- [DONE] **Model selection per backend**: `--model opus` passes the model flag through to the AI CLI subprocess.
- [DONE] **Fallback chain**: If the primary backend isn't installed, automatically try the next available (claude → gemini → codex).
- **Cost-aware routing**: For backends with usage-based pricing, optionally prefer cheaper options for simple scaffolds.

---

## Multi-Convention Support

- **Named convention profiles**: `forge --conventions fintech-client` loads `~/.forge/conventions/fintech-client.md` instead of the default. Different clients, different standards.
- **Convention composition**: Stack multiple convention files — a base `ubundi.md` plus a client-specific overlay.
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
  - CLI tool (Python or Node)
  - Turborepo monorepo
- **Sub-stack prompts**: After selecting "Next.js + React", ask follow-ups like "Auth provider?" (Supabase, Clerk, NextAuth), "Database?" (Postgres, SQLite, none), "UI library?" (shadcn/ui, Radix, none).
- **Stack detection from existing project**: Run `forge` inside an existing repo and have it detect the stack from package.json / pyproject.toml, then scaffold missing pieces (e.g. add Docker to an existing project).

---

## Template System

- **Scaffold templates**: Pre-built prompt fragments for common patterns — Stripe integration, Supabase auth, S3 uploads, WebSocket setup. User selects add-ons during the question flow.
- **Template registry**: `forge templates list` / `forge templates add stripe-checkout` to manage reusable scaffold fragments.
- **Community templates**: Pull templates from a shared repo or registry so teams can share patterns.
- **CLAUDE.md template variants**: Different CLAUDE.md templates per stack (frontend vs backend vs fullstack each get a tailored structure).

---

## Post-Scaffold Automation

- **Auto-install dependencies**: After the AI finishes, detect package.json / pyproject.toml and run the install automatically.
- [DONE] **Auto-open in editor**: `forge --open` opens the new project in Cursor or VS Code after scaffolding.
- [DONE] **Auto-git-init**: Verifies git was initialized after scaffold; if not, runs `git init` and makes an initial commit.
- **Post-scaffold hooks**: User-defined scripts in `~/.forge/hooks/post-scaffold.sh` that run after every scaffold (e.g. configure git remote, set up pre-commit hooks, copy .env from a vault).
- **Health check**: After scaffolding, attempt to run the project's dev server briefly to verify it actually works.

---

## Interactive Improvements

- **Saved presets**: `forge --save-preset api-starter` saves your current answers. Next time: `forge --preset api-starter` skips the questions entirely.
- **Recent projects**: `forge --last` repeats the most recent scaffold with the same settings but a new name.
- **Prompt editor**: `forge --edit-prompt` opens the assembled prompt in $EDITOR before sending it, so you can tweak it.
- [DONE] **Progress display**: Rich spinner with elapsed time while the AI CLI is working.
- [DONE] **Non-interactive mode**: `forge --name pulse --stack fastapi --description "health API" --no-docker` for scripting and CI.

---

## Output Quality

- **Scaffold validation**: After the AI finishes, run basic checks — does the expected file structure exist? Is there a package.json/pyproject.toml? Does it parse correctly?
- **Diff review**: Show a tree of created files with line counts before the AI starts writing, let the user approve.
- **Retry with feedback**: If the scaffold is bad, `forge retry "the auth setup is wrong, use Clerk not NextAuth"` re-runs with the original prompt plus correction.
- **Multi-pass scaffolding**: First pass creates structure, second pass reviews and fixes issues. Expensive but higher quality.

---

## Project Management

- **Scaffold log**: `forge log` shows a history of all projects scaffolded — name, stack, date, backend used, directory.
- **Project registry**: Track active Ubundi projects with their locations, stacks, and status.
- **Scaffold analytics**: Which stacks are you building most? Which backend succeeds most often? Simple local stats.

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
- [DONE] **Risky change confirmation**: Prompts for confirmation before overwriting an existing non-empty project directory.

---

## Reproducibility & Auditability

- **Scaffold manifest**: Write a `.forge/scaffold.json` file containing the stack, backend, model, prompt hash, conventions hash, selected templates, and timestamp so every generated project has traceable provenance.
- **Replay exact scaffold**: `forge replay <project-or-log-id>` re-runs a scaffold with the original inputs and locked conventions for debugging, comparison, or regeneration.
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
- **Shell completions**: Tab completion for `--use`, `--stack`, `--preset`, `--conventions` values.
- [DONE] **Verbose mode**: `forge --verbose` shows the full subprocess command, conventions file size, prompt length, and execution timing.
- [DONE] **Config file**: `~/.forge/config.json` for persistent preferences (default backend, preferred editor, Docker availability, default project directory). Set up via the first-run setup wizard or `forge --setup`.
- **Update checker**: Notify when a new version of Forge is available.

---

## Testing & Reliability

- **Integration tests**: Spin up a test scaffold with `--dry-run` and validate the prompt contains expected sections.
- **Snapshot tests**: Store expected prompt outputs and diff against them on changes.
- **CI pipeline**: GitHub Actions running lint, tests, and a dry-run scaffold on every push.
- **Mock backends**: Test the full flow without requiring actual AI CLIs installed.

---

## Deployment & Distribution (Priority)

This is the key milestone — getting Forge into the hands of Ubundi team members with a single command.

The target workflow:
1. Team member runs `brew install ubundiforge`
2. Runs `forge` from any directory
3. Setup wizard runs on first use (detects tools, configures preferences)
4. Projects scaffold into their configured directory with Ubundi conventions baked in

Steps to ship:
- **Publish to PyPI**: `uv build && uv publish` (needs PyPI account + API token)
- **Create Homebrew tap**: `Ubundi/homebrew-tap` repo on GitHub with a formula pointing at the PyPI package
- **Homebrew formula**: `brew tap ubundi/tap && brew install ubundiforge`
- Transfer repo from `matthewubundi/UbundiForge` to `Ubundi/ubundiforge` when ready
- **pipx support**: `pipx install ubundiforge` for isolated global install (works automatically once on PyPI)
- **Auto-update**: `forge update` pulls the latest version.
- **Docker image**: Run Forge itself in a container with all three AI CLIs pre-installed.
