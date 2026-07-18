# Contributing

ProjectForge is maintained as a production-focused developer tool. The goal of this repo is to stay easy to navigate, easy to release, and safe to evolve.

## Local setup

```bash
uv sync --dev
uv run python scripts/scan_safety.py
uv run python scripts/check_docs.py
uv run python scripts/validate_forge_skill.py
uv run ruff check src/projectforge tests
uv run pytest
uv build
uv run python scripts/inspect_artifacts.py
```

## Repo layout

- `src/projectforge/` contains the shipped CLI package.
- `tests/` contains the automated test suite and prompt snapshots.
- `conventions/` contains the bundled convention layers and manifests.
- `docs/guides/` contains user-facing product documentation.
- `docs/maintainers/` contains release and repo-maintenance playbooks.
- `docs/reference/` contains dated or upstream reference snapshots, not product truth.
- `skills/forge-scaffold/` contains the shipped agent operator skill.
- `scripts/` contains repository validators and release utilities.
- `Formula/` contains the generated Homebrew formula.
- `.github/workflows/` defines CI and release automation.

## Development workflow

1. Make the smallest coherent change that solves the problem.
2. Keep docs in sync when behavior, flags, stacks, or release steps change.
3. Prefer adding or updating tests alongside product changes.
4. Run the relevant checks above before asking for review.

## Documentation standards

- Put end-user guidance in `docs/guides/`.
- Put repeatable maintainer procedures in `docs/maintainers/`.
- Label dated evidence and historical release records explicitly; do not rewrite them as current
  behavior.
- Keep current-source instructions distinct from immutable release instructions when unreleased
  behavior differs from the latest tag.
- Keep filenames lowercase and kebab-case unless an upstream source format needs to be preserved.

## Release and stack changes

- For release steps, use [docs/maintainers/admin-playbook.md](docs/maintainers/admin-playbook.md).
- For Homebrew-specific publishing, use [docs/maintainers/homebrew-release.md](docs/maintainers/homebrew-release.md).
- For adding a supported stack, use [docs/maintainers/adding-a-stack.md](docs/maintainers/adding-a-stack.md).
