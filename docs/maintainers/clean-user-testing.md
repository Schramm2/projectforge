# Clean-user testing

The clean-user harness installs ProjectForge into isolated uv tool directories and runs it with a
separate `FORGE_HOME`, workspace, provider path, uv cache, and Git configuration. It never reads or
writes the developer's real Forge data, and provider credentials are removed from the child
environment.

Use it when changing installation, first-run setup, `doctor`, provider readiness, prompt-only
behavior, package contents, or command entry points.

## Automated installed-wheel verification

Run the full deterministic suite:

```bash
uv run python scripts/clean_user_harness.py verify
```

The harness builds the current wheel, installs it with `uv tool install`, and checks:

| Scenario | Expected behavior |
| --- | --- |
| Pristine, no provider | Both commands work; doctor reports missing config/providers; setup gives recovery guidance. |
| Pristine dry run | Prompt preview succeeds without setup, provider execution, config creation, or project files. |
| Codex installed, logged out | Doctor reports `needs_login` and exits with attention required. |
| Codex ready, no config | Provider readiness passes, but doctor still requires first-run configuration. |
| Codex ready, configured | Doctor reports the installation ready. |

The provider scenarios use a local diagnostic shim. It implements only `codex --version` and
`codex login status`; generation exits with code 86 so the harness cannot make a model call.

CI builds the package first and passes that artifact into the same suite:

```bash
uv run python scripts/clean_user_harness.py verify \
  --wheel dist/matt_projectforge-*.whl
```

Temporary harness files are removed after a successful or failed run unless `--keep` or `--root`
is supplied.

## Reproduce one state

Run one command against an isolated installed package:

```bash
uv run python scripts/clean_user_harness.py run \
  --scenario logged-out \
  -- projectforge doctor --json
```

Available scenarios are `no-provider`, `logged-out`, and `ready`. Add `--configured` to seed the
smallest valid config, representing a completed first-run setup:

```bash
uv run python scripts/clean_user_harness.py run \
  --scenario ready \
  --configured \
  -- projectforge doctor --json
```

Use `--root` to preserve and reuse a named environment while investigating an issue:

```bash
uv run python scripts/clean_user_harness.py run \
  --root /tmp/projectforge-issue-repro \
  --scenario no-provider \
  -- projectforge --setup
```

The harness never clears a supplied root. Reusing it intentionally preserves any Forge state and
workspace files created by earlier commands.

## Interactive fix loop

Open a shell with the current source installed in editable mode:

```bash
uv run python scripts/clean_user_harness.py shell \
  --scenario ready
```

Inside the shell, useful probes include:

```bash
projectforge --version
projectforge doctor
projectforge
```

The unconfigured `ready` scenario enters the actual first-run wizard with a deterministic ready
provider. Exit after setup rather than starting a live scaffold: the provider shim deliberately
rejects generation. Source edits are visible immediately because shell mode defaults to an
editable install.

Use `--keep` to retain an automatically named environment after leaving the shell, or use a stable
`--root` path for repeated sessions. Pass `--wheel path/to/file.whl` when the bug may be specific to
packaging rather than source behavior.

## Boundaries

- The harness verifies packaging, entry points, setup gates, prompt-only behavior, and readiness
  classification; it does not replace an authenticated provider end-to-end scaffold.
- The fixed provider path intentionally hides real Claude, Antigravity, and Codex installations.
- System Git remains visible, but `GIT_CONFIG_GLOBAL` points to a scenario-local file so setup can
  exercise Git prompts without mutating the developer's global Git configuration.
- Interactive mode uses `/bin/sh` without host shell startup variables, preventing dotfiles from
  restoring real provider paths inside the harness.
- Docker and editor discovery reflect the harness path rather than the full host environment.
