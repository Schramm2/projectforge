# Configuration

ProjectForge keeps user-owned configuration under `~/.forge/` and project evidence under each
generated project's `.forge/` directory. Set `FORGE_HOME` to override the user-data directory for
isolated automation or ephemeral environments; Forge's own tests use this boundary and never write
to the developer's real home directory.

## User config

`~/.forge/config.json` is created by `forge --setup`. Forge validates its schema, writes it
atomically with user-only permissions, and rejects unknown keys.

| Key | Meaning |
| --- | --- |
| `config_version` | Current config schema version. |
| `preferred_editor` | Editor identifier used for optional CLI or macOS application opening. |
| `available_backends` | Provider names detected during the last setup run; readiness is rechecked. |
| `backend_models` | Optional advanced model overrides keyed by provider. Empty means provider default/auto. |
| `docker_available` | Docker availability observed during setup. |
| `projects_dir` | Default parent directory for generated projects. |
| `agents` | Default standard versus multi-agent execution preference. |
| `sound` | Whether a successful scaffold plays the local completion sound. |
| `conventions_profile` | Selected user convention profile name. |

Do not place credentials, provider identity, or arbitrary extra keys in this file. Provider login
belongs to the provider CLI. Re-run setup to change normal preferences. Setup keeps the selected convention profile unless you
choose another convention option:

```bash
forge --setup
forge doctor
```

An invalid config is moved to `config.json.corrupt-<timestamp>` when possible. Forge then uses safe
defaults and asks you to run setup. Review the recovery copy locally before removing it.

Antigravity authentication remains in the operating system keyring managed by `agy`; Forge does
not copy it into `~/.forge`. `forge doctor` uses `agy models` as a non-inference session check and
stores none of its output.

Upgrades from a release that supported Gemini CLI may leave
`~/.forge/provider-preflight.json`. Current Forge does not read that obsolete, credential-free
timestamp file; you may remove it after confirming the upgrade.

The unversioned 0.4.1 config is normalized in memory. Existing supported-provider model overrides
are preserved; a fresh setup omits them so providers choose their current defaults. A retired
`gemini` backend entry becomes `antigravity`, while a Gemini CLI model override is discarded
because Antigravity model display names are not compatibility-guaranteed. See
[Migrating from 0.4.1](migrating-from-0.4.1.md).

## Convention profiles and precedence

First-run setup offers three useful starting points: bundled defaults, an explicit import of nearby
instruction files, or a short interview that writes a reusable profile. Nearby discovery is bounded
to `AGENTS.md`, `CLAUDE.md`, and `.github/copilot-instructions.md` in the directory where setup runs;
it does not recursively scan the repository.

Effective convention order is deterministic, from lowest to highest precedence:

1. bundled release defaults;
2. selected `~/.forge/profiles/<name>.md`;
3. legacy-compatible `~/.forge/conventions.md`; and
4. project-local `.forge/conventions.md`.

Later layers have higher precedence. Empty, placeholder-only, or known generated legacy mirrors are
ignored with a warning. Credential-shaped content is rejected before a provider call.

Manage user-owned profiles without editing JSON:

```bash
forge conventions init team
forge conventions import ./CLAUDE.md --name imported-team
forge conventions list
forge conventions select team
forge conventions inspect --stack fastapi --json
forge conventions preview --stack fastapi
forge conventions validate --stack fastapi
forge conventions edit team
```

`init` and `import` never overwrite an existing profile. Imports must be Markdown and no larger
than 1 MB. `inspect` shows the exact ordered paths, warnings, and SHA-256 hashes; `preview` prints
the effective content and starts no provider.

Repository maintainers change bundled rules through `forge admin conventions`; that command is not
the user-profile interface.

## Project evidence

Live scaffolds initialize an unborn `main` Git repository before provider work. Forge adds
`.forge/` and `.code-review-graph/` to the repository-local `.git/info/exclude` so provider commits
do not capture private evidence or local graph runtime data.

### `.forge/progress.json`

