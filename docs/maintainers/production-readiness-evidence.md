# Production Readiness Evidence

Evidence date: 2026-07-18
Release candidate: 0.5.0

This record separates direct runtime proof from documentation-only or unavailable evidence. It
contains no account identity, credential, provider response body, or private absolute path.

## Authenticated scaffold

- Provider: Claude Code 2.1.214, reported authenticated through Claude.ai by the provider-owned
  status command. This is **live** evidence.
- Execution: `safe` mode, mapped to `acceptEdits` with session persistence disabled, in one bounded
  target workspace. A locally configured stable model alias was passed explicitly.
- Scaffold: Python CLI, standard one-call-per-phase mode, no Docker, CI, media, editor launch, or
  external-service credentials; post-scaffold verification enabled.
- Provider ledger: architecture, tests, and verify phases each completed on the first attempt with
  exit 0. Recorded durations were 196, 351, and 216 seconds.

The initial Forge verification did not claim success: install passed, lint and tests failed, and a
cold type check exceeded the then-current 30-second limit. Independent reproduction found stale
generated Typer compatibility, six remaining behavioral assertion/validation mismatches after a
targeted provider repair, and two lint defects. The scaffold was repaired surgically rather than
weakening Forge's acceptance criteria.

Fresh independent checks then passed:

- `uv sync --extra dev`;
- `uv run ruff check .`;
- `uv run mypy .`;
- `uv run pytest -q` — 89 passed; and
- `uv run greet --help`, with all expected commands present.

Repeating the exact Forge command with `--resume` preserved all three completed phases without new
provider calls. The corrected verifier then recorded install, lint, typecheck, and test as passed,
each with exit 0 and a bounded 60-second timeout. `.forge/verification.json` reported
`all_passed: true`, used only project-relative working directories, contained no home path, and the
dashboard reported `Project Ready`.

This is evidence for authenticated end-to-end generation, failure honesty, surgical recovery,
resume correctness, and independent verification. It is not evidence that probabilistic generated
code is always zero-touch; the first generated result required repair, and Forge surfaced that
accurately.

## Provider evidence classification

| Provider | Classification | Evidence |
| --- | --- | --- |
| Claude Code | Live | 2.1.214 version/help/status, safe and plan parser probes, authenticated scaffold and repair call |
| Codex CLI | Partial | Installed/authenticated 0.144.0 version/help/status; official latest 0.144.5 version/help isolated probe; no model call |
| Gemini CLI | Unavailable for live use | Official 0.51.0 version/help isolated probe; no global binary, authentication proof, or model call |

See [Provider Compatibility](provider-compatibility.md) for official sources, safe command shapes,
and provider-specific limitations.

## Publication evidence

- [ProjectForge PR #5](https://github.com/Schramm2/projectforge/pull/5) merged through the hosted
  workflow after all Python 3.12/3.13 Ubuntu/macOS checks passed.
- The release workflow created annotated tag `v0.5.0`, published the
  [GitHub release](https://github.com/Schramm2/projectforge/releases/tag/v0.5.0), measured archive
  SHA-256 `f1293f2405690a7c6c33182fa826a29ce5a39d41323e80ac491f9f573764955d`, and committed the
  generated formula to `main`.
- Its first tap checkout failed because the configured secret was nonempty but unusable. The local
  authenticated GitHub session had verified tap push authority, so
  [tap PR #3](https://github.com/Schramm2/homebrew-tap/pull/3) synchronized the exact generated
  formula through review rather than a direct default-branch push.
- [ProjectForge PR #6](https://github.com/Schramm2/projectforge/pull/6) hardened the release
  workflow: every new tag now requires a real tap push-permission check. An existing release can
  skip writes only after the public and generated formulas compare byte-for-byte.
- The subsequent
  [sync-only workflow](https://github.com/Schramm2/projectforge/actions/runs/29646098616) succeeded,
  regenerated the v0.5.0 formula, verified the exact tap match, and skipped all publication writes.
- A clean isolated `uv tool install` from the immutable tag passed version, help, JSON doctor, and
  zero-call dry-run checks. A Homebrew source reinstall from the public tap built v0.5.0, and
  `brew test`, version, help, JSON doctor, and zero-call dry run all passed.

The remaining operational risk is explicit: the stored tap secret must be replaced before the next
new release. It was not changed during this task. The hardened workflow will stop before creating a
future tag until that credential proves push permission.
