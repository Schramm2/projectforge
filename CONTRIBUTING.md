# Contributing

UbundiForge is maintained as a production-focused internal developer tool. The goal of this repo is to stay easy to navigate, easy to release, and safe to evolve.

## Local setup

```bash
uv sync --dev
uv run pytest
uv run ruff check .
```

## Repo layout

- `src/ubundiforge/` contains the shipped CLI package.
- `tests/` contains the automated test suite and prompt snapshots.
- `docs/guides/` contains user-facing product documentation.
- `docs/maintainers/` contains release and repo-maintenance playbooks.
- `docs/internal/` contains working specs and internal research prompts.
- `docs/reference/` contains captured CLI/reference material that informs Forge behavior.
- `research/` contains exploratory repo archaeology and discovery outputs.
- `assets/` contains README and documentation imagery.
- `media/` is for sample media collections used during development.

## Development workflow

1. Make the smallest coherent change that solves the problem.
2. Keep docs in sync when behavior, flags, stacks, or release steps change.
3. Prefer adding or updating tests alongside product changes.
4. Run lint and tests before asking for review.

## Documentation standards

- Put end-user guidance in `docs/guides/`.
- Put repeatable maintainer procedures in `docs/maintainers/`.
- Put temporary or research-oriented material in `docs/internal/` or `research/`.
- Keep filenames lowercase and kebab-case unless an upstream source format needs to be preserved.

## Release and stack changes

- For release steps, use [docs/maintainers/admin-playbook.md](docs/maintainers/admin-playbook.md).
- For Homebrew-specific publishing, use [docs/maintainers/homebrew-release.md](docs/maintainers/homebrew-release.md).
- For adding a supported stack, use [docs/maintainers/adding-a-stack.md](docs/maintainers/adding-a-stack.md).
