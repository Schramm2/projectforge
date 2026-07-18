# Production Readiness Plan

Status date: 2026-07-18
Target branch: `feat/production-readiness`
Starting point: `main` at `1691b2d` (`v0.4.1`)
Governing objective: the Codex goal attachment for this production-readiness run

This is the durable, resume-safe checklist for the next ProjectForge release. A checked item means
the stated evidence exists; it does not mean a nearby or broader claim is implied. Update the
evidence notes and remaining blockers whenever work changes their status.

## Evidence rules

- [x] Keep implementation work test-first: record the failing behavior, make the smallest change,
  and rerun the same test.
- [x] Treat official provider documentation and version-specific runtime output as the only sources
  for provider behavior.
- [x] Keep account identity, credentials, private paths, and credential-shaped values out of docs,
  tests, fixtures, logs, screenshots, and release artifacts.
- [x] Label live evidence as live, partial, unavailable, or blocked. A mock or help screen is not a
  live provider call.
- [ ] Publish only after every release gate passes and the required external credentials and hosted
  workflow permissions are confirmed.

## Baseline inventory

- [x] Read the active global and repository `AGENTS.md` chain.
- [x] Read architecture, release workflow, package metadata, CI, provider adapters, setup,
  conventions, verification/dashboard, release evidence, and the shipped skill.
- [x] Confirm a clean starting worktree and create `feat/production-readiness` from synchronized
  `main`.
- [x] Confirm hosted default branch `main`, current release `v0.4.1`, CI workflow, and Homebrew
  release workflow.
- [x] Record initial provider documentation and runtime evidence in
  `docs/maintainers/provider-compatibility.md`.
- [x] Run and record the pre-change safety, lint, test, build, help, and dry-run baselines.

Baseline evidence: safety scan passed across 170 files; Ruff passed; 413 tests passed; wheel and
sdist built; root/admin/evolve/replay help rendered; and the documented FastAPI dry run completed
without provider execution.

Baseline gaps already proven:

- Every normal provider invocation currently selects a blanket bypass/yolo mode.
- Gemini `--version` success is currently misreported as authenticated readiness.
- Setup hardcodes volatile model IDs and persists an explicit model even when the provider default
  should be used.
- Ordinary stack scaffolds compile bundled conventions without composing a normal user-wide layer.
- Convention source order and hashes are not exposed by dry runs or manifests.
- Config writes are non-atomic and corrupted config has no recovery copy.
- The showcase records a dashboard false negative against independently passing checks.
- CI covers only Ubuntu/Python 3.12.
- The shipped skill frontmatter summarizes workflow, hardcodes v0.4.1 details, duplicates CLI
  reference, and carries package README/CHANGELOG sediment.

## Provider compatibility and doctor

- [x] Add a reusable provider capability/readiness model with explicit installation,
  authentication, readiness, version, model behavior, permission support, and repair guidance.
- [x] Implement `forge doctor` with polished human output.
- [x] Implement `forge doctor --json` with stable, secret-free machine-readable output.
- [x] Report Python, Forge, Git, editor, Docker, and all supported providers.
- [x] Use documented Claude and Codex status commands and exit behavior.
- [x] Report Gemini authentication as unknown/preflight-required unless a safe prompt preflight was
  explicitly run; never infer authentication from installation or `--version`.
- [x] Classify missing binary, unauthenticated, unavailable model, quota/rate limit, network,
  permission denial, timeout, and unknown failures with provider-specific repair steps.
- [x] Ensure one authenticated provider is sufficient and optional missing providers do not block.
- [x] Add unit and journey tests for fresh install, no-provider, logged-out, one-provider, and
  multiple-provider states.

## Setup, config, and models

- [x] Make setup guide install -> authenticate -> recheck without reading or persisting provider
  credentials.
- [x] Default model selection to provider default/auto; preserve explicit model overrides as an
  advanced option.
- [x] Validate explicit aliases where the provider exposes stable validation; otherwise label the
  override as provider-validated at execution time.
