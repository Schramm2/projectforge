# Forge runtime pipeline

This view starts after CLI entry and follows a live scaffold through preparation, provider execution, verification, and local learning.

![ProjectForge end-to-end scaffold runtime](forge-runtime-pipeline.svg)

[Edit the D2 source](forge-runtime-pipeline.d2).

## Runtime stages

1. **Prepare:** complete setup when needed, collect answers, route phases, load context, scan user-controlled text, and build prompts.
2. **Execute:** copy selected media, initialize resumable progress, and run provider phases.
3. **Verify and hand off:** write the manifest and convention snapshot, initialize Git, run generated-project checks, record results, run the optional hook, and render the final handoff.

Scaffold history, answer preferences, and provider quality signals stay under `~/.forge/` and inform later runs. Generated-project evidence stays under the target project's `.forge/` directory.

## Implementation boundaries

- [`scaffold_request.py`](../../src/projectforge/scaffold_request.py) converts non-interactive CLI
  values into the same answer contract used by the questionnaire.
- [`scaffold_prompts.py`](../../src/projectforge/scaffold_prompts.py) turns routed phases into live
  prompts, prompt-only previews, exports, and resumable progress records.
- [`scaffold_execution.py`](../../src/projectforge/scaffold_execution.py) owns serial, parallel, and
  orchestrated phase execution; [`runner.py`](../../src/projectforge/runner.py) owns provider
  subprocesses.
- [`scaffold_completion.py`](../../src/projectforge/scaffold_completion.py) owns the ordered
  manifest, Git, verification, hook, evidence, dashboard, card, sound, and editor handoff.
