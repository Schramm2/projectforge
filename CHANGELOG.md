# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

These entries describe changes on `main` after v0.6.0. The package version remains `0.6.0` until
the next release is prepared.

### Added

- A complete D2 product-diagram set and static landing page covering the user journey, product
  boundary, input flow, routing, prompt assembly, runtime pipeline, project lifecycle, and trust
  boundaries.
- A maintained inventory of user-visible failure paths and their recovery-safe wording.

### Changed

- Renamed the canonical Python import namespace from `ubundiforge` to `projectforge` across the
  source tree, tests, launchers, workflows, packaging, and maintainer commands. The PyPI
  distribution remains `matt-projectforge`, and the installed commands remain `projectforge` and
  the compatibility alias `forge`.
- Provider, filesystem, setup, convention, verification, replay, resume, editor, Git, media, and
  hook failures now favor bounded recovery guidance over raw exceptions, provider output, local
  paths, or hook failure streams.
- Failure paths preserve completed project work and distinguish required scaffold records from
  optional local evidence so non-critical record failures do not erase a successful scaffold.

## [0.6.0] - 2026-07-18

### Added

- Releases publish to PyPI as `matt-projectforge` through a gated trusted-publishing job, with a
  maintainer runbook and clean uv/pipx verification steps.
- The execution preflight now shows per-provider CLI invocation estimates, quota context, a rough
  numeric cost range, and the last locally measured duration for the selected stack.
- The `projectforge` executable is now the preferred collision-free alias; `forge` remains for
  compatibility and its collision with Foundry is documented.

### Changed

- Scaffold Context summarizes convention source count and size by default; full source hashes now
  require `--verbose` and remain recorded in `.forge/scaffold.json`.
- Interactive execution choices now identify Standard as the actual default and quantify the extra
  multi-agent invocation overhead instead of recommending a non-default choice.
- Doctor diagnostics now report each non-ready provider's exact check, credential-safe observation,
  and concrete next step, and describe missing editors as a PATH/setup issue.
- Successful scaffold history records total duration for stack-specific future estimates.

## [0.5.1] - 2026-07-18

### Added

- `FORGE_HOME` isolates user data for automation, and `forge stats --repair` quarantines
  recognizable legacy pytest artifacts without deleting them.
- The README now opens with an outcome-first walkthrough of the scaffold and verification flow.

### Changed

- Replaced the retired Gemini CLI backend with Google Antigravity CLI (`agy`) across routing,
  adapters, setup, execution, diagnostics, tests, and documentation.
- `forge doctor` now verifies Antigravity Google Sign-In through `agy models` without sending an
  inference prompt or storing provider output.
- Legacy saved `gemini` backend selections migrate to `antigravity`; incompatible Gemini model
  overrides are dropped in favor of Antigravity's current provider default.
- Verification quality is recorded only when verification ran, and stats report scaffold-level
  verification outcomes instead of treating skipped checks or agent-task records as failures.
- Verify-and-fix prompts now specialize frontend and non-frontend stacks independently.

### Fixed

- Backend fallback now follows the declared `claude -> antigravity -> codex` order instead of
  depending on unordered set iteration.
- The pytest suite now redirects config, history, preferences, hooks, and quality memory to a fresh
  temporary Forge home for every test.
- Empty stats now explain how to create the first scaffold instead of presenting a 0% success rate.

### Security

- Antigravity safe and plan modes enable its terminal sandbox. The dangerous permission bypass is
  available only through `--approval-mode unsafe --allow-unsafe`.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-07-18

### Added

- `forge doctor` human and JSON diagnostics for config, runtime tools, and credential-free provider
  readiness.
- An explicit, read-only `forge doctor --preflight gemini` readiness call with a short-lived,
  version-bound, credential-free proof for Gemini's status-API gap.
- User-owned convention profiles with initialize, import, list, select, inspect, preview, validate,
  and edit workflows plus ordered source hashes.
- Provider-neutral `safe`, `plan`, and explicitly consented `unsafe` execution modes.
- Prompt-free `.forge/progress.json` phase evidence and `--resume` with execution-contract
  validation.
- Stable provider failure classes and redacted recovery guidance.
- Inspectable `.forge/verification.json` reports with generated-metadata-aware Python checks and
  bounded configurable health endpoints/timeouts.
