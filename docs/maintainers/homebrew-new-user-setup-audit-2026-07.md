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

Implementation status: **Resolved in ProjectForge v0.7.1**

Distribution status: **Published and clean-install verified on 2026-07-19**

| Finding | Resolution |
| --- | --- |
| NU-01 | `MEDIA_DIR` now resolves from `FORGE_DIR`, so the default is `~/.forge/media` and isolated runs use `$FORGE_HOME/media`. The global pytest fixture also redirects media storage away from the developer's home. |
| NU-02 | `doctor` now calls the same CLI-or-macOS-application detector used by setup. Its JSON `editors` object remains a stable command-to-boolean mapping. |
| NU-03 | Troubleshooting and browsable docs now show how to leave a source virtual environment and refresh command lookup without disabling Homebrew checks. |
| NU-04 | Getting-started and browsable docs recommend a dedicated playground and explain the difference between a saved project directory and current-directory behavior. |
| NU-05 | Documentation now states that `doctor` is a subcommand. No compatibility alias was added. |
| NU-06 | No product change. Homebrew trust warnings remain under Homebrew's control. |

Verification completed on 2026-07-19:

- The two focused regression tests failed against the v0.7.0 behavior, then passed after the fix.
- 580 pytest tests passed.
- Ruff, the public-safety scan, documentation-link checks, operator-skill validation, and bundled
  convention validation passed.
- The wheel and source distribution built successfully and passed artifact inspection.
- An isolated install of the built wheel reported v0.7.0, completed a dry run, and resolved media
  under the supplied `FORGE_HOME`.
- A Homebrew-shaped Python 3.13.14 virtual environment loaded the built wheel, detected the VS Code
  and Antigravity macOS applications, and kept media under the isolated Forge home.
- Source `projectforge doctor` returned ready with the real saved config and reported both detected
  macOS applications.

Post-publication verification confirmed:

- GitHub published the immutable `v0.7.1` tag and release.
- PyPI published both v0.7.1 artifacts; clean uv and pipx installs exposed both command aliases.
- The published PyPI wheel kept media under `FORGE_HOME/media` and detected the supported macOS
  applications.
- The public Homebrew tap matched the repository formula. Upgrading from v0.7.0 to v0.7.1,
  `brew test`, version checks, user-owned media resolution, and editor diagnostics all passed.

## Live scaffold follow-up

A provider-backed `python-cli` scaffold was run from a dedicated playground through the
Homebrew-installed v0.7.1 command. This closed the original audit boundary that intentionally
stopped before provider execution.

The architecture phase completed through Claude. Codex then exited in 0.612 seconds because the
fresh target was not yet a Git repository and `codex exec` requires a trusted repository unless its
skip flag is supplied. `projectforge doctor --json` remained ready for all providers. Initializing
Git manually preserved the completed phase and allowed `--resume` to complete Codex tests and the
final Claude verification phase.

Forge reported `Project Ready`, and independent checks confirmed Ruff, formatting, strict MyPy,
20 passing tests with one intentional xfail, 97% coverage, and a working generated console command.
The independent handoff review also found that the README badge was added after the initial commit,
`uv.lock` was ignored, a documented pre-commit file was absent, and Forge's verification report did
not exercise the generated console entry point.

| ID | Severity | Follow-up finding | Correction in current source |
| --- | --- | --- | --- |
| NU-07 | High | Codex cannot enter a fresh target before Git exists. | Initialize an unborn `main` repository before any live provider phase; stop before model calls if Git cannot start. |
| NU-08 | Medium | Completion may commit before hooks, cards, and README badge injection, leaving a dirty handoff. | Write final artifacts first, then commit all outstanding generated changes even when a provider already committed. |
| NU-09 | Medium | Python verification can report ready without exercising the generated console command. | Derive bounded `uv run <script> --help` checks from `[project.scripts]` and record them as smoke evidence. |
| NU-10 | Medium | Required Python handoff files can be absent or ignored while lint, typecheck, and tests pass. | Fail readiness when required pre-commit configuration is missing, `uv.lock` is absent, or direct lockfile ignore rules prevent committing it. |
| NU-11 | Low | The original Codex failure was classified as unknown. | Classify trusted-directory and `--skip-git-repo-check` failures as workspace permission failures. |

Follow-up implementation status: **Implemented in current source; release pending**

Current-source verification completed with 591 passing tests, Ruff, public-safety and documentation
checks, skill and convention validation, D2 rendering, and successful wheel/source artifact
inspection. A zero-model-call installed-wheel journey used a deterministic provider shim to confirm
that the provider entered an unborn `main` repository, local Forge state was excluded, all phases
completed, the README badge was committed, and the final working tree was clean.

The final Claude phase took 1,072 seconds but exited successfully within Forge's documented
30-minute phase timeout and preflight's 6–45 minute planning range. This is latency evidence, not a
correctness failure; no shorter timeout was introduced from one successful sample.
