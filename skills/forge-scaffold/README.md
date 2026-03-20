# Forge Scaffolding Assistant - Usage Guide

Portable skill for AI agents that need to use Forge professionally.

## Requirements

- Access to this repository
- Python 3.12+
- `uv` for the repo-local launcher, or `pipx` for a packaged install
- At least one installed AI backend CLI:
  - `claude`
  - `gemini`
  - `codex`

## Setup

### 1. Make the skill available to the agent

Give the agent this folder:

```bash
skills/forge-scaffold/
```

At minimum, the agent should read:

- `skills/forge-scaffold/SKILL.md`

### 2. Prepare Forge

**Repo-local mode:**

```bash
uv sync --dev
./forge --version
```

**Packaged mode from this repo:**

```bash
pipx install .
forge --version
```

### 3. Run Forge setup

```bash
./forge --setup
```

This detects installed backends, lets you choose default models, and writes Forge config under `~/.forge/`.

## Testing

### Prompt Review
- [ ] `./forge --dry-run --name studio --stack nextjs --description "Client portal" --no-docker --no-open`
- [ ] Confirm the prompt includes the correct stack, routing plan, and conventions
- [ ] `./forge --export /tmp/forge-skill-check.md --name atlas-api --stack fastapi --description "Internal API" --docker --no-open`
- [ ] Confirm the export file is written and readable

### Live Scaffold
- [ ] Scaffold a Next.js project with auth and CI
- [ ] Scaffold a FastAPI service with Docker and verification
- [ ] Confirm `README.md`, `CLAUDE.md`, `agent_docs/`, `.env.example`, and `.forge/scaffold.json` exist
- [ ] Confirm Forge chose the expected backend routing or honored `--use`

### Verification Follow-Through
- [ ] Review any Forge verification failures
- [ ] Rerun the relevant project command manually in the generated repo
- [ ] Fix obvious generated issues instead of treating scaffold completion as success

## Troubleshooting

**`./forge` says uv is required**
- Install `uv`, then rerun `uv sync --dev`
- Or use a packaged install with `pipx install .`

**Forge says no AI backend is installed**
- Install at least one of `claude`, `gemini`, or `codex`
- If you only need prompt inspection, use `--dry-run` or `--export`

**Unsupported option error**
- `--auth-provider` only works on `nextjs` and `both`
- `--design-template` only works on `nextjs` and `both`
- Use exact CI action IDs supported by the selected stack

**Verification fails after scaffold**
- Inspect the first failing check
- Run the failing command manually inside the generated project
- Patch the scaffold instead of rerunning Forge blindly

## Privacy & Support

**Data processing:** Forge sends the scaffold brief and related context to the chosen AI CLI. **User controls:** Inspect prompts with `--dry-run` or `--export`, keep `--demo` enabled for secret-free startup, and review `.forge/scaffold.json` for provenance. **Support:** Repository: Forge.
