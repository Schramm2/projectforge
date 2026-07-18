# Troubleshooting

Start with the credential-free diagnostic:

```bash
forge doctor
forge doctor --json
```

The human report explains repair actions. JSON is deterministic for automation and returns zero
only when config is valid and at least one provider is verifiably ready.

## `forge: command not found`

Check the install route:

- GitHub/uv: run `uv tool list`, then reinstall the immutable release if needed.
- Homebrew: run `brew list projectforge` and `brew info schramm2/tap/projectforge`.
- Repository checkout: run `uv sync --dev`, then use `./forge` from the repository root.

ProjectForge is not published to PyPI. Follow any PATH guidance printed by `uv tool install` or
Homebrew rather than installing a similarly named package from another channel.

## Provider is missing or needs login

Use the provider's current official installation guide:

- [Claude Code](https://code.claude.com/docs/en/setup), then `claude auth login`.
- [Codex CLI](https://github.com/openai/codex), then `codex login`.
- [Gemini CLI](https://geminicli.com/docs/get-started/installation/) and its
  [authentication guide](https://geminicli.com/docs/get-started/authentication/).

Then rerun `forge doctor`. Forge never asks you to paste a credential.

## Gemini says `preflight_required`

Gemini CLI does not expose a deterministic credential-status command. Forge therefore does not
mark it ready from installation or `--version`. Authenticate through Gemini's own flow, then run:

```bash
forge doctor --preflight gemini
```

This explicit command makes one read-only model call in a temporary sandbox and may consume quota.
On success, Forge stores only the CLI version and verification timestamp for 24 hours in
`~/.forge/provider-preflight.json`; it never stores provider output, identity, or credentials. Use
another ready provider if you do not want a model call.

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
