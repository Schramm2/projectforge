# Public Release Checklist

ProjectForge's public identity is settled:

- repository: `Schramm2/projectforge`
- distribution: `projectforge`
- command: `forge`
- Python import namespace: `ubundiforge` (compatibility constraint)
- public destination: <https://github.com/Schramm2/projectforge>

## Supported today

The only supported public install route is:

```bash
uv tool install git+https://github.com/Schramm2/projectforge.git@v0.4.1
```

This route uses an immutable tag carrying the canonical `projectforge` distribution metadata.
Do not advertise PyPI or Homebrew until the corresponding channel is tested from a clean
environment.

## External release actions still required

1. Confirm the release workflow published `v0.4.1` with `projectforge` metadata and canonical
   project URLs.
2. In `Schramm2/homebrew-tap`, add `Formula/projectforge.rb` from this repository and remove any
   superseded formula after confirming no supported users depend on it.
3. Test `brew install Schramm2/homebrew-tap/projectforge` and `brew test
   Schramm2/homebrew-tap/projectforge` in a clean environment before documenting Homebrew as
   supported.
4. Decide whether to publish `projectforge` to PyPI. If published, test the exact index-backed
   install before adding it to user docs.
5. After the case study is live, set the GitHub repository homepage to
   <https://mattschramm.com/work/projectforge>. Until then, keep public links on the repository
   rather than publishing a dead portfolio URL.
6. Capture a real 30–60 second terminal demo from an operator-approved, authenticated backend.

Record each completed external check in the showcase verification report.

## Release verification

- Run `python scripts/scan_safety.py`.
- Run `uv run ruff check src/ubundiforge tests`.
- Run `uv run pytest` and investigate any change from the recorded baseline.
- Run `uv build` and inspect wheel/sdist metadata.
- Repeat the GitHub-backed install in an empty uv tool directory.
- Verify `forge --version`, `forge --help`, and the showcase dry run.
- Run the live scaffold script in `docs/showcase/terminal-demo.sh` only with an approved,
  authenticated backend.
- Scan the final diff and tracked files for placeholders, stale identities, credentials, and
  machine-local paths.

The tracked working-tree scanner does not inspect historical commits, reflogs, forks, or hosted
release artifacts. Run a separate history scan before making a broader privacy-clean claim.