Written before the first provider phase. It stores schema version, project name and stack, approval
mode, provider routing, prompt hashes, phase status, attempts, durations, exit codes, and stable
failure categories. It never stores prompt or provider output. `--resume` requires this file and an
exact execution-contract match.

### `.forge/scaffold.json`

Written after provider phases complete. It records Forge version, requested project facts, routing,
provider-default versus explicit model behavior, approval mode, design/media/auth selections, demo
mode, project brief, selected-context source hashes, effective convention hash, ordered convention
sources, and timestamp. Selected file content stays out of this JSON record.

### `.forge/conventions-snapshot.md`

The exact effective convention content used for replay. It can contain private organization or
personal guidance; do not paste it into public issues or external messages by default.

### `.forge/context-snapshot.md`

The exact project brief and nearby Markdown content the user approved for the provider prompt.
Forge writes this file only when project context was supplied. The scaffold manifest records source
paths and hashes without copying selected file content into JSON. Treat the snapshot as potentially
private.

### `.forge/verification.json`

Records each generated-project check with command, project-relative working directory, startup and
request timeouts, exit, skip reason, attempted localhost health endpoints, duration, redacted
detail, and remediation. Python checks also validate required project files, tracked `uv.lock`
behavior, and generated console entry points through bounded `--help` smoke commands. Its
`all_passed` value drives dashboard readiness.

## Generated health settings

Python projects can declare bounded health-probe settings in their generated `pyproject.toml`:

```toml
[tool.forge.verification]
health_endpoints = ["/healthz", "/readyz"]
health_startup_timeout = 20
health_request_timeout = 4
```

Forge accepts one to eight local path-only endpoints, a 1–120 second startup timeout, and a 1–30
second request timeout. Invalid metadata falls back to `/health`, `/ready`, 12 seconds, and 3
seconds. The host and port remain derived from the local generated-project run command.

## Design templates

Design templates apply only to frontend-capable stacks. Override order is:

1. project-local `.forge/design-templates/<template-id>.md`;
2. `~/.forge/design-templates/<template-id>.md`; and
3. the template bundled with Forge.

The current built-in identifier is `default-design-guide`. Use live `forge --help` rather than a
copied provider or model catalog when scripting options.

## Media assets

Named collections live under `~/.forge/media/<collection>/`, or
`$FORGE_HOME/media/<collection>/` when the user-data override is active. This keeps user assets
outside package-manager directories so upgrades and uninstalls do not remove them. `--media`
accepts a collection name, not an arbitrary path. If exactly one collection exists, Forge can
select it unless `--no-media` is present.

If an older source checkout stored collections under its repository-level `media/` directory, move
each named collection into `~/.forge/media/` before removing that checkout. Do not keep user assets
inside a Homebrew Cellar directory because package upgrades can remove it.

Destination depends on stack: `public/` for Next.js, `static/` for FastAPI, `frontend/public/` for a
monorepo, and `assets/` for CLI/package/worker stacks.

## Post-scaffold hook

`~/.forge/hooks/post-scaffold.sh` runs after scaffold verification and must be executable. It is
user-authored shell code running with your account's permissions and a 60-second limit. Review it
before use.

Available variables are `FORGE_PROJECT_DIR`, `FORGE_PROJECT_NAME`, `FORGE_STACK`, and
`FORGE_DEMO_MODE`. Avoid credentials in command arguments or output because hooks are outside
Forge's provider-output redaction boundary.

## Local history

- `~/.forge/scaffold.log` is append-only JSONL with project name, stack, providers, target directory
  name, demo-mode value, verification status/request, measured total duration when available, and
  timestamp. It does not store the absolute target path.
- `~/.forge/quality.jsonl` stores local verification quality signals used for routing.
- `~/.forge/preferences.json` stores local answer frequencies used for interactive defaults.

Run `forge stats --repair` once after upgrading if older development tests polluted local history.
Recognizable pytest entries are moved—not deleted—to a timestamped directory under
`~/.forge/quarantine/`, then stats are recalculated from the remaining evidence.

Forge does not transmit these local analytics. Back up or move `~/.forge/` before uninstalling if
you want to retain them. See [Security and Privacy](security-privacy.md) for the complete boundary.
