# Homebrew Release Notes

Forge is packaged for Homebrew under the formula name `ubundiforge`.

Why not `forge`?

- Homebrew already has formulae that occupy the `forge` naming space.
- The package name can be `ubundiforge` while the installed executable remains `forge`.

## Repo Layout

- Formula source: `Formula/ubundiforge.rb`
- Formula generator: `scripts/generate_homebrew_formula.py`
- Runtime dependency source of truth: `uv.lock`

## Release Flow

1. Cut a Git tag that matches the package version, for example `v0.1.0`.
2. Publish the source tarball where Homebrew can fetch it, typically:
   `https://github.com/matthewubundi/forge/archive/refs/tags/v0.1.0.tar.gz`
3. Compute the tarball checksum:
   `curl -Ls <tarball-url> | shasum -a 256`
4. Regenerate the formula with the real release URL and checksum:
   `python3 scripts/generate_homebrew_formula.py --source-url <tarball-url> --source-sha256 <sha256>`
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
