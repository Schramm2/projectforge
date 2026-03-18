# Architecture — Pipeline Flow and Module Responsibilities

## Pipeline overview

```
forge CLI invoked
  |
  v
setup.py          First-run wizard (detect backends, pick default, create conventions file)
  |                Runs only when ~/.forge/config.json is missing, or with --setup flag
  v
cli.py            Orchestration: parse flags, validate inputs, coordinate all steps below
  |
  v
prompts.py        Interactive questionnaire (name, stack, description, docker, optional customization)
  |                Customization drills into: auth provider, services, CI config, extra instructions
  v
router.py         Picks AI backend from ROUTING dict; falls back through FALLBACK_ORDER if primary not installed
  |                ROUTING maps stack -> backend (currently all map to "claude")
  |                FALLBACK_ORDER: claude -> gemini -> codex
  v
conventions.py    Loads ~/.forge/conventions.md (user's coding standards)
  |                Also loads CLAUDE.md template from ~/.forge/claude-md-template.md if present
  v
prompt_builder.py Assembles the final prompt string from:
  |                - User answers (name, stack, description, docker, services, auth, CI)
  |                - Stack metadata from stacks.py (structure, libraries, dev commands, env hints)
  |                - Auth/CI metadata from scaffold_options.py
  |                - Cross-recipe defaults from stacks.py (CROSS_RECIPE_DEFAULTS)
  |                - User conventions from conventions.py
  |                - Optional CLAUDE.md template
  v
safety.py         Scans extra instructions for secret patterns before passing to AI
  |
  v
runner.py         Builds subprocess command for chosen backend, executes in project_dir
                   Post-run: ensures git init, optionally opens editor
```

## Key data structures

### StackMeta (stacks.py)
Dataclass holding per-stack metadata: package_manager, default_structure, common_libraries, dev_commands, services, docker_default, env_hints. Each supported stack has an entry in the `STACK_META` dict.

### CROSS_RECIPE_DEFAULTS (stacks.py)
A long string of cross-project standards (Python conventions, TypeScript conventions, Docker conventions) injected into every generated prompt regardless of stack.

### AuthProviderOption / CiActionOption (scaffold_options.py)
Frozen dataclasses defining auth providers (Clerk, Supabase, Auth.js, Better Auth) and CI actions (lint, typecheck, build, tests, docker-build). Each carries a label, prompt_description, and relevant metadata. `AUTH_SUPPORTED_STACKS` and `STACK_CI_ACTIONS` control which options are available per stack.

## Configuration files (user-side)

All stored under `~/.forge/`:
- `config.json` — saved preferences (default_backend, preferred_editor, available_backends)
- `conventions.md` — coding standards injected into every scaffold prompt
- `claude-md-template.md` — optional CLAUDE.md template for scaffolded projects

## Non-interactive mode

When `--name`, `--stack`, and `--description` are all provided via flags, the CLI skips the interactive questionnaire entirely. Additional flags (`--docker`, `--auth-provider`, `--services`, `--ci`, `--ci-template`, `--ci-actions`) control customization without prompts.

## Stack aliases (cli.py)

`STACK_ALIASES` maps shorthand names to canonical stack IDs. For example: "next" -> "nextjs", "api" -> "fastapi", "fullstack" -> "both", "cli" -> "python-cli".
