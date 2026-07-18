# Trust boundaries

A live scaffold crosses from the developer's machine into a provider-owned CLI and service. Preview and export do not cross that boundary.

![ProjectForge security, privacy, and evidence boundaries](forge-trust-boundaries.svg)

[Edit the D2 source](forge-trust-boundaries.d2).

## Boundary rules

- `--dry-run` and `--export` start no provider process.
- `--approval-mode safe` is the normal live mode and uses each provider's bounded workspace controls.
- `--approval-mode plan` still calls a provider but requests read-only planning.
- `--approval-mode unsafe --allow-unsafe` removes provider boundaries and requires isolation you control.
- Provider credentials and account identity remain with the provider CLI.
- `.forge/conventions-snapshot.md` may contain private guidance. Keep it out of public issues and external messages.
- A successful provider exit is not a verified project. Required local checks determine whether the dashboard reports `Project Ready`.

See [Security and Privacy](../guides/security-privacy.md) for the complete operating guidance.
