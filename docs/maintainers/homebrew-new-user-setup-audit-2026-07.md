# Homebrew new-user setup audit — July 2026

ProjectForge v0.7.0 installs correctly through Homebrew and reaches a runnable state after setup.
The first clean user journey also exposed two product defects: media collections resolve inside the
Homebrew Cellar, and `doctor` disagrees with setup about macOS application availability. This audit
records the full path before those defects are fixed.

## Audit boundary

| Item | Value |
| --- | --- |
| Evidence date | 2026-07-19 |
| Release under test | ProjectForge v0.7.0 |
| Install route | `brew install schramm2/tap/projectforge` |
| Host | macOS on Apple Silicon |
| Homebrew runtime | Python 3.13.14 |
| Test workspace | A dedicated empty directory outside the ProjectForge source checkout |
| Provider calls | None; setup and `doctor` readiness checks only |
| Live scaffold | Not run during this audit |

The evidence below omits the local username, Git identity, provider account identity, and absolute
home-directory paths. Provider readiness is recorded only as a boolean outcome and a public CLI
version.

## Observed journey

### Install and command resolution

1. The first Homebrew invocation downloaded and verified the formula and all Python resources, then
   was interrupted before installation completed.
2. Repeating the same command completed successfully. Homebrew installed and linked
   `projectforge 0.7.0`.
3. Homebrew warned that an active source-checkout virtual environment shadowed both installed
   commands. Deactivating that environment and refreshing shell command lookup resolved the
   warning.
4. From the dedicated playground, `which projectforge` resolved to
   `/opt/homebrew/bin/projectforge`.
5. The warnings about untrusted third-party taps concerned unrelated tools. They did not block or
   weaken the ProjectForge installation.

### First-run setup

| Step | Observed result | Assessment |
| --- | --- | --- |
| AI assistants | Claude Code, Antigravity, and Codex installed and ready | Passed |
| Backend routing | Specialist routing assigned architecture/backend, frontend, and test work | Passed |
| Models | Provider-default model behavior retained for all providers | Passed |
| Editors | VS Code and Antigravity applications detected; VS Code selected | Passed with diagnostic inconsistency |
| Git | Git and an existing global identity detected | Passed |
| Docker | Docker detected | Passed |
| Project directory | Blank value retained; projects follow the directory where Forge is invoked | Valid, but easy to misuse |
| Conventions | Bundled defaults selected | Passed |
| Media | Empty media folder reported inside the Homebrew Cellar | Failed ownership boundary |
| Persistence | `~/.forge/config.json` created with user-only file permissions | Passed |

### Doctor

`projectforge doctor` returned a ready overall status. Configuration, Python, Git, Docker, and all
three providers passed. The attempted `projectforge --doctor` command failed because `doctor` is a
subcommand, not a root option; the documented `projectforge doctor` form worked.

The human report said no editor CLI was on `PATH`, even though setup had detected macOS applications
and selected VS Code. Runtime editor opening already has a macOS application fallback, so the
warning did not describe the actual capability.

## Findings

| ID | Severity | Finding | Required correction |
| --- | --- | --- | --- |
| NU-01 | High | `MEDIA_DIR` derives from the installed package path. Homebrew therefore advertises a versioned Cellar directory for user-owned assets. An upgrade or uninstall can remove it. | Resolve media collections under `FORGE_HOME/media`, defaulting to `~/.forge/media`, and update tests and docs. |
| NU-02 | Medium | Setup treats a macOS `.app` bundle as an available editor, while `doctor` checks only executable names on `PATH`. | Make `doctor` use the same CLI-or-application availability rule as setup. Preserve the existing JSON shape. |
| NU-03 | Medium | Homebrew explains source-virtualenv command shadowing, but ProjectForge troubleshooting does not give the short recovery sequence. | Document `deactivate`, shell command refresh, and clean command-path verification. |
| NU-04 | Low | Leaving `projects_dir` blank is valid but makes the target depend on the invocation directory. A user testing from the source checkout could scaffold into the wrong parent. | Add a dedicated-playground recommendation while preserving the current flexible behavior. |
| NU-05 | Informational | `projectforge --doctor` is invalid because `doctor` is a subcommand. | Keep the command model; use the exact subcommand form consistently in onboarding examples. |
| NU-06 | Informational | Homebrew reported unrelated untrusted taps. | No ProjectForge change. Do not advise users to disable Homebrew trust checks. |

## Controls that passed

- Homebrew linked both `projectforge` and the `forge` compatibility alias.
- Both installed commands reported v0.7.0 from a clean `PATH`.
- `brew linkage --test projectforge` passed.
- `brew test schramm2/tap/projectforge` passed.
- The installed wheel metadata reported `matt-projectforge 0.7.0` and Python 3.12 or newer.
- Bundled conventions and `skills/forge-scaffold/SKILL.md` were present.
- A zero-provider-call dry run completed through the installed Homebrew command.
- `projectforge doctor --json` returned `ready` after setup.
- `~/.forge/config.json` used mode `0600` and contained no model override.

## Fix acceptance criteria

- A regression test fails if media storage resolves anywhere outside `FORGE_HOME/media`.
- Tests isolate media storage from the developer's real home directory.
- A macOS application without a matching CLI is reported as an available editor by setup and
  `doctor`.
- The human doctor report no longer tells a user with a supported macOS application to rerun setup.
- Configuration, troubleshooting, and browsable site documentation name the user-owned media path.
- Getting-started guidance gives new users a dedicated playground option without changing
  current-directory semantics.
- Focused regressions, the full test suite, lint, safety, docs, package inspection, and a Homebrew-
  shaped install smoke test pass.

## Resolution record

Status: **Open**

Implementation and verification evidence will be added here after the fixes pass.