- A rewritten Forge operator skill with native validation and recorded RED/GREEN forward tests.
- Ubuntu/macOS CI coverage on Python 3.12 and 3.13, plus documentation-link validation.

### Changed

- Provider-default or auto model selection is now the default; explicit model overrides remain an
  advanced provider-validated option.
- Live scaffolds now show workspace, providers, model behavior, approval mode, provider-call count,
  a qualified duration range, execution strategy, verification limits, and cost possibility before
  execution.
- Convention precedence is bundled defaults, selected profile, user-wide override, then
  project-local override.
- Config writes are atomic and user-only; invalid config is preserved for recovery.
- The dashboard reports `Project Ready` only when required verification actually passes.
- Generated-project verification no longer inherits Forge's active virtual environment and uses a
  bounded 60-second command timeout for realistic cold checks.
- The built wheel and source distribution include the Forge operator skill.

### Security

- Removed implicit provider bypass/yolo execution from normal runs. Blanket bypass now requires
  both `--approval-mode unsafe` and `--allow-unsafe`.
- Provider status, progress, failure output, logs, manifests, and verification evidence avoid
  credentials, account identity, private absolute paths, and unredacted provider output.
- Verification reports replace project and home paths with portable, non-identifying forms.

### Migration

- Unversioned v0.4.1 config remains readable and existing model overrides are preserved.
- Legacy `~/.forge/conventions.md` remains supported above the selected profile.
- v0.4.1 scaffolds remain replayable but cannot use phase resume retroactively because they lack
  `.forge/progress.json`.

See [the migration guide](docs/guides/migrating-from-0.4.1.md) for details.

## [0.4.1] - 2026-07-18

### Added

- Reproducible public-showcase evidence, a terminal demo script, and public-safety regression
  checks.
- Canonical project URLs in package metadata and release documentation.

### Changed

- The public distribution identity is now consistently `projectforge`; the installed command
  remains `forge`.
- Homebrew release automation now targets the canonical repository and tap.
- Public install documentation now uses the immutable `v0.4.1` release tag.

### Fixed

- Homebrew formula generation now requires the release archive checksum explicitly, preventing a
  version bump from silently reusing an older checksum.
- Removed stale showcase images that contained superseded branding or unverified output.

## [0.4.0] - 2026-03-23

### Added

- **Multi-agent orchestration**: `--agents` flag (or interactive "Execution mode" prompt) decomposes each scaffold phase into 2-6 focused subagent tasks that run in parallel, with dependency-aware scheduling and automatic reconciliation between phases.
- **Execution mode prompt**: Interactive questionnaire now asks users to choose between "Multi-agent" and "Standard" execution, shown in the review panel and editable before scaffolding.
- **Subagent activity feed**: Live progress display showing per-task status transitions, task descriptions, and timing during multi-agent execution.
- **Subagent results panel**: Post-phase summary showing completed/failed task counts with individual task timing.
- **Protocol layer**: `protocol.py` defines the ForgeAgent contract, AgentTask, AgentResult, DecompositionPlan, and ProgressEvent data structures for orchestration.
- **Backend adapters**: Claude Code, Gemini CLI, and Codex each have a dedicated adapter that handles prompt construction, planning prompt assembly, plan parsing, and command building.
- **Subprocess utilities module**: Extracted reusable output processing (ANSI stripping, noise filtering, semantic summarization, spinner rendering) from `runner.py` into `subprocess_utils.py` for shared use by adapters.
- **Per-subagent quality signals**: Quality tracking now records signals per subagent task, not just per phase.
- **Bundled conventions system**: Convention registry, compiler, and admin command (`forge conventions`) for managing structured convention bundles with language-specific sources.

### Changed

- Verbose output now defaults to on for the main `forge` command (`--quiet` to suppress); `evolve` and `replay` retain the previous default.
- `--agents/--no-agents` is now a tri-state flag so explicit `--no-agents` is not overridden by config.json settings.
- Plan validation rejects decomposition plans where `execution_order` doesn't cover all task IDs, preventing silent task drops from malformed LLM output.
- Dry-run planning (`--dry-run --agents`) uses a temporary directory when the project directory doesn't exist yet, producing a real decomposition preview instead of always falling back to single-task.
- Subagent prompts now include the full phase brief so individual tasks have complete context (CI config, design templates, auth details, etc.) alongside their specific assignment.

