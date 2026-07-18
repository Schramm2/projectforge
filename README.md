# ProjectForge

ProjectForge is a local CLI that turns a project brief and your conventions into a verified starter
repository through Claude Code, Codex CLI, or Gemini CLI.

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB)

Forge shows the complete prompt before execution, uses bounded provider workspace modes by default,
records convention provenance, preserves failed runs for resume, and separates “provider finished”
from “generated project verified.”

## What you get

- Interactive and flag-driven scaffolding for seven Python and TypeScript stacks.
- Zero-provider-call prompt previews with `--dry-run`.
- `forge doctor` readiness diagnostics without a model call or credential output; Gemini has a
  separate, opt-in readiness preflight.
- Provider-default models unless you deliberately request an override.
- Deterministic bundled, profile, user-wide, and project-local conventions with source hashes.
- Safe provider execution by default; blanket bypass requires two explicit unsafe flags.
- Atomic phase progress, failure classification, and `--resume` without rerunning completed phases.
- Metadata-aware install, lint, type-check, build, test, and health verification.
- Durable scaffold, convention, and verification evidence under the generated project's `.forge/`.

## Supported stacks

| Stack | Identifier | Aliases |
| --- | --- | --- |
| Next.js + React | `nextjs` | `next`, `react` |
| FastAPI | `fastapi` | `api` |
| FastAPI + AI/LLM | `fastapi-ai` | `ai`, `llm` |
| Next.js + FastAPI monorepo | `both` | `fullstack`, `monorepo` |
| Python CLI | `python-cli` | `cli`, `typer` |
| TypeScript package | `ts-package` | `npm-package`, `library` |
| Python worker | `python-worker` | `worker`, `service` |

See [the stack guide](docs/guides/stacks.md) for generated structures and commands.

## Requirements

- Python 3.12 or 3.13. CI covers both versions on Ubuntu and macOS.
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) for the GitHub install route.
- At least one installed and authenticated provider CLI for live generation. Preview does not need
  a provider.

## Install ProjectForge

Install the immutable v0.5.0 GitHub release:

```bash
uv tool install https://github.com/Schramm2/projectforge/archive/refs/tags/v0.5.0.tar.gz
forge --version
forge --help
```

Or install from the supported Homebrew tap:

```bash
brew install schramm2/tap/projectforge
forge --version
```

ProjectForge is not published to PyPI. The distribution and Homebrew formula are named
`projectforge`; the installed command is `forge`.

## Install and authenticate a provider

Provider credentials stay inside the provider's own CLI. Forge does not install a provider,
collect a token, or print account identity.

