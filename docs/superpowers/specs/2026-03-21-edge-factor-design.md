# UbundiForge Edge Factor — Design Spec

**Date:** 2026-03-21
**Status:** Approved (design phase)
**Goal:** Transform Forge from a functional scaffolder into a premium product with visual polish, learning intelligence, and signature moments that no competing tool offers.

**Target audience:** Ubundi team first, open source later. The quality bar must survive public scrutiny.

**Design principle:** Clean input, stunning output, gorgeous feedback loop. The CLI is effortless to use but visually impressive while it works and when it delivers results.

---

## Phase 1: Visual Polish

Upgrades to the scaffold experience that create immediate wow factor. All built on existing Rich/UI infrastructure with zero new dependencies.

### 1.1 Phase Timeline

**What:** A persistent phase progress indicator shown above the active loader during scaffold execution.

**Current state:** Phases display as isolated loader panels that replace each other. There's no sense of overall progress.

**Design:**
- Horizontal row showing all phases for the current stack: completed (checkmark), active (pulsing dot), pending (dimmed dot)
- Thin progress bar beneath the phase labels, colored per-backend accent (violet/amber/aqua)
- Phase names and elapsed times shown inline
- Updates in real-time via Rich Live (already used by the loader)

**Parallel phases:** When phases run concurrently (e.g. `run_ai_parallel`), all active phases show pulsing dots and their elapsed times update independently. The progress bar shows a blended segment for the concurrent group.

**Integration point:** `runner.py` — requires `run_ai` to accept an optional external `Live` context instead of creating its own. When provided, `run_ai` updates the shared context; when absent, it falls back to its own (preserving backward compatibility). The phase timeline is a Rich renderable composed above the loader panel.

**Files affected:** `runner.py` (interface change to accept shared `Live`), `ui.py` (new `make_phase_timeline` renderable)

### 1.2 File Tree Growth Visualization

**What:** After each phase completes, Forge scans the project directory and renders a color-coded file tree showing what was created.

**Design:**
- Uses Rich Tree component
- Color coding: directories in violet, source files in aqua, config files (pyproject.toml, Dockerfile, etc.) in plum
- Summary line: total files and total lines of code
- Typewriter-style reveal via Rich Live for visual flair (optional, can be instant if it feels slow)
- Appears between phase completions, before the next phase starts

**Integration point:** `runner.py` — called after `run_ai` returns for each phase. Uses `Path.rglob` to scan the project directory.

**Files affected:** `runner.py`, `ui.py` (new `make_file_tree` function)

### 1.3 Real-Time Activity Feed

**What:** Replace the single-line status summary with a scrolling log of completed activity steps.

**Current state:** `_summarize_output_line` classifies backend output into categories (reviewing, writing, testing, etc.) and shows the latest one. Previous steps are lost.

**Design:**
- Accumulate completed activity summaries with checkmarks and elapsed time
- Show the current active step with a spinner
- Max 6 visible lines; oldest scroll off the top
- Deduplicate: if the same summary appears consecutively, update the timer instead of adding a new line

**Parallel phases:** When phases run concurrently, each parallel phase gets a labeled sub-feed within the activity list (e.g., "[Frontend] Writing files" / "[Tests] Running checks"). The `_PhaseProgress` dataclass in `run_ai_parallel` already tracks per-phase summaries — extend it with an activity list.

**Integration point:** `runner.py` — the `_stream_stdout` function already classifies lines. Instead of replacing `summary`, append to a list when the summary changes. The `make_loader_panel` function renders the list.

**Files affected:** `runner.py` (activity list tracking), `ui.py` (update `make_loader_panel` to accept activity list)

### 1.4 Post-Scaffold Dashboard

**What:** After all phases complete, render a comprehensive project report card.

**Design sections:**
- **Header:** Project name, stack, backends used, total scaffold time
- **Health checks:** Pass/fail badges for lint, typecheck, tests (count), build, /health endpoint — data already collected by the verify phase
- **Scaffold summary:** Total files, total lines, phases run, dependency count
- **Next steps:** Contextual commands based on stack (cd, env setup, run command)

**Data sources:**
- Project metadata: from `answers` dict (already available in `cli.py`)
- Health checks: from `VerifyReport` returned by `verify_scaffold` (already collected, needs to be passed through)
- File/line counts: `Path.rglob` + line counting on the project directory
- Dependencies: parse pyproject.toml or package.json

**When `--no-verify` is used:** The health check section displays "skipped" badges instead of pass/fail. The dashboard still renders all other sections (metadata, file counts, next steps).

**Integration point:** `cli.py` — called after all phases and post-scaffold steps complete. A new `render_dashboard` function in `ui.py`.

**Files affected:** `cli.py`, `ui.py` (new `render_dashboard` function)

---

## Phase 2: Intelligence Layer

Forge gets smarter with every scaffold. Data collection starts immediately; features that consume the data ship incrementally.

### 2.1 Quality Memory & Backend Tuning

**What:** Track scaffold quality signals and use them to improve backend routing over time.

