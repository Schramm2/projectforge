# Admin Playbook

This guide explains how to maintain UbundiForge as an administrator: where to update Ubundi conventions, how to add new stacks and capabilities, and how to publish a new Homebrew release so future scaffolds use the latest Forge behavior.

## Mental model

There are two broad kinds of Forge customization:

1. Bundled Forge behavior, which lives in this repository and ships in every new Forge release.
2. User-local overrides, which live in `~/.forge/` or project-local `.forge/` directories on the machine running Forge.

If you want a change to become part of the product for future installs, edit this repository and ship a new Forge version.

If you want a one-off local override for a specific user or project, edit the files under `~/.forge/` or `.forge/` instead.

## What to edit for Ubundi conventions

### Default conventions

Forge creates a starter conventions file from `DEFAULT_CONVENTIONS` in:

- `src/ubundiforge/conventions.py`

This is the built-in Ubundi conventions starter used when `~/.forge/conventions.md` does not already exist.

### Cross-project standards injected into every prompt

Forge also injects shared stack-level standards from:

- `src/ubundiforge/stacks.py`

Specifically, update `CROSS_RECIPE_DEFAULTS` when you want to change the global prompt rules applied to all relevant scaffolds, such as:

- Python packaging and linting defaults
- TypeScript defaults
- Docker defaults
- cross-project architecture rules

### Frontend brand and design direction

If you want to change Ubundi's default visual language for frontend scaffolds, update:

- `src/ubundiforge/design_templates.py`
- `src/ubundiforge/templates/design-templates/ubundi-brand-guide.md`

If you want to add a new selectable design template, add it to `DESIGN_TEMPLATE_OPTIONS` and bundle a matching template file.

## Important behavior: local overrides win

Forge does not blindly force the repo defaults every time it runs.

Convention loading currently works like this:

1. If the current project contains `.forge/conventions.md`, Forge uses that.
2. Otherwise, if `~/.forge/conventions.md` exists, Forge uses that.
3. Otherwise, Forge creates `~/.forge/conventions.md` from the bundled default conventions.

This means a new Forge release does not automatically overwrite an existing user's `~/.forge/conventions.md`.

In practice:

- Changes to `DEFAULT_CONVENTIONS` mostly affect fresh installs and users who do not already have a conventions file.
- Changes to prompt-building logic, stack metadata, routing, bundled design templates, verification rules, and CLI behavior do ship to everyone who upgrades Forge.
- Project-local `.forge/` files can still override global behavior inside a specific scaffold target.

If Ubundi eventually wants centrally managed conventions that always update on upgrade, Forge would need a product change such as:

- merging bundled conventions with user overrides, or
- a migration command that refreshes `~/.forge/conventions.md`

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

- Edit `src/ubundiforge/conventions.py` for starter convention content.
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
uv run pytest
uv run ruff check .
```

If you changed stack behavior, also run a dry-run smoke test:

```bash
./forge --dry-run --name release-smoke --stack fastapi --description "release smoke test"
```

### 4. Commit and tag the release

Example for version `vX.Y.Z`:

```bash
git add .
git commit -m "release: vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

The Git tag must match the package version because the Homebrew formula points at the GitHub release tarball for that tag.

### 5. Compute the release tarball checksum

Example:

```bash
curl -Ls https://github.com/matthewubundi/UbundiForge/archive/refs/tags/vX.Y.Z.tar.gz | shasum -a 256
```

Save the resulting SHA-256 value.

### 6. Regenerate the Homebrew formula

Run:

```bash
uv run python scripts/generate_homebrew_formula.py \
  --source-url https://github.com/matthewubundi/UbundiForge/archive/refs/tags/vX.Y.Z.tar.gz \
  --source-sha256 <sha256>
```

This updates:

- `Formula/ubundiforge.rb`

### 7. Commit the updated formula in this repo

Commit the regenerated formula so the main repo reflects the exact release metadata that was published.

### 8. Sync the formula into the Homebrew tap repo

Copy or sync `Formula/ubundiforge.rb` into the tap repository, typically:

- `matthewubundi/homebrew-tap`

The tap repo is what Homebrew users install from.

### 9. Validate the tap

In the tap context, run:

```bash
brew install --build-from-source matthewubundi/tap/ubundiforge
brew test matthewubundi/tap/ubundiforge
```

### 10. Push the tap update

Once validation passes, commit and push the tap repo change.

At that point:

- new installs get the new version
- existing users get it after `brew update && brew upgrade ubundiforge`

## Quick checklist

For a normal admin release:

1. Update conventions, stacks, prompts, templates, or routing in this repo.
2. Bump version in `pyproject.toml` and `src/ubundiforge/__init__.py`.
3. Refresh `uv.lock` if dependencies changed.
4. Run tests and a dry-run scaffold.
5. Tag and push the release.
6. Generate `Formula/ubundiforge.rb` with the real tarball URL and SHA.
7. Sync that formula to the tap repo.
8. Test with `brew install` and `brew test`.
9. Push the tap update.

## Future improvement ideas

If maintaining Forge becomes a regular admin workflow, the next useful improvements would be:

- a single release script that bumps versions, checks sync, and regenerates the formula
- a separate command for refreshing user conventions from the latest bundled defaults
- CI automation that opens a PR against the Homebrew tap after a tagged release
