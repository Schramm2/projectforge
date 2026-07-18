---
name: forge-scaffold
description: Use when a user asks to scaffold, preview, audit, evolve, replay, or manage conventions with ProjectForge or the Forge CLI.
---

# ProjectForge Operator

Use ProjectForge as the orchestration boundary for project scaffolding. Treat the invoked CLI's
help, doctor report, preview, manifest, and verification report as the runtime contract. Never
substitute remembered release details for live evidence.

## Establish the live contract

Resolve the command without installing or upgrading anything:

```bash
if test -x ./forge && test -f pyproject.toml; then
  FORGE_CMD=./forge
elif command -v forge >/dev/null 2>&1; then
  FORGE_CMD=forge
else
  echo FORGE_NOT_FOUND
fi
```

If Forge is absent, stop. Point to the repository's current installation documentation or current
official release; do not invent a version, model, package channel, or install URL.

For an available command, inspect before constructing a live run:

```bash
"$FORGE_CMD" --version
"$FORGE_CMD" --help
"$FORGE_CMD" doctor --json
```

`doctor --json` may exit nonzero while still returning useful JSON. A preview can continue without
an authenticated provider. A live provider run requires at least one provider whose readiness is
`ready`. Never infer authentication from installation or `--version`, and never print provider
identity or credential values.

Read the relevant subcommand help immediately before using a non-scaffold branch. See
[`references/workflows.md`](references/workflows.md) for branch routing and command templates.

## Safety invariants

- Preview before execution when the user requests review, the brief is ambiguous, the destination
  may collide, or external services materially change the scaffold.
- Treat `--dry-run` as a zero-provider-call preview. Do not add a separate provider planning call.
- Use `--approval-mode safe` for normal live scaffolds, evolve, and replay operations.
- `unsafe` disables provider approval boundaries. Use it only when the user explicitly requests
  that risk and the command also carries the CLI's explicit unsafe-consent flag.
- Prefer the provider's default model. Add `--model` only for a user-requested reproducibility or
  compatibility requirement, and let the provider validate it at execution.
- Keep `--demo` enabled unless the user explicitly wants generated startup to require real service
  credentials. Never place secrets in the description, `--extra`, conventions, logs, or evidence.
- Use `--no-open` unless the user asks to launch an editor.
- Do not overwrite a non-empty target. Follow Forge's collision flow or ask the user to choose the
  existing-project action deliberately.
- Explain that live execution sends the assembled brief, effective conventions, and selected
  context to the chosen provider and may create files, install dependencies, run commands, and
  consume provider quota.
- Preserve partial output after failure. Do not delete, reset, or blindly restart successful
  phases.

## Scaffold workflow

1. Turn the brief into explicit name, stack, description, Docker choice, and only the options the
   user actually requested. Check live help instead of guessing supported combinations.
2. Resolve the intended parent directory and target. Check whether the target exists before any
   live run.
3. Run the same scaffold command with `--dry-run`. Do not claim it validated provider readiness or
   generated-project behavior.
4. Review the preview for target, stack, requested inclusions/exclusions, phase routing, provider
   default versus model override, approval mode, convention source order/hashes, warnings, and any
   unexpected service or sensitive context.
5. If the user requested an approval gate, return the preview assessment and wait. Otherwise,
   continue only when the request already authorizes a live scaffold.
6. Recheck `doctor --json` and target collision immediately before execution.
7. Run the matching live command with `--approval-mode safe`, `--no-open`, and verification enabled.
   Keep the previewed requirements unchanged.
8. Inspect the dashboard and durable evidence. A zero provider exit is not enough, and a skipped
   verification is not a verified project.
9. Independently run the generated project's documented or recorded commands when the user asked
   for a working result. Do not invent package layout, module names, health paths, or test folders.
10. Report outcome, exact evidence, partial-output state, failures, and the safest next action.

## Completion criteria

Claim success only when all applicable items are true:

- the requested project exists at the confirmed target;
- `.forge/scaffold.json` matches the requested stack, routing, model behavior, and approval mode;
- `.forge/conventions-snapshot.md` and the manifest's ordered source hashes explain the effective
  convention inputs;
- `.forge/verification.json` agrees with the dashboard and contains no unresolved required failure;
- the generated project's own install, lint, type-check, build, test, and health commands pass where
  the project defines them;
- requested exclusions such as `--no-docker` are absent from the generated output; and
- the handoff contains no secrets, account identities, or machine-local paths that should not be
  durable.

If any required item is false or unavailable, say "project created; verification incomplete" or
"project created; verification failed" and name the missing evidence. Use
[`references/evidence-and-recovery.md`](references/evidence-and-recovery.md) for failure triage,
privacy, and handoff details.
