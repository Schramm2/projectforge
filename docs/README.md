# Documentation Map

This repo separates product docs, maintainer docs, and reference captures so contributors can find the right source quickly.

Current source behavior is documented in `guides/`, the live maintainer runbooks and roadmap, and
the code under `src/ubundiforge/`. Dated evidence, completed release plans, changelog entries, and
provider prompt captures remain intentionally historical. Each historical document should state
its evidence or release boundary rather than being rewritten to match current source.

ProjectForge v0.6.0 includes PyPI publishing, the collision-free command alias, and the P1 product
audit improvements. Older tags and their bundled
documentation remain the authority for the immutable Gemini-backed releases.

## Guides

- [guides/getting-started.md](guides/getting-started.md) — install Forge and run the first scaffold
- [guides/configuration.md](guides/configuration.md) — user config, conventions, hooks, and manifests
- [guides/security-privacy.md](guides/security-privacy.md) — provider, workspace, local-data, and unsafe-mode boundaries
- [guides/migrating-from-0.4.1.md](guides/migrating-from-0.4.1.md) — compatibility and migration notes
- [guides/stacks.md](guides/stacks.md) — supported stack catalog and defaults
- [guides/troubleshooting.md](guides/troubleshooting.md) — common issues and fixes
- [showcase/README.md](showcase/README.md) — measured portfolio evidence and terminal demo flow

## Maintainers

- [maintainers/admin-playbook.md](maintainers/admin-playbook.md) — repo maintenance, stack changes, and release flow
- [maintainers/adding-a-stack.md](maintainers/adding-a-stack.md) — concrete implementation checklist for new stacks
- [maintainers/homebrew-release.md](maintainers/homebrew-release.md) — formula and tap release notes
- [maintainers/pypi-release.md](maintainers/pypi-release.md) — trusted-publishing setup and verification
- [maintainers/public-release-checklist.md](maintainers/public-release-checklist.md) — final public identity and privacy checklist
- [maintainers/roadmap.md](maintainers/roadmap.md) — product roadmap and future work
- [maintainers/provider-compatibility.md](maintainers/provider-compatibility.md) — dated official sources and runtime provider evidence
- [maintainers/production-readiness-plan.md](maintainers/production-readiness-plan.md) — release gates and evidence status
- [maintainers/production-readiness-evidence.md](maintainers/production-readiness-evidence.md) — dated authenticated scaffold and provider evidence
- [maintainers/skill-behavioral-evidence.md](maintainers/skill-behavioral-evidence.md) — shipped skill RED/GREEN forward tests

## Reference

- [reference/prompts/](reference/prompts/) — provider-specific prompting reference material
- [claude-md-template.md](claude-md-template.md) — project-level `CLAUDE.md` authoring template
- [reference/README.md](reference/README.md) — how to use reference snapshots safely

## Skills

- [skills/forge-scaffold/SKILL.md](../skills/forge-scaffold/SKILL.md) — portable skill that teaches AI agents how to use the Forge command surface professionally

## Diagrams

- [diagrams/forge-flow.md](diagrams/forge-flow.md) - overview and map of the diagram set
- [diagrams/forge-input-flow.md](diagrams/forge-input-flow.md) - setup wizard, questionnaire, smart defaults, and review loop
- [diagrams/forge-routing-and-execution.md](diagrams/forge-routing-and-execution.md) - routing logic, phase merging, and execution order
- [diagrams/forge-prompt-assembly.md](diagrams/forge-prompt-assembly.md) - prompt inputs, variants, and phase-specific assembly
- [diagrams/forge-runtime-pipeline.md](diagrams/forge-runtime-pipeline.md) - module-level scaffold pipeline and post-scaffold outputs
