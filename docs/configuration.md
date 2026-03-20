# Configuration

All Forge user configuration lives under `~/.forge/`. This document covers every config file and customization point.

## Config file

**Path:** `~/.forge/config.json`

Created automatically by the setup wizard on first run. Contains:

| Key | Description |
|-----|-------------|
| `backend` | Preferred AI backend (`claude`, `gemini`, or `codex`). Forge falls back to others if unavailable. |
| `editor` | Editor command for opening projects after scaffolding (e.g., `code`, `cursor`, `zed`). |
| `project_dir` | Default parent directory for new projects. |
| `model` | Model preferences per backend (optional overrides). |

To re-run the setup wizard and regenerate this file:

```bash
forge --setup
```

You can also edit the file directly. It is standard JSON.

## Conventions

**Path:** `~/.forge/conventions.md`

A Markdown file injected into every scaffold prompt. Use it to encode your team's standards so every generated project follows them consistently.

Typical contents:

- Coding standards (naming, formatting, patterns).
- Project structure rules (where files go, module boundaries).
- Tool preferences (package managers, linters, test runners).
- Error handling and logging conventions.
- Git workflow expectations (branch naming, commit messages).

If the file does not exist, Forge proceeds without custom conventions. Create it manually or let the setup wizard generate a starter template.

## Design templates

Design templates encode brand guidelines as prompt tokens so AI backends produce visually consistent UIs.

**Built-in template:** `ubundi-brand-guide`

**Override paths (checked in order):**

1. `.forge/design-templates/<name>.md` -- project-local override
2. `~/.forge/design-templates/<name>.md` -- user-level override
3. Built-in templates bundled with Forge

Design templates only apply to stacks that produce frontend output: `nextjs` and `both` (monorepo). They are ignored for backend-only and CLI stacks.

To create a custom design template, write a Markdown file describing your brand: colors, typography, spacing, component patterns, tone of voice. Place it in either override path using a descriptive name (e.g., `my-company-brand.md`).

## Media assets

Media assets are image files (logos, banners, icons) that get copied into scaffolded projects.

**Structure:**

```
media/
  <collection-name>/
    logo.svg
    banner.png
    favicon.ico
    ...
```

During development, the `media/` directory at the repo root is used. In production, specify a collection with the `--media` flag:

```bash
forge --media ~/brand-assets/acme
```

Files from the collection are copied into the generated project's `public/` or `assets/` directory depending on the stack.

## Post-scaffold hooks

**Path:** `~/.forge/hooks/post-scaffold.sh`

A shell script that runs after every successful scaffold. Use it for custom setup steps like installing additional tools, running migrations, or sending notifications.

**Available environment variables:**

| Variable | Description |
|----------|-------------|
| `FORGE_PROJECT_DIR` | Absolute path to the generated project |
| `FORGE_PROJECT_NAME` | Name of the project |
| `FORGE_STACK` | Stack identifier (e.g., `fastapi`, `nextjs`) |
| `FORGE_DEMO_MODE` | `true` or `false` |

The hook must be executable (`chmod +x`) and must exit within 60 seconds or it will be killed.

Example:

```bash
#!/usr/bin/env bash
cd "$FORGE_PROJECT_DIR"
git remote add origin "git@github.com:myorg/${FORGE_PROJECT_NAME}.git"
```

## Scaffold log

**Path:** `~/.forge/scaffold.log`

An append-only JSON-lines file recording every scaffold run. Each line is a JSON object with:

| Field | Description |
|-------|-------------|
| `name` | Project name |
| `stack` | Stack identifier |
| `backends` | List of AI backends used |
| `directory` | Absolute path to the generated project |
| `timestamp` | ISO 8601 timestamp |

This log is never modified or truncated by Forge. Delete or rotate it manually if needed.

## Scaffold manifest

**Path:** `.forge/scaffold.json` (inside every generated project)

Written into every scaffolded project for provenance tracking. Contains:

| Field | Description |
|-------|-------------|
| `forge_version` | Version of Forge that created the project |
| `name` | Project name |
| `stack` | Stack identifier |
| `backends` | AI backends used during generation |
| `routing` | Routing decision details (why a backend was chosen) |
| `design_template` | Design template applied, if any |
| `conventions_hash` | SHA-256 hash of the conventions file at generation time |
| `timestamp` | ISO 8601 timestamp |

This file is committed to the project's git repository. It provides a permanent record of how the project was scaffolded.
