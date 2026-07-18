# Homebrew Release

Homebrew support is staged but not currently a public installation route. The source repository
contains a `projectforge` formula and generator; `Schramm2/homebrew-tap` still needs the matching
formula and clean-environment verification before user docs may recommend it.

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
- `HOMEBREW_TAP_REPO` is unset (the workflow defaults to `Schramm2/homebrew-tap`) or contains that
  exact repository.
- GitHub Actions can write release tags, releases, and the generated formula back to this repo.

## Normal release

1. Bump the version in `pyproject.toml` and `src/ubundiforge/__init__.py`.
2. Update `CHANGELOG.md` and refresh `uv.lock` if dependencies changed.
3. Run `uv run pytest`, `uv run ruff check src/ubundiforge tests`, and `uv build`.
4. Run the dry-run smoke command from `.github/workflows/release-homebrew.yml`.
5. Commit and push the release through the repository's normal reviewed branch flow.
6. Confirm the `Release Homebrew` workflow created the tag and GitHub release, regenerated the
   formula, and synced it to `Schramm2/homebrew-tap`.

If the tag exists but formula synchronization failed, manually run the workflow with
`sync_only=true`. That mode skips tag and release creation.

## Manual formula regeneration

Use a real tag and compute the checksum from the canonical repository. For example:

```bash
TAG=v0.5.0
SOURCE_URL="https://github.com/Schramm2/projectforge/archive/refs/tags/${TAG}.tar.gz"
curl -Ls "${SOURCE_URL}" -o /tmp/projectforge-release.tar.gz
SOURCE_SHA256="$(shasum -a 256 /tmp/projectforge-release.tar.gz | awk '{print $1}')"

uv run python scripts/generate_homebrew_formula.py \
  --output Formula/projectforge.rb \
  --source-url "${SOURCE_URL}" \
  --source-sha256 "${SOURCE_SHA256}"
```

Review and commit the formula in this repository. The required cross-repository handoff is:

```text
Source: Formula/projectforge.rb
Target: Schramm2/homebrew-tap/Formula/projectforge.rb
Retire after compatibility review: any superseded formula for this command
```

This repository does not authorize that tap edit by itself.

## Verification before public documentation

After the tap change is published, use a clean environment to run:

```bash
brew install --build-from-source Schramm2/homebrew-tap/projectforge
brew test Schramm2/homebrew-tap/projectforge
forge --version
forge --help
forge --dry-run --name brew-smoke --stack python-cli \
  --description "Homebrew smoke test" --no-docker --no-open --no-verify
```

Only then may README and getting-started documentation describe Homebrew as supported.

The checked-in formula must always use a real release archive and its measured checksum. The
generator requires that checksum explicitly so a version bump cannot silently reuse an older one.
