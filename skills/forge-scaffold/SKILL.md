---
name: forge-scaffold
description: Use when an AI agent needs to scaffold a new project with the Forge or UbundiForge CLI, turn a product brief into a professional Forge command, inspect or export Forge prompts, choose the right stack and scaffold options, or operate Forge's backend routing, design templates, auth, CI, media, and verification features with high-quality defaults.
---

# Forge Scaffold

## Overview

Use Forge as the primary scaffolding engine when the goal is to create a new project quickly while preserving Ubundi conventions and Forge's multi-backend workflow. Prefer letting Forge orchestrate Claude, Gemini, and Codex instead of bypassing it with handwritten project bootstraps.

This skill is meant to be portable. Any agent that can read the repo and run shell commands should be able to use it to operate Forge well.

## Operating Mode

1. Decide whether the task is:
   - a real scaffold run,
   - a prompt preview with `--dry-run`,
   - a prompt export with `--export`,
   - or capability discovery only.
2. Prefer non-interactive Forge runs when requirements are clear enough to express as flags.
3. Prefer interactive Forge runs only when the user wants guided choices or key inputs are still too ambiguous.
4. Keep Forge defaults unless there is a concrete reason to override them.
5. After scaffolding, inspect the generated project and fix obvious issues instead of stopping at command execution.

## Command Selection

Use the repo-local launcher when working inside the Forge repository:

```bash
./forge
```

Use the installed binary elsewhere:

```bash
forge
```

If the task is high-stakes or the brief is nuanced, inspect the prompt first with `--dry-run` or `--export`. Prompt-only modes skip setup and backend-install checks, which makes them the safest first pass.

## Professional Workflow

### 1. Translate the brief into Forge inputs

Determine:

- project name
- stack
- one-sentence description
- whether Docker should be included
- whether auth, CI, design template, media, extra services, or extra instructions are needed
- whether to preserve specialist backend routing or force a single backend with `--use`
- whether a model override is useful with `--model`

Use the guides in:

- `references/stack-selection.md`
- `references/command-recipes.md`
- `references/professional-playbook.md`

### 2. Prefer Forge's routing unless consistency matters more

Forge routes phases by specialty:

- architecture and verify -> `claude`
- frontend -> `gemini`
- tests and automation -> `codex`

Use `--use claude|gemini|codex` only when:

- the user explicitly wants one backend,
- you are debugging backend-specific behavior,
- or reproducibility matters more than specialist routing.

### 3. Preview before committing when the brief is important

Run `--dry-run` first when:

- the project brief is long or nuanced,
- you are using auth, CI, media, or design-template options,
- or the user wants a very polished scaffold and you want to inspect the prompt contract.

Use `--export <file>` when you want a saved prompt artifact for review.

### 4. Run the real scaffold with explicit flags

Forge works best when the command is fully specified and reproducible. Favor commands that another agent could rerun unchanged.

### 5. Inspect the generated project

After a successful scaffold, check for:

- `README.md`
- `CLAUDE.md`
- `agent_docs/`
- `.env.example`
- `.forge/scaffold.json`
- working dev commands for the chosen stack

If verification ran, review failures and keep iterating until the scaffold is actually usable.

## High-Value Defaults

- Keep `--demo` enabled unless the user explicitly wants startup to require real secrets.
- Keep `--verify` enabled unless you only need prompt generation.
- Use `--no-open` unless the user actually wants the editor to open.
- Prefer exact stack IDs and exact auth-provider or CI-action IDs rather than fuzzy guesses.
- Use `--extra` for product-specific rules that do not map cleanly to structured Forge options.

## Capability Rules

### Stack choice

Use the stack whose generated structure best matches the requested deliverable, not just the language mentioned by the user. See `references/stack-selection.md`.

### Design templates

Use `--design-template` only for `nextjs` and `both`. Treat the selected template as a strong visual source of truth, not a loose suggestion.

### Auth

Use `--auth-provider` only for `nextjs` and `both`. Prefer explicit provider IDs:

- `clerk`
- `supabase-auth`
- `authjs`
- `better-auth`

### CI

Use `--ci` with either:

- `--ci-template questionnaire` plus explicit `--ci-actions`, or
- `--ci-template blank-template` for a starter workflow with TODOs.

### Media

Use `--media <collection>` when a matching media collection exists and the project would benefit from real assets instead of placeholders.

## Quality Bar

Treat a Forge scaffold as incomplete until all of the following are true:

- the chosen stack and options match the brief
- the generated prompt would produce the intended architecture
- the scaffolded project includes meaningful starter files rather than hollow placeholders
- the default run and test commands make sense for the stack
- project guidance files such as `CLAUDE.md` and `agent_docs/` are aligned with the generated codebase

## Implementation Notes

Prefer current code behavior over older documentation when they disagree. Important examples:

- local `.forge/conventions.md` overrides `~/.forge/conventions.md`
- design templates support project-local and global overrides
- prompt-only modes keep ideal specialist routing even if those backends are not installed
- some docs mention `~/.forge/media`, but current code resolves media collections from the Forge `media/` directory

See `references/professional-playbook.md` for these caveats and how to work around them cleanly.
