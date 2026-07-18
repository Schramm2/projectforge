# Showcase Verification Report

Verified on 2026-07-18 from macOS with Python 3.12 and uv 0.9.22.

## Public identity and release channels

Read-only live checks reported:

```text
repository: Schramm2/projectforge
visibility: public
default branch: main
GitHub homepage field: pending case-study publication
target release: v0.4.1
PyPI projectforge JSON endpoint: HTTP 404
Homebrew tap: release verification pending
```

Decision: use the GitHub-backed uv install as the only supported public route. Keep the repository
as the current public destination. After the case study is live, use
`https://mattschramm.com/work/projectforge` as both the GitHub homepage and portfolio destination.

## Clean installation

Command, with uv's tool, bin, and cache directories pointing at an empty directory:

```bash
UV_TOOL_DIR=/tmp/projectforge-clean-install/tools \
UV_TOOL_BIN_DIR=/tmp/projectforge-clean-install/bin \
UV_CACHE_DIR=/tmp/projectforge-clean-install/cache \
uv tool install --python 3.12 --no-config \
  git+https://github.com/Schramm2/projectforge.git@v0.4.1
```

Relevant output:

```text
Updated https://github.com/Schramm2/projectforge.git
Built projectforge
projectforge==0.4.1
Installed 1 executable: forge
```

## Installed CLI

```bash
forge --version
forge --help
```

Relevant output:

```text
projectforge 0.4.1
Usage: forge [OPTIONS] COMMAND [ARGS]...
```

The help output listed `stats`, `evolve`, `check`, `replay`, and `admin`.

Credential-free prompt check:

```bash
forge --dry-run \
  --name portfolio-smoke \
  --stack python-cli \
  --description "A tiny greeting CLI used to verify ProjectForge installation" \
  --no-docker \
  --no-open \
  --no-verify
```

Measured result: exit 0; rendered a three-phase routing plan and prompt preview with bundled
conventions loaded. No project directory was created.

## Live scaffold boundary

The authenticated live scaffold is run only with explicit operator approval and an authenticated
backend. Its final status and artifact checks are recorded here after the run.

Attempted command:

```bash
cd /tmp
/tmp/projectforge-clean-install/bin/forge \
  --use codex \
  --model gpt-5.4-mini \
  --name forge-proof-cli \
  --stack python-cli \
  --description "A tiny greeting CLI used as reproducible ProjectForge portfolio evidence" \
  --no-docker \
  --no-ci \
  --no-open \
  --verify \
  --no-agents \
  --extra "Keep the scaffold minimal. Implement a greet command, tests, Ruff configuration, and no network-dependent runtime behavior."
```

The checked-in [generated-project](generated-project/) is verified separately below. The
operator-run proof uses [terminal-demo.sh](terminal-demo.sh) and records the real manifest and
terminal capture without inventing output.

## Staging Homebrew formula

Command:

```bash
curl -sSfL \
  https://github.com/Schramm2/projectforge/archive/refs/tags/v0.4.1.tar.gz \
  -o /tmp/projectforge-v0.4.1.tar.gz
shasum -a 256 /tmp/projectforge-v0.4.1.tar.gz
```

Measured checksum:

```text
Recorded after the release tag is published.
```

This repairs the checked-in formula's repository identity but does not make Homebrew a supported
route. The separate tap still requires the handoff in
[the Homebrew runbook](../maintainers/homebrew-release.md).

## Repository verification

Final results are recorded after the implementation is complete:

```text
public-safety scan: PASS (168 tracked and prospective public files)
Ruff: PASS (src/ubundiforge and tests)
pytest: PASS (413 tests; audited baseline 409 plus four identity, release, and scanner regressions)
package build: PASS (projectforge-0.4.1.tar.gz and projectforge-0.4.1-py3-none-any.whl)
generated-project install/lint/test/CLI: PASS (1 test; `Hello, Ada!`)
```

Commands:

```bash
.venv/bin/python scripts/scan_safety.py
.venv/bin/ruff check src/ubundiforge tests
.venv/bin/pytest
uv build --out-dir /tmp/projectforge-build-20260718

cd docs/showcase/generated-project
uv sync --dev
.venv/bin/ruff check .
.venv/bin/pytest -q
.venv/bin/hello-forge --name Ada
```

The full suite passed all 413 tests with no checks skipped or weakened.

Wheel metadata was inspected and reported `Name: projectforge`, the four canonical GitHub project
URLs, `forge = ubundiforge.__main__:main`, and the expected bundled conventions. Regenerating the
formula with the measured archive URL and checksum produced a byte-for-byte match with
`Formula/projectforge.rb`.
