# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-20

### Added

- Interactive CLI built with Typer, Rich, and questionary for guided project scaffolding.
- Support for 7 stacks: Next.js, FastAPI, FastAPI + AI/LLM, Next.js + FastAPI monorepo, Python CLI, TypeScript npm Package, and Python Worker.
- AI backend routing with automatic fallback (Claude Code -> Gemini CLI -> Codex).
- Multi-phase parallel execution with live progress display.
- First-run setup wizard that detects installed AI CLIs, editors, git, and Docker.
- Non-interactive mode via CLI flags for CI and scripting use.
- Shared conventions loaded from `~/.forge/conventions.md` and injected into every scaffold prompt.
- Secret detection scanning on user-provided text.
- `CLAUDE.md` template injection into scaffolded projects.
- Design template system for brand-consistent scaffolds (e.g., `ubundi-brand-guide`).
- Auth provider selection (Clerk, NextAuth.js, Supabase Auth) for frontend stacks.
- CI workflow generation with configurable actions (lint, typecheck, unit-tests, etc.).
- Media asset import with named collection support.
- Post-scaffold verification that confirms generated projects boot correctly.
- Demo mode generating projects that run without real API keys.
- Shell tab completion for all flags.
- Scaffold history log at `~/.forge/scaffold.log`.
- Per-project `.forge/scaffold.json` manifest for provenance tracking.
- Post-scaffold hooks via `~/.forge/hooks/post-scaffold.sh`.
- Prompt export (`--export`) and dry-run (`--dry-run`) modes.
- Homebrew formula and tap for macOS installation.
- pipx support for isolated global installs.
- MIT license.

[0.1.0]: https://github.com/matthewubundi/UbundiForge/releases/tag/v0.1.0