| Provider | Official setup | Provider-owned login | Forge readiness |
| --- | --- | --- | --- |
| Claude Code | [Install](https://code.claude.com/docs/en/setup) | `claude auth login` | Deterministic status check |
| Codex CLI | [Install](https://github.com/openai/codex) | `codex login` | Deterministic status check |
| Gemini CLI | [Install](https://geminicli.com/docs/get-started/installation/) | Follow its [authentication guide](https://geminicli.com/docs/get-started/authentication/) | May require an explicit provider preflight |

After provider login, run:

```bash
forge doctor
forge doctor --json
# Gemini only, after provider-owned authentication (one read-only model call):
forge doctor --preflight gemini
```

A live scaffold requires one provider reported as `ready`. Missing optional providers do not block
the run. An installed Gemini CLI remains `preflight_required` because it exposes no deterministic
credential-status command. Its explicit preflight runs in a temporary workspace with plan mode and
sandboxing, may consume quota, and stores only a version-bound readiness timestamp for 24 hours.

## Preview first

This command creates no project, starts no provider process, and makes no model call:

```bash
forge --dry-run \
  --name atlas \
  --stack fastapi \
  --description "Customer support API" \
  --no-docker \
  --no-open
```

Review the target, phase routing, provider-default versus overridden models, approval mode,
convention source order and hashes, and prompt content. An exported prompt can contain private
conventions; treat it as sensitive.

## Run safely

Use the same requirements for the live run:

```bash
forge \
  --name atlas \
  --stack fastapi \
  --description "Customer support API" \
  --no-docker \
  --approval-mode safe \
  --no-open \
  --verify
```

`safe` is the default. Before the first call, Forge shows the workspace, providers, model behavior,
remaining provider calls, a qualified duration range, execution strategy, demo and verification
limits, and possible provider quota or billing. Live execution sends the assembled brief,
conventions, and selected context to the provider. The provider may edit the target workspace,
install dependencies, run commands, use allowed network access, and consume quota.

`--approval-mode plan` uses a read-only provider mode but still makes provider calls.
`--approval-mode unsafe --allow-unsafe` disables provider approval or sandbox boundaries and should
only be used inside an external isolation boundary you control.

Demo mode is enabled by default so generated startup should not require real service credentials.
It does not remove the provider CLI's own authentication requirement.

## Verify the result

Forge writes these project-local records:

| File | Evidence |
| --- | --- |
| `.forge/progress.json` | Prompt hashes, attempts, durations, failure category, and resume state |
| `.forge/scaffold.json` | Requested facts, routing, models, approval mode, and convention hashes |
| `.forge/conventions-snapshot.md` | Exact replay input; potentially private |
| `.forge/verification.json` | Redacted commands, working directories, timeouts, exits, endpoints, and remediation |

The dashboard reports `Project Ready` only when required verification passes. If verification was
disabled or skipped, the honest result is `Project Created`; a failed check requires attention.
For high-confidence delivery, rerun the generated project's recorded commands independently.

A generated Python project can declare bounded health settings:

```toml
[tool.forge.verification]
health_endpoints = ["/healthz", "/readyz"]
health_startup_timeout = 20
health_request_timeout = 4
```

Health paths remain localhost-only and timeout values are bounded by Forge.

## Resume a failed scaffold

Do not delete partial output or blindly restart. Fix the provider problem, then repeat the original
command with `--resume`:

```bash
forge \
  --name atlas \
  --stack fastapi \
  --description "Customer support API" \
  --no-docker \
  --approval-mode safe \
  --no-open \
  --verify \
  --resume
```

Forge checks the original name, stack, routing, prompt hashes, and approval mode. It preserves
completed phases and retries incomplete ones. Contract drift is rejected rather than silently
mixing two scaffolds.

## Manage conventions

Effective precedence is bundled defaults, selected user profile, `~/.forge/conventions.md`, then
project-local `.forge/conventions.md`. Later layers have higher precedence.

```bash
forge conventions init team
forge conventions import ./AGENTS.md --name imported-team
forge conventions list
forge conventions select team
forge conventions inspect --stack fastapi --json
forge conventions preview --stack fastapi
forge conventions validate --stack fastapi
forge conventions edit team
```

Imports must be Markdown, are size-bounded, and reject credential-shaped content. Repository
maintainers use the separate `forge admin conventions` command for bundled convention sources.

## Other commands

```bash
forge                         # Interactive scaffold
forge doctor                  # Readiness diagnostics, no model call
forge doctor --preflight gemini  # Explicit Gemini readiness call; quota may apply
forge stats                   # Local scaffold analytics
forge check                   # Read-only convention audit
forge check --fix             # Add supported missing convention files
forge evolve auth --dry-run   # Preview an existing-project change
forge evolve auth             # Apply it in safe mode
forge replay --dry-run        # Preview from recorded manifest/snapshot
forge replay --diff           # Replay and compare in safe mode
```

Run root or subcommand `--help` immediately before scripting a command; live help is the runtime
contract.

## Agent skill

The release archive includes `skills/forge-scaffold/SKILL.md`; the wheel installs the same files
under `ubundiforge/skills/forge-scaffold/`. The skill teaches agents to discover live Forge
behavior, preview with zero calls, preserve safe approval boundaries, and verify durable evidence
without hard-coded release or model catalogs. Its behavioral evidence is in
[the maintainer record](docs/maintainers/skill-behavioral-evidence.md).

## Security, privacy, and support

Read [Security and Privacy](docs/guides/security-privacy.md) before using private conventions or
unsafe mode. Report vulnerabilities through [SECURITY.md](SECURITY.md); use
[GitHub Issues](https://github.com/Schramm2/projectforge/issues) for ordinary bugs.

## Upgrade or uninstall

See [the 0.4.1 migration guide](docs/guides/migrating-from-0.4.1.md) before upgrading.

```bash
uv tool upgrade projectforge
# or
brew upgrade schramm2/tap/projectforge
```

Uninstall the application with the matching package manager:

```bash
uv tool uninstall projectforge
# or
brew uninstall projectforge
```

User-owned config, profiles, snapshots, and local history under `~/.forge/` are not removed. Back
them up or move that directory separately if you no longer need them.

## Documentation

- [Getting Started](docs/guides/getting-started.md)
- [Configuration](docs/guides/configuration.md)
- [Stacks](docs/guides/stacks.md)
- [Troubleshooting](docs/guides/troubleshooting.md)
- [Provider compatibility evidence](docs/maintainers/provider-compatibility.md)
- [Documentation map](docs/README.md)

## Development

```bash
uv sync --dev
uv run python scripts/scan_safety.py
uv run python scripts/check_docs.py
uv run ruff check src/ubundiforge tests
uv run pytest
uv build
```

The import namespace remains `ubundiforge` for compatibility. See [AGENTS.md](AGENTS.md) and the
maintainer docs before changing release behavior.

## License

MIT — see [LICENSE](LICENSE).
