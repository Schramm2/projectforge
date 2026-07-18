# New user journey

This is the shortest path from a fresh ProjectForge installation to a verified project and ongoing use.

![New ProjectForge user journey from installation to full use](forge-user-journey.svg)

[Edit the D2 source](forge-user-journey.d2).

## How to read it

1. Install ProjectForge through uv, pipx, Homebrew, or a source checkout.
2. Install and authenticate at least one provider CLI, then confirm readiness with `forge doctor`.
3. Complete the first-use setup wizard. Forge saves local defaults but does not copy provider credentials.
4. Preview the scaffold contract with `forge --dry-run`. This starts no provider process.
5. Run the live scaffold in safe mode with verification enabled.
6. Treat `Project Ready` as the handoff gate. It means the required generated-project checks passed.
7. Use `evolve`, `check`, `replay`, `stats`, and `--resume` as the project changes or a run needs recovery.

The interactive command is `forge`. Scripts can provide `--name`, `--stack`, and `--description` to skip the questionnaire while keeping the same routing, safety, and evidence path.
