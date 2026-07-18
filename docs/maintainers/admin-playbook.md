# Admin Playbook

This guide explains how to maintain ProjectForge as an administrator: where organization conventions now live, how to update them safely, how to add new stacks and capabilities, and how to publish a release so future scaffolds pick up the latest bundled behavior.

## Mental model

There are now two ownership surfaces:

1. Canonical bundled conventions, owned in this repository under `conventions/` and shipped in Forge releases.
2. User-owned profiles and overrides under `~/.forge/` or a project's `.forge/` directory.

If the change should become part of the product, edit the bundled `conventions/` tree in this repo and ship a release.

If the change is user-specific, use `forge conventions` profiles. For a one-project exception, use
`.forge/conventions.md`. Effective order is bundled defaults, selected profile, user-wide override,
then project-local override.

## The canonical conventions tree

Forge now builds prompt-ready convention bundles from this layered source tree:

```text
conventions/
  global/
  languages/
  stacks/
  prompts/
  manifests/
```

- Markdown files hold the human-readable standards.
- Metadata files define inheritance and ordering.
- Manifests define prompt bundle composition and browse labels.

Use the admin command to inspect the system:

```bash
forge admin conventions --validate
forge admin conventions --preview-stack fastapi
forge admin conventions --history global
forge admin conventions --open global/python-standards.md
```

## Normal admin flow: updating Python conventions

If you want to change how Python code is scaffolded:

1. Run `forge admin conventions --preview-stack fastapi` to inspect the current compiled Python-facing bundle.
2. Open the source Markdown file that currently owns the Python defaults, usually:
   - `conventions/global/python-standards.md`
   - `conventions/global/python-architecture.md`
3. Edit the Markdown directly in the repo.
4. If Python conventions later move into language-layer files, update the matching metadata file under:
   - `conventions/languages/python/metadata.yaml`
5. Validate the tree:
   - `forge admin conventions --validate`
6. Preview one or more affected stacks again:
   - `forge admin conventions --preview-stack fastapi`
   - `forge admin conventions --preview-stack python-worker`
7. Inspect recent changes if needed:
   - `forge admin conventions --history python`
8. Commit the repo change and ship it in the next Forge release.

Use the language layer for broad Python standards such as typing, imports, testing posture, or packaging defaults. Use a stack layer when the rule is specific to a stack such as FastAPI routing, worker structure, or monorepo conventions.

## Where to edit bundled behavior

### Conventions content

Edit the bundled `conventions/` tree for:

- coding standards
- project structure rules
- stack-specific implementation patterns
- prompt bundle composition

### Prompt assembly and compatibility

Relevant code lives in:

- `src/ubundiforge/convention_registry.py`
- `src/ubundiforge/convention_compiler.py`
- `src/ubundiforge/convention_admin.py`
- `src/ubundiforge/convention_history.py`
- `src/ubundiforge/conventions.py`

`src/ubundiforge/conventions.py` now acts mainly as the compatibility loader for bundled bundles plus legacy local overrides.

### Frontend brand and design direction

If you want to change the default visual language for frontend scaffolds, update:

- `src/ubundiforge/design_templates.py`
- `src/ubundiforge/templates/design-templates/default-design-guide.md`

If you want to add a new selectable design template, add it to `DESIGN_TEMPLATE_OPTIONS` and bundle a matching template file.

## Important behavior: local overrides still exist

Forge composes user-owned layers after bundled sources:

1. selected `~/.forge/profiles/<name>.md`
2. `~/.forge/conventions.md` compatibility override
3. `.forge/conventions.md` project override

Those are compatibility paths and should not be treated as the repo-admin source of truth.

In practice:

- Bundled `conventions/` changes affect local development in this repo immediately.
- Everyone else gets those bundled changes on the next Forge release.
- Local `.forge/` overrides can still take precedence for a specific project or machine.

## Adding a new stack

Use [adding-a-stack.md](adding-a-stack.md) as the implementation checklist.

In practice, a new stack usually requires changes in all of these places:

- `src/ubundiforge/stacks.py`
  Add the `StackMeta` entry.
- `src/ubundiforge/prompts.py`
  Add the interactive menu choice.
- `src/ubundiforge/router.py`
  Add the stack's scaffold phases.
- `src/ubundiforge/prompt_builder.py`
  Add the human-readable stack label.
- `src/ubundiforge/cli.py`
  Add CLI aliases.
- `src/ubundiforge/scaffold_options.py`
  Add CI support and optional auth support if applicable.
- `tests/`
  Add or update tests for routing, prompt generation, CLI parsing, and options.

After making the code changes, verify with:

```bash
uv run pytest
uv run ruff check .
./forge --dry-run --name test-project --stack <new-stack> --description "test scaffold"
```

