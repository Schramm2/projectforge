# Homebrew Release

Forge is packaged for Homebrew under the formula name `ubundiforge`.

Why not `forge`?

- Homebrew already has formulae that occupy the `forge` naming space.
- The package name can be `ubundiforge` while the installed executable remains `forge`.

## Repo Layout

- Formula source: `Formula/ubundiforge.rb`
- Formula generator: `scripts/generate_homebrew_formula.py`
- Runtime dependency source of truth: `uv.lock`
- Release workflow: `.github/workflows/release-homebrew.yml`

## Prerequisites

This runbook assumes the release workflow is already configured and able to write to both repositories.

- `HOMEBREW_TAP_TOKEN` exists in the source repository Actions secrets.
- If you are not using the defaults, `HOMEBREW_TAP_REPO` and `HOMEBREW_TAP_BRANCH` are set.
- GitHub Actions can write back to `main`.

## Release Steps

Use this path for a normal Homebrew release.

1. Bump the version in both:
   - `pyproject.toml`
   - `src/ubundiforge/__init__.py`
2. Update `CHANGELOG.md` and `uv.lock` if needed.
3. Verify locally:
   - `uv run pytest`
   - `uv run ruff check .`
4. Commit and push the release to `main`:
   - `git add .`
   - `git commit -m "release: vX.Y.Z"`
   - `git push origin main`
5. Open `Actions` -> `Release Homebrew` and confirm the run succeeded.

## What The Workflow Does

On a new version push to `main`, the workflow:

- validates that the version is in sync
- runs lint, tests, build, and a dry-run smoke test
- creates `vX.Y.Z` if the tag does not already exist
- creates the GitHub release
- downloads the release tarball and computes the Homebrew checksum
- regenerates `Formula/ubundiforge.rb`
- commits the updated formula back to this repo
- syncs the formula into the Homebrew tap repo

## Verify The Release

After the workflow completes, confirm:

- the workflow run is green in GitHub Actions
- a new `vX.Y.Z` tag exists
- a GitHub release was created
- [Formula/ubundiforge.rb](/Users/matthew-schramm-ubundi/Desktop/Side%20Projects/forge/Formula/ubundiforge.rb) points at the new tag and checksum
- the tap repo has the same updated formula

## Recovery Run

If the tag already exists but the formula or tap update failed:

1. Open `Actions` -> `Release Homebrew`.
2. Click `Run workflow`.
3. Enable `sync_only`.
4. Run the workflow on `main`.

That mode skips tag and GitHub release creation and only re-syncs the formulas.

## Manual Fallback

1. Cut a Git tag that matches the package version, for example `vX.Y.Z`.
2. Publish the source tarball where Homebrew can fetch it, typically:
   `https://github.com/matthewubundi/UbundiForge/archive/refs/tags/vX.Y.Z.tar.gz`
3. Compute the tarball checksum:
   `curl -Ls <tarball-url> | shasum -a 256`
4. Regenerate the formula with the real release URL and checksum:
   `uv run python scripts/generate_homebrew_formula.py --source-url <tarball-url> --source-sha256 <sha256>`
5. Commit the updated `Formula/ubundiforge.rb`.
6. Copy or sync that file into the Homebrew tap repository, typically `matthewubundi/homebrew-tap`.
7. Validate in the tap:
   `brew install --build-from-source matthewubundi/tap/ubundiforge`
8. Run the tap formula test:
   `brew test matthewubundi/tap/ubundiforge`

## Notes

- The formula uses `virtualenv_install_with_resources`.
- Resource blocks are generated from Forge's locked runtime dependencies, not hand-maintained.
- The formula declares a conflict with `forge` because both install a `forge` executable.
