# Configuration

All Forge user configuration lives under `~/.forge/`. This document covers every config file and customization point.

## Config file

**Path:** `~/.forge/config.json`

Created automatically by the setup wizard on first run. Contains:

| Key | Description |
|-----|-------------|
| `preferred_editor` | Editor command Forge tries first when opening the generated project. |
| `available_backends` | Backends that were detected during setup. |
| `backend_models` | Optional model overrides keyed by backend name. |
| `docker_available` | Whether Docker was available during setup. |
| `projects_dir` | Default parent directory for new projects. |

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

If the file does not exist, Forge creates a starter template automatically the first time conventions are loaded.

## Design templates

Design templates encode brand guidelines as prompt tokens so AI backends produce visually consistent UIs.

**Built-in template:** `ubundi-brand-guide`

**Override paths (checked in order):**

1. `.forge/design-templates/<template-id>.md` -- project-local override
2. `~/.forge/design-templates/<template-id>.md` -- user-level override
3. Built-in templates bundled with Forge

Design templates only apply to stacks that produce frontend output: `nextjs` and `both` (monorepo). They are ignored for backend-only and CLI stacks.

Today, Forge exposes one selectable design template id: `ubundi-brand-guide`. To customize it without changing code, create an override file at either `.forge/design-templates/ubundi-brand-guide.md` or `~/.forge/design-templates/ubundi-brand-guide.md`.

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

Forge currently reads media collections from the repo's top-level `media/` directory. The `--media` flag takes a collection name, not an arbitrary filesystem path:

```bash
forge --media ubundi_assets
```

If exactly one collection exists, Forge auto-selects it unless you pass `--no-media`.

Files from the selected collection are copied into the generated project's static asset directory depending on the stack:

- `nextjs` -> `public/`
- `fastapi` / `fastapi-ai` -> `static/`
- `both` -> `frontend/public/`
- `python-cli`, `ts-package`, `python-worker` -> `assets/`

## Post-scaffold hooks

**Path:** `~/.forge/hooks/post-scaffold.sh`

A shell script that runs after every successful scaffold. Use it for custom setup steps like installing additional tools, running migrations, or sending notifications.

**Available environment variables:**

| Variable | Description |
|----------|-------------|
| `FORGE_PROJECT_DIR` | Absolute path to the generated project |
| `FORGE_PROJECT_NAME` | Name of the project |
| `FORGE_STACK` | Stack identifier (e.g., `fastapi`, `nextjs`) |
| `FORGE_DEMO_MODE` | `1` when demo mode is enabled, otherwise `0` |

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
| `demo_mode` | Whether demo mode was enabled |
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
| `description` | Project description provided by the user |
| `backends` | AI backends used during generation |
| `routing` | Phase-to-backend mapping used for the scaffold |
| `model_override` | Explicit `--model` value, when provided |
| `backend_models` | Per-backend model preferences from config |
| `design_template` | Design template applied, if any |
| `media_collection` | Imported media collection, if any |
| `auth_provider` | Auth provider requested, if any |
| `demo_mode` | Whether demo mode was enabled |
| `conventions_hash` | SHA-256 hash of the conventions file at generation time |
| `timestamp` | ISO 8601 timestamp |

This file is committed to the project's git repository. It provides a permanent record of how the project was scaffolded.
