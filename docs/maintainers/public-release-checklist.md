# Public Release Checklist

ProjectForge's public identity is settled:

- repository: `Schramm2/projectforge`
- PyPI distribution: `matt-projectforge` (PyPI rejected `projectforge` as too similar)
- Homebrew formula: `projectforge`
- preferred command: `projectforge`
- compatibility command: `forge` (collides with Foundry's Ethereum CLI)
- canonical Python import namespace: `projectforge`
- canonical destination: <https://github.com/Schramm2/projectforge>

## v0.4.1 release status

- [x] Publish the GitHub release with canonical package metadata.
- [x] Synchronize `Formula/projectforge.rb` to `Schramm2/homebrew-tap`.
- [x] Retire the superseded tap formula.
- [x] Verify clean uv archive installation, version, help, and dry-run output.
- [x] Verify clean Homebrew source installation, `brew test`, version, help, and dry-run output.
- [x] Complete an authenticated three-phase scaffold and independently run its lint, test, type,
  and CLI checks.
- [x] Publish the portfolio case study to the default Vercel project URL with no custom domain.
- [x] Scan the public tree and evidence capture for company identity, credentials, and private
  machine paths.

PyPI trusted publishing is configured in the release workflow. For any release, verify the
publisher/environment setup in the [PyPI release runbook](pypi-release.md), explicitly approve the
connected-system publication, and do not describe a version as available there until clean uv and
pipx installs pass. The GitHub homepage remains blank by choice; the repository does not depend on
a custom portfolio domain.

## v0.5.0 release status

- [x] Choose a compatibility-preserving pre-1.0 minor version and write migration-aware notes.
- [x] Complete provider, safety, conventions, resume, verification, docs, CI, package, and skill
  production-readiness work on a reviewed feature branch.
- [x] Pass pre-publication gates and an authenticated end-to-end scaffold on the release candidate.
- [x] Merge the ready PR after hosted CI passes.
- [x] Publish and verify the GitHub release and synchronized Homebrew formula.
- [x] Repeat immutable uv and clean Homebrew installation checks against v0.5.0.

## Current release install routes (verify for the version being published)

```bash
uv tool install matt-projectforge
pipx install matt-projectforge
brew install --build-from-source schramm2/tap/projectforge
```

ProjectForge v0.7.0 includes the canonical `projectforge` Python namespace. Do not describe the
version as available on a distribution channel until its tag, artifacts, and that channel's clean
installation route have passed the release gates below.

## Release verification

- Run `uv run python scripts/scan_safety.py`.
- Run `uv run ruff check src/projectforge tests`.
- Run `uv run pytest` and investigate any change from the recorded baseline.
- Run `uv build` and inspect wheel/sdist metadata.
- Repeat the PyPI uv, PyPI pipx, and Homebrew install routes in clean environments.
- Verify `projectforge --version`, `projectforge --help`, the `forge` compatibility alias, and the
  showcase dry run.
- Run the live scaffold script only with an approved, authenticated backend.
- Scan the final diff and tracked files for placeholders, stale identities, credentials, and
  machine-local paths.

The working-tree scanner does not inspect historical commits, reflogs, forks, or hosted release
artifacts. Run a separate history scan before making a broader privacy-clean claim.
