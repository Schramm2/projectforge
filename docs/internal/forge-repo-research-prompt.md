# Forge Repo Research Prompt

Internal working prompt. Replace `<forge_repo_root>` with the actual path to this repository before using it in another workspace.

Use this prompt in Claude Code when you have a workspace that contains multiple existing Ubundi projects and you want to extract the conventions, stacks, libraries, and scaffold patterns that Forge should learn from.

Best used from a parent directory that contains:

- the existing Ubundi repos to analyze
- the Forge repo itself

If Forge is not in the same workspace, adjust the paths in the prompt before running it.

---

## Prompt

```md
You are working on Forge, a Python CLI that scaffolds new projects by routing to AI coding tools and injecting Ubundi conventions into the generated prompt.

Your job is to analyze all existing Ubundi projects in this workspace and produce the source material Forge needs to generate more accurate, more Ubundi-like scaffolds.

Operate like a repo archaeologist and scaffold designer, not just a summarizer.

## Objective

Mine the existing project portfolio to discover:

- recurring project types and tech stacks
- common library choices and combinations
- shared folder structures and naming conventions
- frontend design conventions and UI libraries
- backend architecture conventions and infrastructure patterns
- environment variable and config conventions
- testing, linting, formatting, and CI expectations
- common integrations like auth, payments, AI providers, databases, queues, analytics, storage, and cloud tooling
- patterns that should become Forge defaults
- patterns that should become optional Forge recipes
- new stack options Forge should support
- routing hints for which AI backend Forge should prefer per stack

Your outputs must be useful for actually improving Forge, not just documenting the repos.

## Workspace Assumptions

- The workspace contains multiple Ubundi projects.
- The Forge repo is at: `<forge_repo_root>`
- Analyze sibling repos and nested repos that appear to be real product/code repositories.
- Ignore obvious noise like `.git`, `node_modules`, `.next`, `dist`, `build`, `.venv`, coverage artifacts, generated caches, and vendored dependencies.

## Deliverables

Create the following files under:

`<forge_repo_root>/research/forge-discovery/`

### 1. `portfolio-inventory.md`

For each repo analyzed, capture:

- repo name
- apparent product/domain
- primary stack
- secondary tools/frameworks
- package managers
- deployment/infrastructure clues
- whether it looks like a good Forge scaffold source
- notable unique patterns

Also include a short section for repos skipped and why.

### 2. `stacks.yaml`

Build a normalized stack catalog Forge can eventually use.

For each stack, include:

- `id`
- `label`
- `repo_examples`
- `languages`
- `frameworks`
- `package_managers`
- `common_libraries`
- `typical_services`
- `default_structure`
- `common_dev_commands`
- `should_be_supported_by_forge`
- `support_priority` as `high`, `medium`, or `low`
- `notes`

This file should include both current Forge stacks and any newly discovered stack candidates.

Examples of possible new stack families:

- React + Vite
- Next.js + Supabase
- FastAPI + Postgres
- Worker/service repos
- Internal CLI tools
- AI agent tools
- Fullstack monorepos with separate frontend/backend packages

### 3. `libraries-and-patterns.md`

Summarize reusable libraries and patterns across repos. Organize by category:

- frontend UI/styling
- state/data fetching
- auth
- forms/validation
- backend framework/runtime
- ORM/database
- background jobs
- AI/LLM tooling
- testing
- linting/formatting/type checking
- observability
- deployment/devops

For each library or pattern, include:

- how often it appears
- which repos use it
- what role it plays
- whether it should affect Forge scaffolds
- whether it should be a default, optional recipe, or repo-specific exception

### 4. `conventions-forge-should-learn.md`

Write a distilled conventions document specifically meant to improve Forge prompts.

This should cover:

- naming conventions
- directory structure conventions
- frontend design language
- component organization
- backend/service organization
- config and env var patterns
- testing expectations
- documentation expectations
- common scripts/commands
- git and release conventions if they are consistent enough

Separate:

- hard conventions
- soft conventions
- conflicting conventions

When conventions conflict, recommend a default and explain why.

### 5. `scaffold-recipes.md`

Define practical scaffold recipes Forge could support.

For each recipe, include:

- recipe name
- target use case
- triggering stack
- must-have files and folders
- recommended libraries
- optional integrations
- setup commands
- docs that should be generated
- what should go into `CLAUDE.md`
- what should go into `.env.example`
- whether Docker should be included by default

Examples:

- marketing site
- SaaS app
- FastAPI JSON API
- Next.js + API monorepo
- internal admin tool
- AI workflow service
- library/package repo
- CLI utility

### 6. `forge-recommendations.md`

Convert the research into concrete Forge changes.

Include recommendations for:

- new stack choices in `forge/prompts.py`
- routing updates in `forge/router.py`
- richer convention defaults in `forge/conventions.py`
- prompt assembly improvements in `forge/prompt_builder.py`
- whether Forge should support recipe selection in addition to stack selection
- whether Forge should support optional integrations as structured prompts
- whether Forge should support per-stack prompt templates
- whether the `CLAUDE.md` template should change

For each recommendation, include:

- priority
- why it matters
- evidence from analyzed repos
- exact Forge file(s) likely to change

### 7. `gaps-and-open-questions.md`

List areas where the portfolio does not give enough evidence, such as:

- one-off stacks
- contradictory conventions
- incomplete repos
- unclear deployment patterns
- areas that need human product judgment rather than inference

## Research Method

1. Identify all candidate repos in the workspace.
2. For each repo, inspect the top-level files and the metadata files that reveal stack and tooling.
3. Sample key source directories to understand architecture and conventions.
4. Extract patterns only when supported by evidence.
5. Distinguish between:
   - broadly repeated defaults
   - emerging patterns
   - one-off exceptions
6. Prefer practical scaffolding insight over exhaustive cataloging.

## Evidence Rules

- Do not guess.
- Cite concrete file paths when making claims.
- When useful, cite line references.
- If a pattern appears in only one repo, treat it as a candidate or exception, not a default.
- If two patterns conflict, explicitly say so and recommend one default for Forge.

## Special Focus Areas

Pay extra attention to anything Forge could eventually encode as structure instead of freeform prose:

- stack selection taxonomy
- optional integration choices
- preferred starter libraries
- standard directory layouts
- standard scripts and commands
- standard docs files
- standard environment variables
- standard Docker/devcontainer setup
- standard testing and linting setup
- recurring CLAUDE.md content

Also look for hidden but important patterns such as:

- repeated use of the same auth/database pairings
- common UI kit choices
- repeated repo layouts by product type
- repeated infrastructure/deployment setups
- repeated agent/AI tooling patterns
- repeated monorepo package boundaries

## Output Quality Bar

Your outputs should be specific enough that a developer could use them to directly improve Forge.

Bad output:

- “Many repos use React.”
- “There are some shared conventions.”

Good output:

- “5 of 7 frontend-capable repos use Next.js App Router with TypeScript strict mode, Tailwind, and a `src/components` + `src/lib` split; this should remain Forge’s default frontend scaffold.”
- “3 repos pair FastAPI with Pydantic settings, Ruff, and pytest; Docker is present in 2 of those 3, so Docker should be optional but strongly suggested for API recipes.”

## Final Summary

When the files are complete, provide a concise summary that includes:

- how many repos were analyzed
- the top stack families discovered
- the top conventions Forge should adopt
- the highest-value Forge changes recommended
- any major uncertainties

Do not edit Forge source code yet unless explicitly asked. This task is research and synthesis only.
```