### Fixed

- Activity feed labels now show human-readable task descriptions instead of raw task IDs.
- Subagent summary replaced plain text output with a structured Rich panel.

## [0.3.0] - 2026-03-22

### Added

- `forge stats` with scaffold analytics and backend performance tracking.
- `forge evolve` for augmenting existing projects with additional capabilities.
- `forge check` for convention drift auditing, with `--fix` and `--export` support.
- `forge replay` with conventions snapshots and `--diff` support for rerunning past scaffolds.
- Quality memory and smart defaults so backend routing and answers improve over time.
- Signature moments in the scaffold flow, including completion sound, Forge badge, and project card output.

### Changed

- The scaffold experience now includes a richer dashboard with a phase timeline, activity feed, file tree, and post-run report card.
- Public docs, screenshots, diagrams, and Homebrew release automation were refreshed for the `0.3.0` release.

## [0.2.0] - 2026-03-20

### Added

- Backend readiness checks during setup so Forge can distinguish installed tools from backends that are actually ready to scaffold.
- A post-setup handoff screen on first run so new users can create a project now, review setup again, or exit cleanly.
- A review-and-edit screen before interactive scaffolding so users can revise their selections without restarting the whole flow.
- Focused tests for backend readiness, first-run handoff, review/edit behavior, and safer project-directory handling.

### Changed

- Interactive scaffolding now supports editing basics, design/media, integrations, and demo mode before generation starts.
- Existing target directories now offer safer choices: rename the project, overwrite the directory, or cancel.
- Setup now offers inline git identity configuration when `user.name` or `user.email` is missing.
- Setup and getting-started docs now reflect backend readiness, first-run handoff, and the review/edit scaffold flow.
- Routing now skips backends that are known to be installed but not authenticated instead of failing later during execution.

## [0.1.0] - 2026-03-20

### Added

- Interactive CLI built with Typer, Rich, and questionary for guided project scaffolding.
- Support for 7 stacks: Next.js, FastAPI, FastAPI + AI/LLM, Next.js + FastAPI monorepo, Python CLI, TypeScript npm Package, and Python Worker.
- AI backend routing with automatic fallback (Claude Code -> Gemini CLI -> Codex).
- Multi-phase parallel execution with live progress display.
- First-run setup wizard that detects installed AI CLIs, editors, git, and Docker.
- Non-interactive mode via CLI flags for CI and scripting use.
- Shared conventions loaded from `~/.forge/conventions.md` and injected into every scaffold prompt.
- Secret detection scanning on user-provided text.
- `CLAUDE.md` template injection into scaffolded projects.
- Design template system for brand-consistent scaffolds (e.g., `default-design-guide`).
- Auth provider selection (Clerk, NextAuth.js, Supabase Auth) for frontend stacks.
- CI workflow generation with configurable actions (lint, typecheck, unit-tests, etc.).
- Media asset import with named collection support.
- Post-scaffold verification that confirms generated projects boot correctly.
- Demo mode generating projects that run without real API keys.
- Shell tab completion for all flags.
- Scaffold history log at `~/.forge/scaffold.log`.
- Per-project `.forge/scaffold.json` manifest for provenance tracking.
- Post-scaffold hooks via `~/.forge/hooks/post-scaffold.sh`.
- Prompt export (`--export`) and dry-run (`--dry-run`) modes.
- Homebrew formula and tap for macOS installation.
- pipx support for isolated global installs.
- MIT license.

[Unreleased]: https://github.com/Schramm2/projectforge/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/Schramm2/projectforge/releases/tag/v0.6.0
[0.5.1]: https://github.com/Schramm2/projectforge/releases/tag/v0.5.1
[0.5.0]: https://github.com/Schramm2/projectforge/releases/tag/v0.5.0
[0.4.1]: https://github.com/Schramm2/projectforge/releases/tag/v0.4.1
[0.4.0]: https://github.com/Schramm2/projectforge/releases/tag/v0.4.0
[0.3.0]: https://github.com/Schramm2/projectforge/releases/tag/v0.3.0
[0.2.0]: https://github.com/Schramm2/projectforge/releases/tag/v0.2.0
[0.1.0]: https://github.com/Schramm2/projectforge/releases/tag/v0.1.0