**Data collection:**
- After each scaffold, append a JSONL entry to `~/.forge/quality.jsonl`
- Fields: stack, backend, phase, timestamp, and boolean signals: built, tests_passed, lint_clean, typecheck_clean, health_ok
- The quality data collection function receives the `VerifyReport` object from `verify_scaffold` and extracts boolean signals from `CheckResult.passed` values
- When reading quality.jsonl, skip malformed lines silently. Log a warning on the first corrupt line encountered per session.

**Routing integration:**
- After 8+ data points for a stack+phase combination, compute a weighted success score per backend (minimum threshold set high to avoid noise from early scaffolds)
- Exponential moving average (alpha=0.2) so recent results matter more while smoothing out noise from flaky outcomes
- Router uses scores to break ties when multiple backends are available, instead of the static `PHASE_IDEAL_BACKEND` map
- Static map remains the fallback when insufficient data exists

**Files affected:** New `quality.py` module, `router.py` (scoring integration), `cli.py` (data collection call after verify)

### 2.2 Smart Defaults (Adaptive Questions)

**What:** Learn user answer patterns and pre-select dominant choices.

**Data collection:**
- After each scaffold, record answer values to `~/.forge/preferences.json`
- Structure: `{question_key: {value: count, ...}, ...}`

**Adaptive behavior:**
- When one answer accounts for >70% of scaffolds (minimum 3 data points), pre-select it
- Collapse pre-selected questions into a summary line: "Using your defaults: Clerk, GitHub Actions, Docker"
- Show a confirmation prompt listing the defaults: "Use your usual setup? (Clerk, GitHub Actions, Docker) [Y/n]". If the user declines, expand into the full question flow. This uses questionary's existing `confirm` prompt — no custom keybinding work.
- Name and description are never collapsed (always asked)
- The review-and-edit screen remains the final gate before generation

**Files affected:** New `preferences.py` module, `prompts.py` (adaptive question logic)

### 2.3 Scaffold Analytics (`forge stats`)

**What:** A `forge stats` command that renders a terminal dashboard of scaffold history and backend performance.

**Metrics:**
- Total scaffolds, overall success rate, average scaffold time, total lines generated
- Stack distribution bar chart
- Backend performance table (success rate per phase)
- Recent scaffolds list with outcomes

**Data sources:** Existing `~/.forge/scaffold.log` (already implemented) + new `quality.jsonl`

**Rendering:** Rich Tables and bar charts (unicode block characters). No external dependencies.

**Files affected:** `cli.py` (new `stats` command), new `analytics.py` module

### 2.4 `forge evolve` — Augment Existing Projects

**What:** Add capabilities to existing Forge-scaffolded projects using the project's scaffold DNA.

**How it works:**
1. Detect `.forge/scaffold.json` in the current directory
2. Read project DNA: stack, conventions, options, scaffold timestamp
3. Present a menu of capabilities appropriate for the detected stack:
   - FastAPI: auth, WebSockets, S3 uploads, Stripe, background worker, monitoring
   - Next.js: auth, analytics, CMS integration, i18n, PWA
   - Both: all of the above
4. Assemble an "evolve prompt" that includes: project DNA, current file tree, and key file contents selected by: (a) the main app entry point, (b) any existing file matching the capability's `typically_touches` list, (c) the project's pyproject.toml/package.json. Cap total included file content at 8000 tokens to stay within backend context limits.
5. Route through the standard backend routing system
6. Update `.forge/scaffold.json` with the evolution record

**Capability registry:** A new `evolutions.py` module with per-stack capability definitions. Each capability has: name, description, prompt fragment, and a list of files it typically touches (for context inclusion).

**Sub-features (for incremental delivery):**
- (a) evolve command skeleton + capability registry data structure
- (b) evolve prompt assembly (file selection, token budgeting, context building)
- (c) per-stack capability definitions (prompt fragments for each capability)

**Files affected:** `cli.py` (new `evolve` command), new `evolutions.py` module, `prompt_builder.py` (evolve prompt assembly)

---

## Phase 3: Signature Moments

Distinctive touches that become Forge's identity.

### 3.1 Convention Drift Detection (`forge check`)

**What:** Deterministic, local-only audit of any project against Ubundi conventions.

**How it works:**
1. Detect stack from pyproject.toml/package.json
2. Load matching convention profile from `~/.forge/conventions.md` or `.forge/conventions.md`
3. Run checks organized by category:
   - **Structure:** Required directories and files per stack (tests/, agent_docs/, CLAUDE.md, .env.example, etc.)
   - **Tooling:** Ruff config with required rules, pre-commit hooks, CI presence, MyPy strict mode
   - **Runtime:** Health endpoint, Docker non-root user, HEALTHCHECK directive
4. Output a pass/warn/fail scorecard with counts

**Flags:**
- `forge check` — audit and report
- `forge check --fix` — auto-generate missing files from templates (CLAUDE.md, .env.example, agent_docs/ skeleton). For files that exist but fail checks, `--fix` will not overwrite — it reports them as `warn` with a suggestion to update manually.
- `forge check --export report.md` — save the report for PR comments or reviews

