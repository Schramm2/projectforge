# Changelog

All notable changes to the Forge Scaffolding Assistant skill will be documented in this file.

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

### Rationale
The previous version was useful, but it still looked like a Codex-authored skill package rather than a Kwanda-style production skill. This release aligns the structure and writing style to the standard used in `kwanda-skills`: self-contained `SKILL.md`, human-facing `README.md`, versioned `CHANGELOG.md`, and command examples that are concrete instead of suggestive.
