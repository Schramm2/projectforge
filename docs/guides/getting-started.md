# Getting Started

## 1. Install ProjectForge

ProjectForge supports Python 3.12 and 3.13 on macOS and Linux. Install `uv` from its
[official guide](https://docs.astral.sh/uv/getting-started/installation/), then install the
immutable release:

```bash
uv tool install https://github.com/Schramm2/projectforge/archive/refs/tags/v0.4.1.tar.gz
forge --version
forge --help
```

Homebrew is also supported:

```bash
brew install schramm2/tap/projectforge
forge --version
```

ProjectForge is not published to PyPI. For repository development:

```bash
git clone https://github.com/Schramm2/projectforge.git
cd projectforge
uv sync --dev
./forge --version
```

## 2. Install and authenticate one provider

Choose at least one provider. Follow its current official installation and authentication guide:

- [Claude Code setup](https://code.claude.com/docs/en/setup), then `claude auth login`.
- [Codex CLI](https://github.com/openai/codex), then `codex login`.
- [Gemini CLI installation](https://geminicli.com/docs/get-started/installation/) and
  [authentication](https://geminicli.com/docs/get-started/authentication/).

Forge does not collect credentials or account identity. Confirm readiness without a model call:

```bash
forge doctor
forge doctor --json
```

One `ready` provider is enough. An installed Gemini CLI can remain `preflight_required` because the
provider exposes no deterministic credential-status command; installation alone is not readiness.

## 3. Preview with zero provider calls

```bash
forge --dry-run \
  --name hello-forge \
  --stack python-cli \
  --description "A tiny greeting CLI" \
  --no-docker \
  --no-open
```

`--dry-run` does not create a project, run a provider planner, or make a model call. Review target,
stack, options, routing, models, safe approval mode, convention source hashes, warnings, and prompt
content. Preview does not prove provider readiness or generated-project behavior.

## 4. Run the same scaffold safely

```bash
forge \
  --name hello-forge \
  --stack python-cli \
  --description "A tiny greeting CLI" \
  --no-docker \
  --approval-mode safe \
  --no-open \
  --verify
```

The preflight panel states the target workspace, provider and model behavior, remaining provider
calls, a qualified time range, execution strategy, demo/verification limits, and possible provider
quota or billing. Live generation sends the assembled brief, effective conventions, and selected
context to the chosen provider CLI. Safe mode keeps writes inside the provider's selected workspace
boundary; it still allows project edits and commands required to scaffold.

Demo mode is on by default so the generated project should start without real service credentials.
The provider CLI itself still requires authentication.

The interactive equivalent is simply:

```bash
forge
```

The first interactive run opens setup, then lets you create a project, revisit setup, or exit. The
questionnaire ends at a review screen before provider execution.

## 5. Read the evidence

After a successful run, inspect:

- `.forge/progress.json` for phase status, attempts, and durations;
- `.forge/scaffold.json` for routing, approval mode, models, and convention hashes;
- `.forge/conventions-snapshot.md` for exact replay input; and
- `.forge/verification.json` for commands, timeouts, exits, endpoints, and remediation.

`Project Ready` means required verification passed. `Project Created` means verification was not
run or was incomplete. Independently rerun recorded project commands when delivery confidence
matters.

## Failure recovery

If a provider phase fails, preserve the target. Fix the classified login, model, quota, network,
permission, or timeout problem and repeat the original command with `--resume`. Forge validates the
recorded contract and skips completed phases.

If a verification check fails, run the exact command and working directory recorded in
`.forge/verification.json`; do not regenerate a project just to hide a failed check.

See [Troubleshooting](troubleshooting.md) for provider-specific recovery.

## Upgrade and 0.4.1 migration

Read [Migrating from 0.4.1](migrating-from-0.4.1.md) for config normalization, conventions profile
precedence, safe provider modes, new manifests, and resume compatibility.

```bash
uv tool upgrade projectforge
# or
brew upgrade schramm2/tap/projectforge
```

## Uninstall

```bash
uv tool uninstall projectforge
# or
brew uninstall projectforge
```

Package removal does not delete user-owned files under `~/.forge/`. Move or back up that directory
separately before removing it if you want to retain profiles or local scaffold history.

## Next steps

- [Configuration](configuration.md) — profiles, precedence, config recovery, hooks, and evidence.
- [Stacks](stacks.md) — generated structures and commands.
- [Security and Privacy](security-privacy.md) — provider, workspace, local-data, and unsafe-mode
  boundaries.
- [Troubleshooting](troubleshooting.md) — diagnostic and recovery flows.
