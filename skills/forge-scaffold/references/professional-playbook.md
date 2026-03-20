# Professional Forge Playbook

## What Forge Actually Does

Forge is an orchestration CLI, not a hand-coded template engine. It gathers project inputs, injects conventions and stack metadata into a structured prompt, and then delegates scaffold phases to AI CLIs.

Default specialist routing:

- architecture -> `claude`
- frontend -> `gemini`
- tests -> `codex`
- verify -> `claude`

This means a high-quality Forge workflow is mostly about:

1. choosing the right stack and options
2. shaping the brief carefully
3. deciding when to preview the prompt
4. checking the resulting scaffold instead of assuming it is perfect

## Brief-Writing Rules

Write the description as a sharp product brief, not a vague idea dump.

Good:

- "Customer support portal with authenticated tickets, searchable conversations, and an analytics overview."
- "Retrieval API for internal knowledge documents with pgvector-backed semantic search."

Weak:

- "Build something cool."
- "Maybe like a dashboard with AI and auth and some admin stuff."

Use `--extra` for important constraints that are not already captured by:

- stack choice
- Docker toggle
- auth provider
- design template
- CI template or actions
- services

## Prompt-Inspection Strategy

Use `--dry-run` or `--export` before a real scaffold when:

- the project is important enough to justify a review pass
- the brief includes nuanced architecture constraints
- you are combining multiple structured options
- you want to compare specialist routing with a forced backend via `--use`

Inspect for:

- correct stack label
- correct auth, CI, design-template, and media blocks
- meaningful extra instructions
- the expected phase routing

## Verification Strategy

Keep `--verify` on for real scaffolds unless there is a strong reason not to. Forge verification attempts dependency install, then stack-specific lint, typecheck, build, test, and health checks where applicable.

If verification fails:

1. inspect the first failing check
2. fix the generated project rather than rerunning blindly
3. rerun the relevant project command locally

## Project Files Worth Inspecting

After scaffolding, inspect:

- `.forge/scaffold.json` for provenance
- `README.md` for run instructions
- `CLAUDE.md` for assistant guidance quality
- `agent_docs/` for progressive-disclosure coverage
- `.env.example` for realism and completeness

## Important Implementation Caveats

Prefer observed code behavior over older docs:

- Project-local conventions at `.forge/conventions.md` override `~/.forge/conventions.md`.
- Design templates can be overridden from `.forge/design-templates/` or `~/.forge/design-templates/`.
- Prompt-only modes skip setup and installed-backend checks, which makes them ideal for review workflows.
- Current code resolves media collections from Forge's `media/` directory even though some docstrings still mention `~/.forge/media/`.
- Current code loads the bundled `claude-md-template.md`; it does not expose the older global override path described in some docs.

## Quality Heuristics For Exceptional Scaffolds

- Favor precise stack and option selection over long `--extra` instructions.
- Use specialist routing unless you need a deliberate backend experiment.
- Keep demo mode on so the scaffold starts cleanly without real secrets.
- Ask Forge for a strong starter project, not a bloated pseudo-product.
- After scaffold generation, continue with a normal coding pass if the user wants the result polished beyond the starter level.
