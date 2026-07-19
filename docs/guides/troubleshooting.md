# Troubleshooting

This guide documents ProjectForge v0.7.1, including the Antigravity provider and privacy-safe
failure handling. Older releases retain their own bundled troubleshooting guidance.

Start with the credential-free diagnostic:

```bash
forge doctor
forge doctor --json
```

The human report explains repair actions. JSON is deterministic for automation and returns zero
only when config is valid and at least one provider is verifiably ready.

## `forge: command not found`

Check the install route:

- Current checkout: run `uv sync --dev`, then use `./forge` from the repository root.
- PyPI/uv or pipx package: run `uv tool list` or `pipx list`, then reinstall
  `matt-projectforge` if needed.
- Published GitHub archive: run `uv tool list`, then reinstall the intended immutable release.
- Homebrew: run `brew list projectforge` and `brew info schramm2/tap/projectforge`.

Current source installs both `projectforge` (preferred) and `forge` (compatibility). If Foundry's
Ethereum CLI already owns `forge` on PATH, run `projectforge` or inspect `command -v forge` and
`command -v projectforge`. Follow PATH guidance printed by uv, pipx, or Homebrew.

## Homebrew command is shadowed by a virtual environment

A source checkout installed into an active virtual environment can appear before Homebrew on
`PATH`. Homebrew reports this as a shadowed executable. Leave the environment, refresh shell
command lookup, and verify the packaged command from a directory outside the checkout:

```bash
deactivate
rehash  # zsh; use `hash -r` in bash
cd ~/Projects/forge-playground
command -v projectforge
projectforge --version
```

The expected Homebrew command is `/opt/homebrew/bin/projectforge` on Apple Silicon or
`/usr/local/bin/projectforge` on Intel macOS. Do not delete the source environment merely to change
command precedence.

## Provider is missing or needs login

Use the provider's current official installation guide:

- [Claude Code](https://code.claude.com/docs/en/setup), then `claude auth login`.
- [Codex CLI](https://github.com/openai/codex), then `codex login`.
- [Google Antigravity CLI](https://antigravity.google/docs/cli-install), then run `agy` and complete
  Google Sign-In.

Then rerun `forge doctor`. Forge never asks you to paste a credential.

## Antigravity needs Google Sign-In

Forge uses `agy models` to verify an existing Antigravity session without sending a model prompt.
If `forge doctor` reports `needs_login`:

```bash
agy
# Complete Google Sign-In, then leave the TUI with /exit.
forge doctor
```

On SSH, `agy` prints an authorization URL. Open it on a local device, sign in, and paste the
returned code into the remote terminal. Credentials remain in Antigravity's system-keyring
integration. Forge never asks for or stores the code, token, catalog output, or account identity.

If `forge doctor` reports `check_inconclusive`, confirm connectivity and keyring access, then run
`agy models` directly. A successful command prints available model display names; a missing session
prints a sign-in instruction. See Google's
[Antigravity troubleshooting guide](https://antigravity.google/docs/cli-troubleshooting) for PATH,
keyring, and SSH-specific recovery.

## Migrating from Gemini CLI

Gemini CLI is no longer a supported Forge backend. Install Antigravity, authenticate as above, and
use `--use antigravity`. Forge migrates saved `gemini` backend entries to `antigravity` in memory,
but drops old Gemini model overrides so Antigravity can select a current supported default. Running
`--setup` writes a fresh provider selection.

## Config is corrupted

Forge preserves invalid config as `~/.forge/config.json.corrupt-<timestamp>` when possible and
continues with safe defaults. Run:

```bash
forge --setup
forge doctor
```

Review the recovery copy locally before removing it. Unknown keys and invalid model/backend values
are rejected; do not put provider credentials in Forge config.

## Provider phase fails

Forge classifies missing binary, authentication, unavailable model, quota/rate limit, network,
permission, timeout, and unknown failures. Preserve the partial project and `.forge/progress.json`.

Current source classifies provider output transiently but does not echo or persist the captured
provider tail. The displayed category and remediation are intentionally bounded. If those are not
enough, run the provider-owned diagnostic named by `forge doctor` locally; review its output on
your machine rather than attaching it to a public issue.

1. Follow the redacted remediation shown for the category.
2. Rerun `forge doctor` for install/auth/network readiness when applicable.
3. Repeat the original scaffold command with `--resume`.

Resume rejects a different name, stack, routing, prompt hash, or approval mode and skips completed
phases. Do not delete successful phase output or rerun the entire scaffold blindly.

For an explicit model failure, remove `--model` to return to the provider default or choose a value
the provider supports. Forge does not maintain a volatile model catalog.

## Permission or sandbox failure

Keep `--approval-mode safe`. Confirm the target workspace is correct and adjust only the provider's
scoped workspace policy. Do not jump to unsafe mode as a general fix.

`--approval-mode unsafe --allow-unsafe` removes provider approval or sandbox boundaries. It is for
an externally isolated environment and explicit user intent, not routine recovery.

## Resume contract differs

Repeat the original flags and restore the same effective convention sources. `forge conventions
inspect --stack <stack> --json` shows current source hashes. If you intentionally changed the
brief, conventions, routing, model, or approval mode, choose a new target rather than mixing
contracts.

Scaffolds created by 0.4.1 have no phase ledger and cannot be resumed retroactively.

## Verification fails after generation

Open `.forge/verification.json` and find the first required failure. Run its recorded command from
its recorded project-relative working directory. The report includes startup/request timeouts,
exit, attempted endpoints, redacted detail, and remediation.

Do not interpret a successful provider exit as a verified project. The dashboard reports
`Project Ready` only when required checks pass.

If health probing uses the wrong project path or timing, declare bounded settings in the generated
`pyproject.toml` as described in [Configuration](configuration.md), then rerun the recorded local
server/check flow.

## Existing target directory

For a new scaffold, interactive Forge offers rename, confirmed overwrite, or cancel. Use
`--resume` only when the target contains matching `.forge/progress.json` evidence. Never point an
automated run at a non-empty unrelated directory.

## Post-scaffold hook fails

Check that `~/.forge/hooks/post-scaffold.sh` exists, is executable, and finishes within 60 seconds.
Run it manually only after reviewing it as user-authored shell code. Hook output can contain data
outside Forge's provider redaction boundary.

## Shell completion is stale

Regenerate it with:

```bash
forge --install-completion
```

Start a new shell after installation.

## Still blocked

Check [Security and Privacy](security-privacy.md), then open a
[GitHub issue](https://github.com/Schramm2/projectforge/issues) with Forge/provider versions,
operating system, approval mode, minimal reproduction steps, and redacted evidence. Do not attach
credentials, `.env` content, raw prompts, provider identity, or convention snapshots.
