# Getting Started

> This guide documents ProjectForge v0.7.1 with the Claude, Antigravity, and Codex provider set.
>
> Current source installs `projectforge` as the preferred collision-free command and keeps `forge`
> as a compatibility alias. Foundry also installs a command named `forge`; use `projectforge` when
> both products are installed.

![New ProjectForge user journey from installation to full use](../diagrams/forge-user-journey.svg)

The [new user journey](../diagrams/forge-user-journey.md) shows how these setup steps lead into preview, live generation, verification, recovery, and ongoing project commands.

## 1. Use the current source

ProjectForge supports Python 3.12 and 3.13 on macOS and Linux. Install `uv` from its
[official guide](https://docs.astral.sh/uv/getting-started/installation/), then install the current
checkout for the Antigravity-capable behavior documented here:

```bash
git clone https://github.com/Schramm2/projectforge.git
cd projectforge
uv sync --dev
./forge --version
./forge --help
```

Use `./forge` from the repository root anywhere the examples below show `forge`.

Install the published PyPI distribution or use Homebrew:

```bash
uv tool install matt-projectforge
# or: pipx install matt-projectforge
# or: brew install schramm2/tap/projectforge
```

PyPI required the distinct `matt-projectforge` distribution name because `projectforge` was too
similar to an existing project. All installation routes provide the preferred `projectforge`
command and the `forge` compatibility alias.

For a clean first run, use a dedicated parent directory rather than the ProjectForge source
checkout. Save this path during setup if every scaffold should use it; leave the setup value empty
only when projects should follow the directory where you invoke Forge.

```bash
mkdir -p ~/Projects/forge-playground
cd ~/Projects/forge-playground
projectforge --setup
projectforge doctor
```

`doctor` is a subcommand, so use `projectforge doctor`, not `projectforge --doctor`.

## 2. Install and authenticate one provider

Choose at least one provider. Follow its current official installation and authentication guide:

- [Claude Code setup](https://code.claude.com/docs/en/setup), then `claude auth login`.
- [Codex CLI](https://github.com/openai/codex), then `codex login`.
- [Google Antigravity CLI](https://antigravity.google/docs/cli-install), then run `agy` and
  complete Google Sign-In. On SSH, open the displayed authorization URL locally and paste the
  returned code into the terminal.

Forge does not collect credentials or account identity. Confirm readiness without a model call:

```bash
forge doctor
forge doctor --json
```

One `ready` provider is enough. Forge checks Antigravity with `agy models`, which confirms the
provider-owned session without sending a prompt, consuming model quota, or printing identity. If
Forge reports `needs_login`, run `agy`, finish sign-in, exit with `/exit`, and rerun `forge doctor`.

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
stack, options, routing, models, safe approval mode, convention source summary, warnings, and
prompt content. Add `--verbose` for full convention source paths and hashes. Preview does not prove
provider readiness or generated-project behavior.

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
CLI invocations, a numeric time range, the last local duration for the same stack, per-provider
quota context, a rough cost range, execution strategy, and demo/verification limits. Live
generation sends the assembled brief, effective conventions, and selected
context to the chosen provider CLI. Safe mode uses each provider's bounded execution controls.
Antigravity auto-accepts workspace edits and enables its terminal sandbox; print mode may deny
commands that are not already permitted by Antigravity's scoped policy.

Demo mode is on by default so the generated project should start without real service credentials.
The provider CLI itself still requires authentication.

The interactive equivalent is simply:

```bash
forge
```

The first interactive run opens setup, then lets you create a project, revisit setup, or exit.
During setup, choose Forge's bundled conventions, import nearby instruction files, or create a
reusable profile through a short interview.

The project questionnaire keeps reusable conventions separate from project context. It asks who
the project is for, what the first useful version should demonstrate, and which constraints matter.
If known Markdown files are present in the current folder, Forge lists them without reading their
content into the prompt. Only files you select are loaded, secret-scanned, and included. The review
screen shows the active brief and selected-file count before provider execution.

## 5. Read the evidence

After a successful run, inspect:

- `.forge/progress.json` for phase status, attempts, and durations;
- `.forge/scaffold.json` for routing, approval mode, models, and convention hashes;
- `.forge/conventions-snapshot.md` for exact convention replay input;
- `.forge/context-snapshot.md` for the approved brief and selected file content, when supplied; and
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
git pull --ff-only
uv sync --dev
```

For the published package, use `uv tool upgrade matt-projectforge` or
`brew upgrade schramm2/tap/projectforge` and follow that release's bundled documentation.

## Uninstall

For the current-source route, leave the repository environment and remove the checkout through
your normal file-management workflow. For a published package installation:

```bash
uv tool uninstall matt-projectforge
# or
brew uninstall projectforge
```

Removing the checkout or package does not delete user-owned files under `~/.forge/`. Move or back
up that directory separately if you want to retain profiles or local scaffold history.

## Next steps

- [Configuration](configuration.md) — profiles, precedence, config recovery, hooks, and evidence.
- [Stacks](stacks.md) — generated structures and commands.
- [Security and Privacy](security-privacy.md) — provider, workspace, local-data, and unsafe-mode
  boundaries.
- [Troubleshooting](troubleshooting.md) — diagnostic and recovery flows.