- [x] Make config writes atomic and preserve a recoverable corrupted copy.
- [x] Validate config shape and migrate v0.4.1 model preferences safely.
- [x] Add config corruption, atomicity, migration, and sensitive-value rejection tests.

## Conventions and reproducibility

- [x] Define deterministic precedence: bundled defaults -> selected user profile -> user-wide
  override -> project-local override.
- [x] Support profiles under `~/.forge` with a stable default profile.
- [x] Add friendly initialize, import, edit, select, inspect, preview, and validate commands.
- [x] Safely import Markdown instruction surfaces including `AGENTS.md`, `CLAUDE.md`, and ordinary
  convention files.
- [x] Support documented placeholders and reject unknown or secret-bearing values.
- [x] Show exact source paths, order, warnings, and hashes in dry runs and live preflight.
- [x] Snapshot effective conventions plus source metadata for replay.
- [x] Preserve replay compatibility and document v0.4.1 migration behavior.
- [x] Add regression coverage for user-wide conventions in an ordinary stack plus project
  precedence, profiles, placeholders, validation, hashes, snapshots, replay, and privacy.

## Safe provider execution

- [x] Add a provider-neutral approval mode interface with safe defaults and an explicitly named
  unsafe/unattended mode.
- [x] Require informed consent before dangerous Claude bypass, Codex no-sandbox bypass, or Gemini
  yolo execution.
- [x] Map safe modes to current provider capabilities and scope writes to the target workspace.
- [x] Print target workspace, selected provider, model behavior, and effective mode before running.
- [x] Refuse combinations where bounded execution cannot be guaranteed without explicit consent.
- [x] Share command construction between standard and orchestrated adapters.
- [x] Add tests for defaults, migration, consent, non-interactive runs, boundaries, redaction, and
  unsupported combinations.
- [x] Document provider trust boundaries, data sent, local writes, recovery, and the unsafe escape
  hatch in user language.

## Reliability, verification, and recovery

- [x] Reproduce the showcase dashboard false negative as a failing test.
- [x] Make stack verification commands reflect the generated project layout and actual metadata.
- [x] Record commands, working directories, timeouts, skipped reasons, exit codes, and concise
  remediation in verification reports.
- [x] Make health probes configurable and report every attempted endpoint and timeout honestly.
- [x] Ensure dashboard status and independently executed checks agree.
- [x] Preserve partial project output after provider failure and write phase progress for resume.
- [x] Add actionable retry/resume/rerun guidance without overwriting successful work.
- [x] State duration, provider-call count, cost possibility, quick/thorough behavior, and demo-mode
  limits before execution.
- [x] Redact prompts, progress, errors, logs, manifests, analytics, and diagnostics.
- [x] Add failed-phase, timeout, quota, permission, redaction, resume, verification, and successful
  scaffold acceptance coverage.

## Shipped skill RED -> GREEN

- [x] Read `writing-agent-instructions`, `skill-creator`, `superpowers:writing-skills`,
  `superpowers:test-driven-development`, `writing-great-skills`, its glossary, and the skill testing
  reference completely.
- [x] Record realistic no-guidance and current-skill RED scenarios without desired-answer leakage.
- [x] Rewrite frontmatter as a compact capability/trigger routing pointer with no workflow summary.
- [x] Keep the ordered core and completion criteria in `SKILL.md`; move branch-heavy reference one
  level down behind precise context pointers.
- [x] Remove stale version claims, duplicated CLI reference, no-ops, conflicting owners, README,
  and CHANGELOG sediment.
- [x] Make the skill discover local/global Forge safely and consult live `--help` and `doctor`.
- [x] Route preview, live, audit, evolve, and replay branches while preserving approval and privacy
  boundaries.
- [x] Generate aligned `agents/openai.yaml` using current creator guidance.
- [x] Run the native validator, frontmatter/package checks, metadata readback, links/paths, and
  fresh-context GREEN forward tests.

## Documentation, packaging, and CI

