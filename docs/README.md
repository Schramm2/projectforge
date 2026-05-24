# Documentation Map

This repo separates product docs, maintainer docs, and reference captures so contributors can find the right source quickly.

Current product truth lives in `guides/`, `maintainers/`, and the code under `src/ubundiforge/`.

## Guides

- [guides/getting-started.md](guides/getting-started.md) — install Forge and run the first scaffold
- [guides/configuration.md](guides/configuration.md) — user config, conventions, hooks, and manifests
- [guides/stacks.md](guides/stacks.md) — supported stack catalog and defaults
- [guides/troubleshooting.md](guides/troubleshooting.md) — common issues and fixes

## Maintainers

- [maintainers/admin-playbook.md](maintainers/admin-playbook.md) — repo maintenance, stack changes, and release flow
- [maintainers/adding-a-stack.md](maintainers/adding-a-stack.md) — concrete implementation checklist for new stacks
- [maintainers/homebrew-release.md](maintainers/homebrew-release.md) — formula and tap release notes
- [maintainers/public-release-checklist.md](maintainers/public-release-checklist.md) — final public identity and privacy checklist
- [maintainers/roadmap.md](maintainers/roadmap.md) — product roadmap and future work

## Reference

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
