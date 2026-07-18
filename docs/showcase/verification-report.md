# Showcase Verification Report

Verified on 2026-07-18 from macOS with Python 3.12 and uv 0.9.22.

## Public identity and release channels

| Check | Measured result |
| --- | --- |
| Repository | `Schramm2/projectforge`, public, default branch `main` |
| GitHub release | [v0.4.1](https://github.com/Schramm2/projectforge/releases/tag/v0.4.1), published and not a prerelease |
| Homebrew workflow | [Release Homebrew run 29638625788](https://github.com/Schramm2/projectforge/actions/runs/29638625788), completed successfully on `main` |
| Homebrew tap | `Schramm2/homebrew-tap/Formula/projectforge.rb`, synchronized for v0.4.1 |
| PyPI | `projectforge` JSON endpoint returned HTTP 404; this channel is deliberately unpublished |
| GitHub homepage | Blank by choice; no custom domain is required for this release |
| Portfolio evidence | [ProjectForge case study on Vercel](https://matt-schramm-portfolio-v2-mattschramm1235-gmailcoms-projects.vercel.app/work/projectforge), HTTP 200 |

The supported public install routes are the immutable GitHub archive through uv and the public
Homebrew tap. PyPI is not advertised.

## Clean uv installation

Command, with uv's tool, bin, and cache directories pointing at an empty directory:

```bash
UV_TOOL_DIR=/tmp/projectforge-clean-install/tools \
UV_TOOL_BIN_DIR=/tmp/projectforge-clean-install/bin \
UV_CACHE_DIR=/tmp/projectforge-clean-install/cache \
uv tool install --python 3.12 --no-config \
  https://github.com/Schramm2/projectforge/archive/refs/tags/v0.4.1.tar.gz
```

Measured result: exit 0, `projectforge==0.4.1` built, and one executable named `forge` installed.

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

Measured result: exit 0; Forge rendered a three-phase routing plan and prompt preview with bundled
conventions loaded. No project directory was created.

## Homebrew release and installation

The v0.4.1 source archive checksum is:

```text
6fb78e853864e028e7c929f6e2138424b7d8bb4632b72258ca0355b31e237cd4
```

That checksum and archive URL match `Formula/projectforge.rb` in this repository and the public
tap. The tap retains `Formula/projectforge.rb`; the superseded formula was removed.

Clean-environment checks:

```bash
brew install --build-from-source schramm2/tap/projectforge
brew test schramm2/tap/projectforge
forge --version
```

Measured result: install and formula test passed; the installed command reported
`projectforge 0.4.1`.

## Authenticated live scaffold

The terminal proof used the isolated installer and scaffold flow represented by
[terminal-demo.sh](terminal-demo.sh), with `FORGE_BACKEND=claude` and `FORGE_MODEL=haiku`. The
current script also codifies the independent verification commands used after the captured run.
ProjectForge used Claude Haiku 4.5 for all three phases and wrote the manifest at
`2026-07-18T09:54:04.586177+00:00`.

| Phase | Backend | Exit | Duration |
| --- | --- | ---: | ---: |
| Architecture & Core | Claude | 0 | 550.1 s |
| Tests & Automation | Claude | 0 | 513.2 s |
| Verify & Fix | Claude | 0 | 119.2 s |

The generated repository contained four phase commits ending at
`f394709 chore: integrate multi-phase scaffold and verify all systems`. Independent checks in the
generated repository passed:

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest -q
uv run mypy src tests
uv run hello-forge greet Ada
```

Measured result: Ruff passed, mypy passed, 23 tests passed with 100% coverage, and the CLI printed
`Hello, Ada!` with a party emoji. A privacy scan of the project and terminal capture found no
company, legacy-brand, credential, or machine-local identity strings.

The scaffold took about 20 minutes of backend runtime. The 30–60 second target in the
[shot list](terminal-demo-shot-list.md) is an edited evidence clip, not a generation-time claim.
The Forge dashboard displayed successful phase exits but incorrectly marked its inferred install,
lint, and test health checks as failed; the independent commands above are the authoritative
verification. This display mismatch remains a product follow-up and is not hidden from the
showcase record.

## Repository and deterministic fixture verification

```bash
uv run python scripts/scan_safety.py
uv run ruff check src/ubundiforge tests
uv run pytest
uv build --out-dir /tmp/projectforge-build-20260718

cd docs/showcase/generated-project
uv sync --dev
.venv/bin/ruff check .
.venv/bin/pytest -q
.venv/bin/hello-forge --name Ada
```

Recorded repository result: public-safety scan passed, Ruff passed, all 413 tests passed, and the
source and wheel packages built. The deterministic checked-in fixture passed its install, lint,
single test, and CLI checks. It is intentionally separate from the authenticated 23-test live
scaffold above.

Wheel metadata reported `Name: projectforge`, the canonical GitHub project URLs,
`forge = ubundiforge.__main__:main`, and the expected bundled conventions. Regenerating the formula
with the measured archive URL and checksum produced a byte-for-byte match with
`Formula/projectforge.rb`.

## Privacy boundary

The current public tree contains no standalone company brand, company domain, credentials, or
private workspace paths. The historical Python import namespace remains for compatibility and is
not presented as company branding. This working-tree review does not rewrite or make claims about
historical commits, reflogs, forks, or third-party caches.
