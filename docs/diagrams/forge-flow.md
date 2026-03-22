# Forge Flow Diagrams

These diagrams are now split into focused documents so each flow stays readable and easier to maintain.

Current state in this section is based on the scaffold path implemented in:

- `src/ubundiforge/cli.py`
- `src/ubundiforge/setup.py`
- `src/ubundiforge/prompts.py`
- `src/ubundiforge/router.py`
- `src/ubundiforge/prompt_builder.py`
- `src/ubundiforge/runner.py`
- `src/ubundiforge/verify.py`
- `src/ubundiforge/quality.py`
- `src/ubundiforge/media_assets.py`
- `src/ubundiforge/scaffold_log.py`

## Diagram Map

- [forge-input-flow.md](forge-input-flow.md) - first-run setup, interactive questionnaire, smart defaults, and review loop
- [forge-routing-and-execution.md](forge-routing-and-execution.md) - backend selection, quality-aware routing, phase merging, and execution order
- [forge-prompt-assembly.md](forge-prompt-assembly.md) - how Forge builds per-phase prompts from answers and context files
- [forge-runtime-pipeline.md](forge-runtime-pipeline.md) - end-to-end module flow from CLI entry to verification, logs, and editor launch

## High-Level Overview

```mermaid
flowchart TD
    Start["Developer runs forge"] --> SetupCheck{"First scaffold run<br/>and not dry-run/export?"}

    SetupCheck -- Yes --> Setup["Run 8-step setup wizard"]
    SetupCheck -- No --> InputMode
    Setup --> InputMode{"Interactive Q&A<br/>or CLI flags?"}

    InputMode -- Interactive --> Interactive["Collect basics, defaults,<br/>design/media, integrations,<br/>demo mode, review loop"]
    InputMode -- Flags --> Flags["Validate non-interactive inputs<br/>and build answers dict"]

    Interactive --> Route
    Flags --> Route["Compute phase plan"]

    Route --> Context["Load conventions, templates,<br/>media manifest, backend models"]
    Context --> Safety["Secret scan user-entered text"]
    Safety --> Prompting["Build per-phase prompts"]
    Prompting --> Preview{"Dry run or export?"}

    Preview -- Yes --> OutputPrompt["Print or write merged prompts"]
    Preview -- No --> Execute["Copy media, run phases,<br/>architecture first,<br/>middle phases parallel when possible,<br/>verify last"]

    Execute --> Post["Write manifest, init git,<br/>verify scaffold, log quality,<br/>run hook, record preferences"]
    Post --> Ready["Render dashboard,<br/>write project card,<br/>badge README, play sound,<br/>open editor"]
```

## Notes

- `forge check`, `forge replay`, `forge evolve`, and `forge stats` exist too, but this diagram set focuses on the main scaffold workflow.
- The old single-file diagrams had drifted behind the code. The split docs aim to track the actual runtime path more closely.
