# Homebrew Release

Homebrew is a supported public installation route. The release workflow keeps this repository's
formula synchronized with `Schramm2/homebrew-tap`; v0.5.0 has passed a clean source installation
and `brew test`.

The checked-in formula remains on v0.5.0 until the current unreleased Antigravity-capable source is
versioned and published. Do not describe source-only provider changes as available from Homebrew.

The names are intentionally different:

- distribution and Homebrew formula: `projectforge`
- installed executable: `forge`
- Python import namespace: `ubundiforge` for compatibility

## Repository layout

- formula source: `Formula/projectforge.rb`
- formula generator: `scripts/generate_homebrew_formula.py`
- runtime dependency source: `uv.lock`
- release workflow: `.github/workflows/release-homebrew.yml`
- target tap: `Schramm2/homebrew-tap`

## Workflow prerequisites

- `HOMEBREW_TAP_TOKEN` can write to `Schramm2/homebrew-tap`.
- `HOMEBREW_TAP_REPO` is unset, allowing the workflow default, or contains that exact repository.
- GitHub Actions can write release tags, releases, and the generated formula back to this repo.

## Normal release

1. Bump the version in `pyproject.toml` and `src/ubundiforge/__init__.py`.
2. Update `CHANGELOG.md` and refresh `uv.lock` if dependencies changed.
3. Run the safety scan, documentation and skill validators, Ruff, pytest, `uv build`, and artifact
   inspection from the production-readiness checklist.
4. Run the dry-run smoke command from `.github/workflows/release-homebrew.yml`.
5. Commit and push the release through the repository's normal reviewed branch flow.
6. Confirm the workflow's tap token passed a provider-owned push-permission check before tag
   creation, then confirm
   `Release Homebrew` created the tag and GitHub release, regenerated the
   formula, and synchronized it to `Schramm2/homebrew-tap`.
7. Repeat the clean installation checks below before updating public documentation.

If the tag exists but formula synchronization failed, manually run the workflow with
`sync_only=true`. That mode skips tag and release creation. If the public tap already matches the
newly generated formula byte-for-byte, the run completes as a verified no-op; any mismatch still
requires a token that reports push permission for the configured tap repository.

## Manual formula regeneration

Use a real tag and compute the checksum from the canonical repository. For example:

```bash
TAG=vX.Y.Z
SOURCE_URL="https://github.com/Schramm2/projectforge/archive/refs/tags/${TAG}.tar.gz"
curl -Ls "${SOURCE_URL}" -o /tmp/projectforge-release.tar.gz
SOURCE_SHA256="$(shasum -a 256 /tmp/projectforge-release.tar.gz | awk '{print $1}')"

uv run python scripts/generate_homebrew_formula.py \
  --output Formula/projectforge.rb \
  --source-url "${SOURCE_URL}" \
  --source-sha256 "${SOURCE_SHA256}"
```

Review and commit the source formula. The workflow synchronizes it to:

```text
Schramm2/homebrew-tap/Formula/projectforge.rb
```

Retire a superseded formula only after confirming that the new formula preserves the supported
command and no supported users depend on the old package name.

## Clean verification

```bash
brew install --build-from-source schramm2/tap/projectforge
brew test schramm2/tap/projectforge
forge --version
forge --help
forge --dry-run --name brew-smoke --stack python-cli \
  --description "Homebrew smoke test" --no-docker --no-open --no-verify
```

The checked-in formula must always use a real release archive and its measured checksum. The
generator requires that checksum explicitly so a version bump cannot silently reuse an older one.
For every new release, the workflow must verify actual tap push permission before creating a tag or
GitHub release; checking only that a secret is nonempty is insufficient. A missing or unusable
cross-repository credential is a stop-before-publish condition, not a partial-release mode.
