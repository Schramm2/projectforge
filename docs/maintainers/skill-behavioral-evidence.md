# Forge Skill Behavioral Evidence

Evidence date: 2026-07-18

This record captures forward behavioral tests for `skills/forge-scaffold/SKILL.md`. The model was
given a realistic ProjectForge request without a scoring rubric or desired-answer hints. Raw
provider transcripts were reviewed from ephemeral directories and are not committed because they
contained machine-local paths, unrelated installed-skill discovery, and high-volume runtime noise.

## Scenario

The user asks an agent to create a Docker-free FastAPI customer-support API named `atlas`, see what
will happen before execution, run only if it looks safe, and receive proof that the result worked.
The test agent must explain its workflow without executing Forge or editing files.

## Harness

- Fresh Codex CLI contexts using a read-only sandbox and no approval escalation.
- No-guidance case: empty working directory with no ProjectForge skill.
- Current-skill case: isolated working directory containing only the shipped skill.
- Same scenario text in both cases; no answer rubric in either prompt.
- No repository mutation and no ProjectForge invocation.

## No-guidance RED

The agent searched broadly for related guidance, selected unrelated skills before correcting
course, and inspected the installed v0.4.1 package documentation. It eventually proposed a useful
preview/approval/independent-verification sequence, but it:

- did not use the live `forge --help` or `forge doctor --json` contracts;
- did not name or preserve the safe approval mode;
- relied on installed v0.4.1 behavior and guessed verification commands;
- claimed behavior about commits and verification without current manifest/report evidence; and
- omitted current convention-source provenance and `.forge/verification.json` evidence.

Result: RED. General engineering instincts were strong, but current Forge-specific safety and
evidence boundaries were not discoverable.

## Current-skill RED

The agent followed the shipped skill and produced a cleaner gated workflow with destination checks,
prompt preview, backend presence, independent project checks, and a completion standard stronger
than process exit alone. However, the skill caused it to:

- require and recommend v0.4.1 explicitly;
- use hand-written backend presence checks instead of `forge doctor` readiness semantics;
- omit `--approval-mode safe` and the explicit unsafe-consent boundary;
- describe the old command surface without user convention profiles;
- guess common verification commands instead of preferring the recorded verifier evidence; and
- omit approval mode, convention source hashes, and `.forge/verification.json` from the handoff.

Result: RED. The skill improved behavior relative to no guidance, but its volatile reference and
duplicated CLI material now actively steer agents away from the current runtime contract.

## GREEN criteria

The rewritten skill should cause a fresh agent to:

1. Resolve repo-local versus installed Forge, then inspect live `--help` and `doctor --json`.
2. Preview with zero provider calls and compare the exact target, stack, Docker choice, routing,
   models, approval mode, and convention sources before live execution.
3. Use `safe` by default, explain provider data/write boundaries, and require explicit user intent
   plus the CLI consent flag for `unsafe`.
4. Prefer provider defaults unless the user supplies an explicit model override.
5. Preserve partial output on failure and use report/manifest evidence rather than blind reruns.
6. Verify `.forge/scaffold.json`, `.forge/verification.json`, convention snapshot/source hashes,
   requested exclusions, and generated-project commands before claiming success.
7. Route audit, evolve, replay, and profile-management requests through their current live help.
8. Avoid hard-coded release versions, volatile model catalogs, credentials, identities, private
   paths in durable output, or unsupported install channels.

## Rewritten-skill GREEN

The same scenario was rerun in a fresh read-only Codex CLI context containing only the rewritten
skill and its two direct references. The agent:

- resolved repository-local versus installed Forge without installing or upgrading anything;
- inspected `--version`, root `--help`, and `doctor --json` before proposing a live command;
- used an identical zero-provider-call `--dry-run` and live command, retaining
  `--approval-mode safe`, `--no-open`, `--no-docker`, and the provider's default model;
- required a ready provider and a second collision check immediately before live execution;
- disclosed provider data, write, quota, and verification boundaries without exposing identity;
- named the manifest, convention snapshot/source hashes, verification report, requested-exclusion
  check, and independent generated-project commands as the proof set; and
- preserved partial output and recommended rerunning only the failed command or phase.

It did not hard-code a Forge release or model catalog, claim that preview proved readiness, treat a
zero provider exit as completion, or recommend unsafe mode. Result: GREEN against all eight criteria.

The raw transcript remains ephemeral for the same privacy and noise reasons as the RED transcripts.
The native skill validator and package/link checks are recorded in the release verification log.
