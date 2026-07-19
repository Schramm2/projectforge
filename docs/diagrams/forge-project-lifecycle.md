# Project lifecycle

A Forge-managed project keeps enough local evidence to recover an interrupted scaffold, verify a created project, and support later changes.

![Lifecycle of a Forge-managed project](forge-project-lifecycle.svg)

[Edit the D2 source](forge-project-lifecycle.d2).

## Outcome states

- **Provider phase interrupted:** preserve the target, fix readiness, and repeat the original command with `--resume`.
- **Project Created:** generation finished, but verification was skipped, incomplete, or failed.
- **Project Ready:** every required verification check passed.

Live scaffolds create an unborn `main` Git repository before provider execution so every provider
works inside the same trusted boundary. Completion writes verification and presentation artifacts,
runs the optional hook, and commits any remaining generated changes before reporting the outcome.

After handoff, `forge evolve` adds supported capabilities, `forge check` audits convention drift,
`forge replay` reproduces or compares the original scaffold, and `forge stats` reports local
outcomes.