## Adding new conventions or capabilities

Use this rough rule of thumb:

- Edit `conventions/` for bundled convention content.
- Edit `src/ubundiforge/stacks.py` for stack structures, libraries, commands, services, and env hints.
- Edit `src/ubundiforge/scaffold_options.py` for auth and CI options.
- Edit `src/ubundiforge/design_templates.py` and bundled templates for visual/brand direction.
- Edit `src/ubundiforge/prompt_builder.py` if the prompt contract itself should change.
- Edit `src/ubundiforge/router.py` if certain work should route to different AI backends.
- Edit `src/ubundiforge/verify.py` if scaffolds should be validated differently.

## Release workflow

Once the repo changes are ready, publish them as a new Forge release.

### 1. Update the version

Bump the version in both files:

- `pyproject.toml`
- `src/ubundiforge/__init__.py`

These must stay in sync.

### 2. Update locked dependencies if needed

If you changed runtime dependencies, refresh `uv.lock` before generating the Homebrew formula.

Homebrew resource blocks are generated from `uv.lock`, not maintained by hand.

### 3. Verify locally

Run:

```bash
uv run python scripts/scan_safety.py
uv run python scripts/check_docs.py
uv run python scripts/validate_forge_skill.py
uv run ruff check src/ubundiforge tests
uv run pytest
uv build
uv run python scripts/inspect_artifacts.py
```

If you changed stack behavior, also run a dry-run smoke test:

```bash
./forge --dry-run --name release-smoke --stack fastapi --description "release smoke test"
./forge admin conventions --validate
```

### 4. Merge the reviewed release change

Use the repository's normal reviewed branch flow. Do not bypass review by committing directly to
`main` unless a maintainer explicitly authorizes it.

The Homebrew release workflow first verifies tap publication authorization, then handles the rest:

- creates `vX.Y.Z` if it does not already exist
- creates the GitHub release
- regenerates `Formula/projectforge.rb`
- commits the updated formula back to this repo
- syncs the formula into the Homebrew tap repo

See `docs/maintainers/homebrew-release.md` for the Homebrew release runbook, including the release steps, expected workflow behavior, verification checks, and the `sync_only=true` recovery flow.

If an unexpected post-tag failure occurs before formula or tap synchronization completes, re-run
`.github/workflows/release-homebrew.yml` manually with `sync_only=true`. Missing tap authorization
must fail before the tag is created.

### 5. Manual fallback

If automation is unavailable, you can still run the old manual flow.

#### Compute the release tarball checksum

Example for a planned `v0.5.0` release:

```bash
TAG=v0.5.0
SOURCE_URL="https://github.com/Schramm2/projectforge/archive/refs/tags/${TAG}.tar.gz"
curl -Ls "${SOURCE_URL}" -o /tmp/projectforge-release.tar.gz
SOURCE_SHA256="$(shasum -a 256 /tmp/projectforge-release.tar.gz | awk '{print $1}')"
echo "${SOURCE_SHA256}"
```

Save the resulting SHA-256 value.

#### Regenerate the Homebrew formula

Run:

```bash
uv run python scripts/generate_homebrew_formula.py \
  --output Formula/projectforge.rb \
  --source-url "${SOURCE_URL}" \
  --source-sha256 "${SOURCE_SHA256}"
```

This updates:

- `Formula/projectforge.rb`

#### Commit the updated formula in this repo

Commit the regenerated formula so the main repo reflects the exact release metadata that was published.

#### Sync the formula into the Homebrew tap repo

Copy or sync `Formula/projectforge.rb` to
`Schramm2/homebrew-tap/Formula/projectforge.rb`.

The tap repo is what Homebrew users install from.

#### Validate the tap

In the tap context, run:

```bash
brew install --build-from-source Schramm2/homebrew-tap/projectforge
brew test Schramm2/homebrew-tap/projectforge
```

#### Push the tap update

Once validation passes, commit and push the tap repo change.

At that point:

- new installs get the new version
- existing users get it after `brew update && brew upgrade projectforge`

## Quick checklist

For a normal admin release:

1. Update conventions, stacks, prompts, templates, or routing in this repo.
2. Bump version in `pyproject.toml` and `src/ubundiforge/__init__.py`.
3. Refresh `uv.lock` if dependencies changed.
4. Run tests and a dry-run scaffold.
5. Merge the reviewed feature/release PR through the hosted workflow.
6. Confirm the credential preflight and release workflow tagged, released, and updated both formulas.

## Future improvement ideas

If maintaining Forge becomes a regular admin workflow, the next useful improvements would be:

- a single release script that bumps versions, checks sync, and regenerates the formula
- a separate command for refreshing user conventions from the latest bundled defaults
- CI automation that opens a PR against the Homebrew tap after a tagged release