**Check definitions:** A declarative check registry in a new `checks.py` module. Each check: name, category, detection function, severity (pass/warn/fail), fix function (optional).

**Files affected:** `cli.py` (new `check` command), new `checks.py` module

### 3.2 Scaffold Replay & Diff

**What:** Reproduce a past scaffold and optionally diff against the current project state.

**How it works:**
1. Read `.forge/scaffold.json` from the target project
2. Reconstruct the original prompt using stored inputs + locked conventions (convention hash stored in manifest)
3. Scaffold into a temp directory using the same backend routing. If the original backend is unavailable, fall back to standard routing and warn the user that results may differ.
4. `--diff` compares the replay output against the current project directory. Because AI backends are non-deterministic, the diff shows structural drift (files added/removed, patterns changed by the user) rather than an exact delta.
5. Output: added/changed/removed file summary, optionally a full diff saved to `.forge/replay-diff-<date>.md`

**Flags:**
- `forge replay` — re-scaffold from DNA in current directory
- `forge replay <project-name>` — look up in scaffold.log by name
- `forge replay --diff` — scaffold + compare

**Dependency:** Requires convention content to be stored or referenced in the manifest. Current manifest stores a conventions hash but not the content. Design decision: store conventions content snapshot in `.forge/conventions-snapshot.md` at scaffold time.

**Files affected:** `cli.py` (new `replay` command), `prompt_builder.py` (reconstruct from manifest), `runner.py` (temp directory execution), `scaffold_log.py` (`write_scaffold_manifest` must write `conventions-snapshot.md` alongside `scaffold.json`)

### 3.3 The Forge Card

**What:** Auto-generated README badge and SVG project card.

**Badge:** Shields.io-style inline badge — "forged with | UbundiForge" in violet + indigo. Generated as a static SVG string from a Python template. Injected into the project README.md after the first heading.

**Card:** A richer SVG showing project name, stack, backends, and scaffold date. Saved to `.forge/card.svg`. Useful for internal dashboards or social sharing.

**Generation:** Pure Python string templating. The SVG templates are ~30 lines each. No external dependencies.

**Files affected:** New `card.py` module, `cli.py` (call after scaffold), `runner.py` (README badge injection in `ensure_git_init` or post-scaffold)

### 3.4 Completion Sound

**What:** Optional audio feedback when a scaffold finishes.

**Design:**
- Success: two-tone ascending chime
- Failure: single low tone
- Opt-in via `~/.forge/config.json`: `"sound": true`
- macOS: `afplay` with bundled WAV files (<25KB each, stored in package data)
- Linux: `paplay` or `aplay` fallback
- Universal fallback: terminal bell (`\a`)
- Plays asynchronously (non-blocking)

**Distribution note:** Update `pyproject.toml` `[tool.hatch.build]` to include sound files as package data. Add a test verifying the sound files are accessible via `importlib.resources`.

**Files affected:** New `sound.py` module, `cli.py` (call after scaffold completion), `pyproject.toml` (package data config)

---

## Implementation Priority

Ordered by impact-to-effort ratio, with dependencies respected:

| # | Feature | Phase | Effort | Impact |
|---|---------|-------|--------|--------|
| 1 | Post-scaffold dashboard | P1 | Medium | High — the screenshot moment |
| 2 | Activity feed | P1 | Low | High — builds on existing summarizer |
| 3 | Phase timeline | P1 | Medium | High — ties the experience together |
| 4 | File tree growth | P1 | Low | Medium — cherry on top |
| 5 | Quality memory + routing | P2 | Medium | High — data collection starts early |
| 6 | Smart defaults | P2 | Medium | High — reduces friction over time |
| 7 | forge stats | P2 | Low | Medium — visualization of collected data (depends on #5) |
| 8 | forge evolve | P2 | High | Very high — unique differentiator |
| 9 | forge check | P3 | Medium | High — standalone value for any project |
| 10 | Forge card + badge | P3 | Low | Medium — viral branding |
| 11 | Completion sound | P3 | Low | Low — quick sensory win |
| 12 | Scaffold replay | P3 | High | Medium — power user feature |

---

## Architectural Notes

**No new dependencies.** Everything is built with Rich, Python stdlib, and existing Forge infrastructure.

**New modules:**
- `quality.py` — quality signal collection and scoring
- `preferences.py` — answer frequency tracking and adaptive defaults
- `analytics.py` — scaffold statistics aggregation and rendering
- `evolutions.py` — per-stack evolution capability registry
- `checks.py` — convention check registry and execution
- `card.py` — SVG badge and card generation
- `sound.py` — audio feedback

**Data files (all under `~/.forge/`):**
- `quality.jsonl` — quality signals per scaffold (new)
- `preferences.json` — answer frequency data (new)
- `scaffold.log` — scaffold history (existing, extended)

**Project files (under `.forge/` in scaffolded projects):**
- `scaffold.json` — project DNA (existing, extended with evolution records)
- `conventions-snapshot.md` — conventions at scaffold time (new, for replay)
- `card.svg` — project card (new)
- `replay-diff-<date>.md` — replay comparison output (new, on demand)
