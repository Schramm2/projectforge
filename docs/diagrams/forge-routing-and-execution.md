# Forge Routing And Execution

This document covers how Forge picks backends for each phase and how those phases are run.

## Current Behavior

- Routing is phase-based, not single-backend by default.
- The router considers explicit `--use`, installed and ready backends, project-description keywords, and quality-memory scores.
- Execution order is fixed: architecture first, verify last, with middle phases run in parallel when more than one exists.

## Routing Logic

```mermaid
flowchart TD
    Start["answers.stack + answers.description"] --> Override{"--use provided?"}

    Override -- Yes --> Forced["Route every phase to forced backend"]
    Override -- No --> Available["Determine usable backends<br/>from readiness checks"]

    Available --> Phases["Load stack phase list<br/>from STACK_PHASES"]
    Phases --> CodexHint{"Architecture description<br/>matches Codex phrases?"}

    CodexHint -- Yes --> ArchChoice["Prefer Codex for architecture<br/>if Codex is available"]
    CodexHint -- No --> IdealChoice["Use ideal backend per phase"]

    ArchChoice --> IdealMap
    IdealChoice --> IdealMap["Ideal mapping:<br/>architecture -> claude<br/>frontend -> gemini<br/>tests -> codex<br/>verify -> claude"]

    IdealMap --> Fallback{"Ideal backend available?"}
    Fallback -- Yes --> Routed["Use ideal backend"]
    Fallback -- No --> FallbackPick["Fallback preference:<br/>claude, then first available backend"]

    Routed --> Quality{"Enough quality-memory data<br/>for this stack + phase?"}
    FallbackPick --> Quality
    Quality -- No --> PhasePlan["Phase backend plan"]
    Quality -- Yes --> QualityMargin{"Alternative backend score<br/>beats current by > 0.1?"}
    QualityMargin -- Yes --> OverrideByQuality["Swap to best-scoring backend"]
    QualityMargin -- No --> KeepCurrent["Keep current backend"]
    OverrideByQuality --> PhasePlan
    KeepCurrent --> PhasePlan
```

## Merge And Execution Strategy

```mermaid
flowchart TD
    PhasePlan["Per-phase routing list"] --> Merge["Merge adjacent phases<br/>that share a backend"]
    Merge --> PromptBuild["Build prompts per phase<br/>and merged prompts for preview/export"]

    PromptBuild --> RunWindow{"Prompt-only run?"}
    RunWindow -- Yes --> Preview["Show or export merged prompts"]
    RunWindow -- No --> SerialFirst["Run architecture phase serially"]

    SerialFirst --> Middle{"Middle phases present?"}
    Middle -- No --> FinalVerify
    Middle -- Yes --> ParallelCheck{"More than one<br/>middle phase?"}

    ParallelCheck -- Yes --> ParallelRun["Run frontend/tests window in parallel"]
    ParallelCheck -- No --> SerialMiddle["Run the single middle phase serially"]

    ParallelRun --> FinalVerify["Run verify phase serially"]
    SerialMiddle --> FinalVerify
    FinalVerify --> Done["Scaffold phases complete"]
```

## Notes

- `merge_adjacent_phases()` reduces redundant prompt handoffs when the same backend owns neighboring phases.
- Parallel work only applies to the middle window. Architecture and verify stay serialized to preserve dependency order.
- If no usable backends are ready, Forge stops before any prompt is assembled or executed.
