# Workflow Branches

Read only the branch that matches the user's request. Always inspect live help first; the examples
show command shape, not a promise that every installed release exposes every option.

## Preview or scaffold

Start from this explicit shape after checking root help:

```bash
"$FORGE_CMD" \
  --name <project-name> \
  --stack <stack-id> \
  --description "<brief>" \
  --docker-or-no-docker \
  --approval-mode safe \
  --no-open \
  --dry-run
```

Replace the Docker placeholder with exactly one live flag. Add structured options only when the
brief requests them and live help confirms support. For the approved live run, remove `--dry-run`
and retain `--approval-mode safe`, `--no-open`, and the same requirements. Verification is enabled
by default; keep it explicit when evidence clarity matters.

Use `--export <path>` instead of `--dry-run` only when the user requests a review artifact. Treat
the exported prompt as potentially sensitive.

## Audit an existing project

```bash
"$FORGE_CMD" check --help
"$FORGE_CMD" check
```

`check` is read-only unless the user explicitly requests `--fix`. Export only to a user-approved
path. An audit result is convention evidence, not a replacement for the project's tests.

## Evolve an existing Forge project

```bash
"$FORGE_CMD" evolve --help
"$FORGE_CMD" evolve <capability> --dry-run
```

Require `.forge/scaffold.json` and inspect the preview before live evolution. For live execution,
use `--approval-mode safe`. Verify the changed project's recorded commands and confirm the
evolution entry without assuming that a successful provider exit means the feature works.

## Replay or compare

```bash
"$FORGE_CMD" replay --help
"$FORGE_CMD" replay --dry-run
```

Replay depends on the original manifest and convention snapshot. Use `--diff` only when the user
wants a comparison artifact. Never replace the current project with replay output implicitly.

## Manage user conventions

```bash
"$FORGE_CMD" conventions --help
"$FORGE_CMD" conventions inspect --help
"$FORGE_CMD" conventions inspect --stack <stack-id> --json
```

Use `init`, `import`, `list`, `select`, `inspect`, `preview`, `validate`, or `edit` according to live
help. Imports must be Markdown and credential-free. User profiles layer between bundled defaults
and user-wide/project-local sources; later layers have higher precedence. Keep bundled-repository
administration under `forge admin conventions` separate from user profile management.

## Statistics or administration

`stats` reports local aggregate history. `admin conventions` operates on bundled repository
conventions. Inspect their help and keep these read-only unless the user separately authorizes a
repository edit.
