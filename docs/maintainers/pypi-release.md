# PyPI Release

ProjectForge is prepared for PyPI trusted publishing so users can install the distribution without
a GitHub archive URL:

```bash
uv tool install matt-projectforge
# or
pipx install matt-projectforge
```

The package installs `projectforge` as the preferred collision-free command and `forge` as a
compatibility alias. The `forge` alias can collide with Foundry's Ethereum CLI.

## One-time trusted-publisher setup

Before the first publication, configure a pending trusted publisher for the
`matt-projectforge` project in PyPI with these exact values:

- owner: `Schramm2`
- repository: `projectforge`
- workflow: `release-homebrew.yml`
- environment: `pypi`

Protect the GitHub `pypi` environment with the repository's normal release approval policy. Do not
add a long-lived PyPI API token: the workflow requests a short-lived OIDC publishing credential.
This hosted setup and the first publication are connected-system actions and must be explicitly
approved by the maintainer.

## Release behavior

`.github/workflows/release-homebrew.yml` runs the existing safety, docs, lint, test, build,
artifact, GitHub release, and Homebrew synchronization gates first. Only a newly created release
continues to the `publish-pypi` job. That job:

1. checks out the immutable release tag;
2. rebuilds and inspects the wheel and source distribution;
3. publishes through PyPI trusted publishing.

Existing-tag and Homebrew `sync_only` runs do not publish to PyPI. A failed Homebrew release job
also blocks PyPI publication.

## Verification

Do not advertise a version as available from PyPI until all of these pass against an isolated tool
directory:

```bash
python -m pip index versions matt-projectforge

UV_TOOL_DIR=/tmp/projectforge-pypi/tools \
UV_TOOL_BIN_DIR=/tmp/projectforge-pypi/bin \
UV_CACHE_DIR=/tmp/projectforge-pypi/cache \
  uv tool install --python 3.12 --no-config matt-projectforge

/tmp/projectforge-pypi/bin/projectforge --version
/tmp/projectforge-pypi/bin/projectforge --help
/tmp/projectforge-pypi/bin/forge --version
```

Also verify `pipx install matt-projectforge` in a clean environment and confirm that package metadata,
project URLs, bundled conventions, and the operator skill match the release tag. PyPI versions are
immutable; publish a new version rather than replacing a bad artifact.
