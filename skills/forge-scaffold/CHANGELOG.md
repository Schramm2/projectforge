# Changelog

All notable changes to the Forge Scaffolding Assistant skill will be documented in this file.

## [2.0.0] - 2026-03-22

### Added
- Convention auditing guidance: `forge check`, `--fix`, `--export` usage
- Project augmentation guidance: `forge evolve` with per-stack capability tables
- Scaffold analytics guidance: `forge stats` for history and performance data
- Scaffold replay guidance: `forge replay` with `--diff` for drift analysis
- Scaffold experience documentation: phase timeline, activity feed, file tree, dashboard
- Smart defaults documentation: adaptive question flow based on user patterns
- Quality-based routing documentation: EMA scoring and backend override behavior
- Completion sound documentation: opt-in audio feedback
- Forge card documentation: auto-generated SVG badge and project card
- User data reference table: all `~/.forge/` files and their purposes
- Augmentation mode to operating modes section
- Homebrew install as the primary installation method
- Updated CLI commands summary table

### Changed
- Updated skill description to reference v0.3.0 and all five commands
- Expanded Core Capabilities with quality routing and smart defaults
- Expanded Post-Scaffold Repair Mode to include `forge check` as a follow-up step
- Updated verification section to reference the post-scaffold dashboard
- Replaced `pipx install .` with `brew install ubundiforge` as the recommended install
- Updated README testing checklist to cover all five commands

### Removed
- References to `pipx install .` (Homebrew is the supported distribution channel)

## [1.0.0] - 2026-03-20

### Added
- Rebuilt the skill package to match the Kwanda skills standard more closely
- Added a self-contained operational `SKILL.md` with:
  - entrypoint checks
  - complete Forge command examples with real parameters
  - explicit operating modes
  - stack-selection guidance
  - routing, verification, and guardrail sections
- Added `README.md` as a human-facing usage and testing guide
- Added `CHANGELOG.md` for versioned maintenance

### Changed
- Replaced the earlier Codex-style guidance and reference-heavy layout with a Kwanda-style operational skill
- Moved from abstract guidance to complete runnable Forge command blocks
- Made the skill portable for any agent that can read the repo and run shell commands

### Removed
- Removed repo skill metadata and reference directories that were not part of the Kwanda package pattern
