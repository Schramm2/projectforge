# forge-proof-cli

A compact Python CLI fixture used to verify the ProjectForge portfolio flow without runtime
credentials or network access.

This directory is a curated review fixture, not a captured AI-backend result. It intentionally has
no `.forge/scaffold.json`; inventing one would fabricate provenance. The operator-run terminal demo
creates the real generated project and manifest.

## Verify

```bash
uv sync --dev
uv run ruff check .
uv run pytest
uv run hello-forge --name Ada
```

Expected CLI output:

```text
Hello, Ada!
```
