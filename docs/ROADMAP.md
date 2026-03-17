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
- **Project-local conventions**: Check for a `.forge/conventions.md` in the current directory first, then fall back to `~/.forge/conventions.md`. Useful for monorepos with sub-project conventions.
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
- **Auto-git-init**: Verify git was initialized, make the initial commit if the AI didn't.
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

## Developer Experience

- **Plugin system**: Third-party plugins that add new stacks, backends, or post-scaffold hooks. Simple Python entry points.
- **Shell completions**: Tab completion for `--use`, `--stack`, `--preset`, `--conventions` values.
- [DONE] **Verbose mode**: `forge --verbose` shows the full subprocess command, conventions file size, prompt length, and execution timing.
- **Config file**: `~/.forge/config.toml` for persistent preferences (default backend, default Docker=yes, preferred editor, etc).
- **Update checker**: Notify when a new version of Forge is available.

---

## Testing & Reliability

- **Integration tests**: Spin up a test scaffold with `--dry-run` and validate the prompt contains expected sections.
- **Snapshot tests**: Store expected prompt outputs and diff against them on changes.
- **CI pipeline**: GitHub Actions running lint, tests, and a dry-run scaffold on every push.
- **Mock backends**: Test the full flow without requiring actual AI CLIs installed.

---

## Deployment & Distribution

- **Homebrew formula**: `brew install forge` for easy installation on macOS.
- **pipx support**: `pipx install forge-cli` for isolated global install.
- **Docker image**: Run Forge itself in a container with all three AI CLIs pre-installed.
- **Auto-update**: `forge update` pulls the latest version.
