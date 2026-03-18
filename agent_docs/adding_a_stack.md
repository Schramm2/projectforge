# Adding a New Stack Type

Checklist of files to modify when adding a new stack to UbundiForge, in order.

## 1. Define stack metadata — `ubundiforge/stacks.py`

Add a new `StackMeta` entry to the `STACK_META` dict with:
- `package_manager` — e.g. "uv", "npm", "uv + npm"
- `default_structure` — list of directories/files the scaffold should create
- `common_libraries` — dict of library name -> description
- `dev_commands` — dict of command name -> shell command
- `services` — list of optional services users can select
- `docker_default` — whether Docker is included by default
- `env_hints` — list of `.env.example` entries (use `{project_name}` placeholder)

## 2. Add to interactive menu — `ubundiforge/prompts.py`

Add a `questionary.Choice` to the `STACK_CHOICES` list. The `value` must match the key used in `STACK_META`.

## 3. Add routing — `ubundiforge/router.py`

Add the stack key to the `ROUTING` dict mapping it to the preferred AI backend.

## 4. Add prompt label — `ubundiforge/prompt_builder.py`

Add the stack key to the `STACK_LABELS` dict with a human-readable description used in the generated prompt.

## 5. Add CLI aliases — `ubundiforge/cli.py`

Add shorthand entries to the `STACK_ALIASES` dict so users can use `--stack <alias>` in non-interactive mode.

## 6. Add CI actions — `ubundiforge/scaffold_options.py`

Add the stack key to `STACK_CI_ACTIONS` with the list of applicable CI action IDs from `CI_ACTION_OPTIONS`.

If the stack needs auth support, add it to `AUTH_SUPPORTED_STACKS`.

## 7. Add tests

Add or update tests in `tests/` to cover the new routing, prompt building, and scaffold options for the new stack.

## Verification

After all changes:
```bash
uv run pytest
uv run ruff check ubundiforge/
```

Then test end-to-end:
```bash
forge --name test-project --stack <new-stack> --description "test" --dry-run
```
