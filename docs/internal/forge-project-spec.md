# FORGE — Ubundi Project Scaffolder

> Historical design brief. This file preserves the original product spec and no longer reflects the current implementation line-for-line. Use `docs/guides/`, `docs/maintainers/`, and `src/ubundiforge/` as the source of truth for current behavior.

> A Python CLI that wraps AI coding tools (Claude Code, Gemini CLI, Codex) to scaffold new projects with your conventions baked in. Feed this spec to Claude Code to build it.

---

## What Is Forge

Forge is a CLI wrapper — like [Sketch from the Workflow podcast](https://www.youtube.com/watch?v=example) but for project scaffolding. You run `forge`, answer a few questions, and it constructs a detailed prompt from your answers + your Ubundi conventions file, then pipes that prompt into the best AI CLI tool for the job.

Forge does NOT call APIs directly. It does NOT parse output or write files itself. It assembles the perfect prompt and hands it to `claude`, `gemini`, or `codex` as a subprocess. The AI CLI does what it already does well — creates files, sets up the project, handles the details.

**The core loop:**
1. You run `forge`
2. Forge asks 4-5 quick questions
3. Forge picks the default AI backend
4. Forge constructs a prompt (your answers + conventions file)
5. Forge pipes that prompt into the chosen AI CLI
6. The AI creates your project
7. You're building

---

## User Flow

```
$ forge

  🔨 Forge — Ubundi Project Scaffolder

  ? Project name: christmas-store
  ? What are we building?
    ❯ Next.js + React (frontend or fullstack)
      Python API (FastAPI)
      Both (Next.js frontend + FastAPI backend)
  ? Brief description:
    > A festive e-commerce store for Christmas decorations
  ? Include Docker setup? (Y/n): Y

  → Using Gemini CLI (frontend project detected)
  → Loading conventions from ~/.forge/conventions.md
  → Handing off to Gemini...

  [Gemini CLI takes over, creates the project, you see its output]
```

Total time from idea to building: under 60 seconds.

---

## AI Routing — Default Backend

Forge defaults all stacks to Claude for now, with a fallback chain if Claude is not installed:

| Stack Selected | AI CLI Used | Why |
|---|---|---|
| Next.js + React | `claude` | Temporary default until scaffold-quality research says otherwise |
| Python API (FastAPI) | `claude` | Best general default |
| Both (monorepo) | `claude` | Best general default |
| Any test/automation task (future) | `codex` | Codex excels at tests, scripts, automation |

**Override flag:** `forge --use claude` or `forge --use gemini` or `forge --use codex` to force a specific backend regardless of the routing logic.

The routing logic lives in a single function that's easy to update as you learn what works best in practice.

---

## Tech Stack (For Forge Itself)

| Component | Choice |
|---|---|
| Language | Python 3.11+ |
| CLI Framework | Typer (auto help, tab completion) |
| Terminal UI | Rich (styled output, spinners, panels) |
| Interactive Prompts | questionary (select, confirm, text) |
| AI Backends | subprocess calls to `claude`, `gemini`, `codex` |
| Packaging | pip installable, `forge` console entry point |

---

## Forge's Own Project Structure

```
forge/
├── pyproject.toml
├── README.md
├── CLAUDE.md
├── forge/
│   ├── __init__.py
│   ├── cli.py              # Typer app, entry point
│   ├── prompts.py          # Interactive question flow
│   ├── router.py           # Picks the right AI CLI
│   ├── prompt_builder.py   # Assembles the prompt string
│   ├── runner.py           # Executes the AI CLI subprocess
│   ├── conventions.py      # Loads ~/.forge/conventions.md
│   └── config.py           # Settings
└── tests/
    └── test_router.py
```

---

## Core Modules

### cli.py — Entry Point

- Single command: just `forge`. No subcommands for v1.
- Typer flags:
  - `--use [claude|gemini|codex]` — override AI routing
  - `--dry-run` — print the assembled prompt without executing
- Flow: collect answers → pick AI backend → build prompt → run subprocess
- Clean error handling: if the chosen CLI isn't installed, tell the user what to install and exit

### prompts.py — Questions

Uses questionary. Keep the flow short, but allow a few targeted follow-ups when requested:

1. **Project name** (text input, validated as valid directory name)
2. **Stack** (select): Next.js + React / Python API (FastAPI) / Both
3. **Description** (text): 1-2 sentences about what you're building
4. **Docker?** (confirm, default yes)
5. **Authentication?** (optional for Next.js/fullstack): provider selection such as Clerk, Supabase Auth, Auth.js, or Better Auth
6. **CI?** (optional): include CI, then either choose CI actions or request a blank template
7. **Any extra instructions?** (text, optional): freeform additions like "include Stripe integration"

Returns a simple dict with the answers.

### router.py — AI Routing

Single function: takes the stack selection, returns which CLI to use.

```python
def pick_backend(stack: str, override: str | None = None) -> str:
    if override:
        return override
    
    routing = {
        "nextjs": "claude",
        "fastapi": "claude",
        "both": "claude",
    }
    return routing.get(stack, "claude")  # default to claude
```

This is intentionally simple. Update the routing dict as you learn what works best.

### prompt_builder.py — The Secret Sauce

This module assembles the prompt that gets piped into the AI CLI. It combines:

1. **The conventions file** (~/.forge/conventions.md) — your Ubundi standards
2. **The project details** — name, stack, description, Docker yes/no
3. **The scaffold instruction** — telling the AI exactly what to create
4. **Extra instructions** — any freeform additions from the final question

The assembled prompt should read like a clear, detailed brief. Example of what gets generated:

```
You are scaffolding a new project. Create the full project in the current directory.

PROJECT DETAILS:
- Name: christmas-store
- Stack: Next.js + React
- Description: A festive e-commerce store for Christmas decorations
- Docker: Yes

CONVENTIONS (follow these exactly):
[contents of ~/.forge/conventions.md inserted here]

INSTRUCTIONS:
- Create a complete, working project structure with all config files
- Include a CLAUDE.md at the root that describes this project for AI coding assistants
- Include an agent_docs/ directory with starter docs that match the CLAUDE.md progressive-disclosure structure
- Include appropriate .gitignore, .env.example, README.md
- Include Docker setup (Dockerfile + docker-compose.yml)
- Initialize with sensible defaults — the user should be able to run the project immediately after scaffolding
- Follow the conventions above strictly for all styling, structure, and coding patterns

EXTRA INSTRUCTIONS FROM USER:
[any freeform text from question 5, or "None"]
```

**Important:** The prompt format might need slight adjustments per backend. Claude Code, Gemini CLI, and Codex may respond best to slightly different prompt structures. Start with one format and adjust per backend if needed.

### runner.py — Subprocess Execution

Runs the chosen AI CLI with the assembled prompt. Each backend has its own invocation:

```python
import subprocess

def run_ai(backend: str, prompt: str, project_name: str):
    """Execute the AI CLI with the assembled prompt."""
    
    if backend == "claude":
        # Claude Code: pipe prompt via stdin with --print flag or similar
        cmd = ["claude", "--print", prompt]
        
    elif backend == "gemini":
        # Gemini CLI: however gemini accepts prompts
        cmd = ["gemini", prompt]
        
    elif backend == "codex":
        # Codex: however codex accepts prompts  
        cmd = ["codex", prompt]
    
    subprocess.run(cmd, cwd=project_name)
```

**NOTE TO BUILDER:** The exact subprocess invocation for each CLI will need to be figured out based on how each tool accepts input. Check the docs for:
- How Claude Code accepts a prompt/instruction via command line
- How Gemini CLI accepts a prompt via command line  
- How Codex accepts a prompt via command line

The key is that Forge creates the project directory first (`mkdir project_name`), then runs the AI CLI inside that directory so all files get created in the right place.

### conventions.py — Convention Loader

- Looks for `~/.forge/conventions.md`
- If missing, creates `~/.forge/` and writes the default conventions (see below)
- Returns content as a string for injection into the prompt
- User edits this file to customize — Forge just reads it

### config.py — Configuration

- Checks that the selected AI CLI is installed (shutil.which)
- Any shared settings
- No API keys needed — the CLI tools handle their own auth

---

## Default Conventions File

This gets written to `~/.forge/conventions.md` on first run. Written as instructions to an AI about how to generate code:

```markdown
# Ubundi Project Conventions

Follow these conventions when generating any project files.

## Brand & Styling (Frontend Projects)

- Use Tailwind CSS for all styling
- Ubundi brand palette:
  - Backgrounds: dark blue-grey (#1A2332 to #2A3444)
  - Accents: cyan-teal (#0FA5A5, #0CC5C5)
  - Text: white on dark backgrounds
  - Cards/panels: glassmorphism (backdrop-blur, semi-transparent bg)
- Fonts: Inter for UI text, JetBrains Mono for code blocks
- Configure fonts in tailwind.config
- Dark mode is the default theme
- Components should be modern, clean, minimal
- No heavy shadows. Use subtle borders with opacity

## Coding Standards

### TypeScript / Next.js
- TypeScript strict mode. No 'any' types.
- App router (app/ directory)
- Components in src/components/
- Utilities in src/lib/
- ESLint + Prettier configured

### Python / FastAPI
- Type hints on all functions and variables
- Pydantic models for all data structures
- Async endpoints where possible
- Structure: app/ with routers/, models/, services/, config.py
- Ruff for linting and formatting

## Always Include
- .gitignore appropriate to the stack
- .env.example showing all required environment variables
- README.md with project name, description, setup instructions, and how to run
- CLAUDE.md at root — a briefing for AI coding assistants containing:
  project name, description, stack, folder structure, conventions, and any 
  project-specific notes. Write it as a direct briefing, not documentation.

## Git
- Use conventional commit style
- Initialize git on project creation
```

---

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd forge

# Install in dev mode
pip install -e .

# Now available globally
forge

# Override AI backend
forge --use claude

# Preview the prompt without running
forge --dry-run
```

`pyproject.toml` registers `forge` as a console entry point → `forge.cli:app`

### Prerequisites
The user needs at least one of these AI CLI tools installed:
- Claude Code (`claude`)
- Gemini CLI (`gemini`)
- Codex (`codex`)

Forge checks for the selected tool at runtime and gives a clear error if it's not found.

---

## Design Principles

**Speed over features.** Idea to building in under 60 seconds. If a feature doesn't serve that, it's not in v1.

**Wrapper, not a platform.** Forge is a thin layer. The AI CLIs do the hard work. Forge just gives them the right instructions.

**Convention over configuration.** Your opinions live in conventions.md. The CLI asks minimal questions. Sensible defaults everywhere.

**AI-generated, not templated.** No static templates to maintain. The AI generates a bespoke scaffold every time, informed by your conventions.

**Easy to extend.** New stack option = add to prompts.py + router.py. New convention = edit a markdown file. New AI backend = add a case to runner.py.

---

## Future Ideas (NOT V1)

Do not build these yet. V1 is only the scaffolder.

- Multiple conventions files for different clients (e.g. `forge --conventions client-x`)
- `forge log` — experiment journal to track what you've built
- `forge run` — unified workflow runner for your automation tools
- Post-scaffold hooks (auto-install deps, open browser, etc.)
- Smarter routing that learns which backend produces better results over time
