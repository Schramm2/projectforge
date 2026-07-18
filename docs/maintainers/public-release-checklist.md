# Public Release Checklist

ProjectForge's public identity is settled:

- repository: `Schramm2/projectforge`
- distribution and Homebrew formula: `projectforge`
- command: `forge`
- Python import namespace: `ubundiforge` (compatibility constraint)
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

PyPI remains deliberately unpublished. Do not document it as an install route until a future
release publishes and verifies it. The GitHub homepage remains blank by choice; the repository
does not depend on a custom portfolio domain.

## Supported install routes

```bash
uv tool install https://github.com/Schramm2/projectforge/archive/refs/tags/v0.4.1.tar.gz
brew install --build-from-source schramm2/tap/projectforge
```

## Release verification

- Run `uv run python scripts/scan_safety.py`.
- Run `uv run ruff check src/ubundiforge tests`.
- Run `uv run pytest` and investigate any change from the recorded baseline.
- Run `uv build` and inspect wheel/sdist metadata.
- Repeat both public install routes in clean environments.
- Verify `forge --version`, `forge --help`, and the showcase dry run.
- Run the live scaffold script only with an approved, authenticated backend.
- Scan the final diff and tracked files for placeholders, stale identities, credentials, and
  machine-local paths.

The working-tree scanner does not inspect historical commits, reflogs, forks, or hosted release
artifacts. Run a separate history scan before making a broader privacy-clean claim.