- [x] Update README and user docs for install, provider auth, conventions, preview, approval,
  scaffold, verification, troubleshooting, v0.4.1 migration, and uninstall.
- [x] Add concise provider/support and security/privacy documentation with official links.
- [x] Remove stale or contradictory commands and make volatile provider facts link-only.
- [x] Verify every documented command against current `--help`.
- [x] Verify internal links and practical official external links.
- [x] Expand CI to the supported Python and OS matrix or narrow the documented support claim.
- [x] Inspect wheel/sdist contents, metadata, bundled conventions, and skill packaging.
- [x] Test isolated source and wheel installs.

## Release gates

- [x] `uv run python scripts/scan_safety.py`
- [x] `uv run ruff check src/ubundiforge tests`
- [x] `uv run pytest`
- [x] `uv build`
- [x] Documented dry-run smoke test
- [x] Clean wheel and sdist inspection
- [x] Isolated wheel and immutable archive installation
- [x] Skill validation and behavioral tests
- [x] All new doctor/onboarding/provider/conventions/security/verification acceptance tests
- [x] Realistic isolated Claude, Codex, and Gemini probes with evidence classification
- [x] At least one authenticated end-to-end scaffold plus independent verification; see
  [the evidence record](production-readiness-evidence.md).
- [x] Final security/privacy, changed-files, docs, package, and temporary-artifact review

## Version, PR, publication, and immutable verification

- [x] Choose the next semantic version from compatibility and maturity evidence; prefer a pre-1.0
  minor release unless all 1.0 claims are proven.
- [x] Update version sources, classifiers, changelog, migration guide, release notes, formula inputs,
  and immutable install references consistently.
- [x] Make intentional scoped commits on `feat/production-readiness`.
- [x] Push the branch and open a ready PR.
- [x] Wait for CI and resolve every failure.
- [x] Merge through the hosted workflow only after required evidence and authorization gates pass.
- [x] Verify the release workflow creates the tag and GitHub release and the Homebrew tap is
  synchronized. The first cross-repository checkout failed; tap PR #3 completed the update and a
  hardened sync-only run then verified an exact no-op match.
- [x] Verify release notes and all hosted workflows, including the successful sync-only recovery.
- [x] Verify clean `uv tool install` from the immutable tag.
- [x] Verify clean `brew install schramm2/tap/projectforge`, `brew test`, version, help, and doctor.
- [x] Verify a release-archive dry run.

## Current external evidence status

| Provider/channel | Status | Evidence or blocker |
| --- | --- | --- |
| Claude Code | Live | v2.1.214 installed and authenticated; safe three-phase scaffold, targeted repair, resume, and independent checks completed |
| Codex CLI | Partial | v0.144.0 installed and authenticated; official latest v0.144.5 version/help surface passed in an isolated npm probe; authenticated bounded-write evidence remains |
| Gemini CLI | Unavailable for live use | Official v0.51.0 version/help surface passed through the no-install route; no global binary, deterministic auth status, authenticated preflight, or model call is available |
| GitHub release | Released | v0.5.0 is tagged, published, and installs from its immutable archive |
| Homebrew tap | Released | v0.5.0 formula matches the generated main-repo formula and passes source install plus `brew test` |

## Stop-before-publish blockers

Stop before publication if any of these remain unresolved: no authenticated end-to-end scaffold,
missing release/tap credentials, branch protection or CI failures, unsafe provider execution that
cannot be bounded, an unresolved compatibility/version decision, or unavailable external
infrastructure. Record the exact missing evidence rather than weakening a claim.

No blocker remains for the published v0.5.0 release. The stored `HOMEBREW_TAP_TOKEN` is present but
cannot currently authenticate to the tap. A future new release is intentionally blocked before tag
creation until a maintainer replaces that credential outside this task. v0.5.0 was synchronized
through reviewed tap PR #3, and the hardened release workflow subsequently verified the public tap
as an exact generated-formula match in a successful, non-mutating sync-only run.
