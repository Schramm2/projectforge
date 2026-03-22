# Forge Scaffolding Assistant - Usage Guide

Portable skill for AI agents that need to use Forge professionally. Updated for v0.3.0.

## Requirements

- Access to this repository
- Python 3.12+
- `brew install ubundiforge` (Homebrew) or `uv sync --dev` (repo-local)
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

**Homebrew (recommended):**

```bash
brew tap matthewubundi/tap
brew install ubundiforge
forge --version
```

**Repo-local mode:**

```bash
uv sync --dev
./forge --version
```

### 3. Run Forge setup

```bash
forge --setup
```

This detects installed backends, lets you choose default models, and writes Forge config under `~/.forge/`.

## Testing

### Prompt Review
- [ ] `forge --dry-run --name studio --stack nextjs --description "Client portal" --no-docker --no-open`
- [ ] Confirm the prompt includes the correct stack, routing plan, and conventions
- [ ] `forge --export /tmp/forge-skill-check.md --name atlas-api --stack fastapi --description "Internal API" --docker --no-open`
- [ ] Confirm the export file is written and readable

### Live Scaffold
- [ ] Scaffold a Next.js project with auth and CI
- [ ] Scaffold a FastAPI service with Docker and verification
- [ ] Confirm `README.md`, `CLAUDE.md`, `agent_docs/`, `.env.example`, and `.forge/scaffold.json` exist
- [ ] Confirm Forge chose the expected backend routing or honored `--use`
- [ ] Confirm the post-scaffold dashboard displays health checks and stats
- [ ] Confirm `.forge/card.svg` was generated and README has the badge

### Convention Auditing
- [ ] Run `forge check` inside a scaffolded project
- [ ] Confirm pass/warn/fail scorecard renders correctly
- [ ] Run `forge check --fix` and confirm missing files are generated
- [ ] Run `forge check --export report.md` and confirm markdown report

### Project Augmentation
- [ ] Run `forge evolve --dry-run auth` inside a scaffolded project
- [ ] Confirm the prompt includes project context and capability instructions
- [ ] Run `forge evolve --help` and confirm all options

### Analytics
- [ ] Run `forge stats` and confirm scaffold history renders
- [ ] Scaffold 2-3 projects and confirm stats update

### Replay
- [ ] Run `forge replay --dry-run` inside a scaffolded project
- [ ] Confirm the reconstructed prompt matches the original scaffold inputs
- [ ] Run `forge replay --help` and confirm all options

### Verification Follow-Through
- [ ] Review any Forge verification failures in the dashboard
- [ ] Rerun the relevant project command manually in the generated repo
- [ ] Fix obvious generated issues instead of treating scaffold completion as success

## Troubleshooting

**`forge` command not found**
- Install via Homebrew: `brew tap matthewubundi/tap && brew install ubundiforge`
- Or use repo-local: `uv sync --dev && ./forge --version`

**Forge says no AI backend is installed**
- Install at least one of `claude`, `gemini`, or `codex`
- If you only need prompt inspection, use `--dry-run` or `--export`

**Unsupported option error**
- `--auth-provider` only works on `nextjs` and `both`
- `--design-template` only works on `nextjs` and `both`
- Use exact CI action IDs supported by the selected stack

**Verification fails after scaffold**
- Inspect the first failing check in the dashboard
- Run the failing command manually inside the generated project
- Use `forge check` for a broader convention audit
- Patch the scaffold instead of rerunning Forge blindly

**`forge evolve` says no scaffold.json**
- Run from inside a Forge-scaffolded project (must have `.forge/scaffold.json`)
- If the project was scaffolded before v0.3.0, the manifest may be missing fields

**`forge replay` conventions warning**
- Projects scaffolded before v0.3.0 won't have `.forge/conventions-snapshot.md`
- Replay falls back to current `~/.forge/conventions.md` with a warning

## Privacy & Support

**Data processing:** Forge sends the scaffold brief and related context to the chosen AI CLI. Quality signals and preferences are stored locally under `~/.forge/`. **User controls:** Inspect prompts with `--dry-run` or `--export`, keep `--demo` enabled for secret-free startup, and review `.forge/scaffold.json` for provenance. **Support:** Repository: UbundiForge.
