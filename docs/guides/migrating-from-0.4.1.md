# Migrating from ProjectForge 0.4.1

Current ProjectForge releases use `projectforge` as the preferred command and canonical Python
namespace, with `forge` retained as a compatibility command. Existing projects and user
configuration remain usable. The Gemini-to-Antigravity migration described below applies when
upgrading from v0.5.0 or earlier.

## Configuration

Forge reads the unversioned 0.4.1 `~/.forge/config.json` format and normalizes it to schema version
1. Existing model overrides for supported providers are preserved. New setups omit model overrides
by default so each provider can select its current default or auto model.

Gemini CLI is retired. Forge maps a saved `gemini` backend selection to `antigravity` in memory and
drops its old model override because Antigravity's model display names are not guaranteed to accept
Gemini CLI identifiers. Install and authenticate `agy`, run `forge doctor`, then use
`forge --setup` to save the current provider selection. Legacy replay manifests and resumable
progress contracts translate only the retired backend name; prompt hashes and all other resume
invariants remain enforced.

Config saves are now atomic and use user-only permissions. If the file is invalid or contains an
unsupported key, Forge preserves it as `config.json.corrupt-<timestamp>` and asks you to run
`forge --setup`. Do not delete the recovery copy until you have reviewed it locally.

## Conventions

The 0.4.1 user-wide file `~/.forge/conventions.md` is still supported. Effective precedence is now:

1. bundled defaults;
2. the selected user profile under `~/.forge/profiles/`;
3. `~/.forge/conventions.md`; and
4. project-local `.forge/conventions.md`.

Later layers have higher precedence. Start without replacing existing instructions:

```bash
forge conventions init team
forge conventions import ./AGENTS.md --name imported-team
forge conventions list
forge conventions select team
forge conventions inspect --stack fastapi --json
forge conventions validate --stack fastapi
```

Every live or preview scaffold shows ordered source hashes. New manifests record those sources and
the conventions snapshot remains the replay input.

## Provider execution

Normal runs now default to `--approval-mode safe` and provider-default models. The former implicit
provider bypass/yolo behavior is removed. A blanket bypass requires both
`--approval-mode unsafe` and `--allow-unsafe` on that specific command.

Run `forge doctor` after upgrading. A provider must be both installed and verifiably ready before
Forge routes a live phase to it. Antigravity readiness uses `agy models`, which verifies the saved
Google session without an inference call. If login is required, run `agy`, complete Google Sign-In,
exit with `/exit`, and rerun `forge doctor`.

## Evidence and recovery

New scaffolds write `.forge/progress.json` before provider execution. If a phase fails, preserve the
directory and repeat the same command with `--resume`; changed options, routing, prompt hashes, or
approval mode are rejected. Scaffolds created by 0.4.1 do not have this phase ledger and cannot use
the new resume path retroactively.

Verification now follows generated Python metadata, supports bounded project-declared health paths
under `[tool.forge.verification]`, and writes `.forge/verification.json`. The dashboard reports
`Project Ready` only when required verification passes.

## Shipped agent skill

The Forge operator skill no longer hard-codes release or model catalogs. Agents are instructed to
consult live help, `forge doctor --json`, safe preview/execution, and durable evidence. If you copied
an older skill into another agent workspace, replace it from the current checkout or a future
release that includes the Antigravity migration.
