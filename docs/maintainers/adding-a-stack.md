# Adding a New Stack

Use this checklist when promoting a new scaffold type into Forge.

## Implementation checklist

1. Update `src/ubundiforge/stacks.py`.
   Add the new `StackMeta` entry to `STACK_META`, including structure, libraries, commands, services, Docker default, and env hints.
2. Update `src/ubundiforge/prompts.py`.
   Add the stack to the interactive selection flow.
3. Update `src/ubundiforge/router.py`.
   Define the stack's phases and preferred backend routing.
4. Update `src/ubundiforge/prompt_builder.py`.
   Add the human-readable stack label used in the generated prompt.
5. Update `src/ubundiforge/cli.py`.
   Add any shorthand aliases accepted by `--stack`.
6. Update `src/ubundiforge/scaffold_options.py`.
   Wire in CI actions and auth support when the stack needs them.
7. Update [../guides/stacks.md](../guides/stacks.md).
   Document identifiers, aliases, defaults, project structure, libraries, and dev commands.
8. Update tests.
   Add or adjust coverage for routing, prompt generation, CLI parsing, options, and snapshots where needed.

## Verification

```bash
uv run pytest
uv run ruff check .
./forge --name test-project --stack <new-stack> --description "test" --dry-run
```
