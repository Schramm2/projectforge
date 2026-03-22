# Documentation Map

This repo separates product docs, maintainer docs, internal working docs, and reference captures so contributors can find the right source quickly.

Current product truth lives in `guides/`, `maintainers/`, and the code under `src/ubundiforge/`. The `internal/` and `reference/` sections are intentionally non-authoritative: they preserve history, research prompts, and upstream snapshots that may drift over time.

## Guides

- [guides/getting-started.md](guides/getting-started.md) — install Forge and run the first scaffold
- [guides/configuration.md](guides/configuration.md) — user config, conventions, hooks, and manifests
- [guides/stacks.md](guides/stacks.md) — supported stack catalog and defaults
- [guides/troubleshooting.md](guides/troubleshooting.md) — common issues and fixes

## Maintainers

- [maintainers/admin-playbook.md](maintainers/admin-playbook.md) — repo maintenance, stack changes, and release flow
- [maintainers/adding-a-stack.md](maintainers/adding-a-stack.md) — concrete implementation checklist for new stacks
- [maintainers/homebrew-release.md](maintainers/homebrew-release.md) — formula and tap release notes
- [maintainers/roadmap.md](maintainers/roadmap.md) — product roadmap and future work

## Internal

- [internal/forge-project-spec.md](internal/forge-project-spec.md) — original product spec and build brief
- [internal/forge-repo-research-prompt.md](internal/forge-repo-research-prompt.md) — prompt for mining existing repos into Forge defaults
- [internal/README.md](internal/README.md) — what counts as archival versus current in internal docs

## Reference

- [reference/cli-tools-help.txt](reference/cli-tools-help.txt) — captured CLI help and invocation notes
- [reference/prompts/](reference/prompts/) — provider-specific prompting reference material
- [claude-md-template.md](claude-md-template.md) — project-level `CLAUDE.md` authoring template
- [reference/README.md](reference/README.md) — how to use reference snapshots safely

## Skills

- [skills/forge-scaffold/SKILL.md](/skills/forge-scaffold/SKILL.md) — portable skill that teaches AI agents how to use all five Forge commands professionally
- [skills/forge-scaffold/README.md](/skills/forge-scaffold/README.md) — human-facing usage and testing guide for the skill

## Diagrams

- [diagrams/forge-flow.md](diagrams/forge-flow.md) - overview and map of the diagram set
- [diagrams/forge-input-flow.md](diagrams/forge-input-flow.md) - setup wizard, questionnaire, smart defaults, and review loop
- [diagrams/forge-routing-and-execution.md](diagrams/forge-routing-and-execution.md) - routing logic, phase merging, and execution order
- [diagrams/forge-prompt-assembly.md](diagrams/forge-prompt-assembly.md) - prompt inputs, variants, and phase-specific assembly
- [diagrams/forge-runtime-pipeline.md](diagrams/forge-runtime-pipeline.md) - module-level scaffold pipeline and post-scaffold outputs
