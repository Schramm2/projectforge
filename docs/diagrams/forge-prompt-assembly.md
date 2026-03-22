# Forge Prompt Assembly

This document covers the data that flows into `build_phase_prompt()` and how Forge decides which prompt variant to use.

## Current Behavior

- Forge builds one prompt per phase for execution.
- It also builds merged prompts for `--dry-run` and `--export`.
- If a single backend owns all phases, Forge uses the full legacy-style prompt. Otherwise it chooses targeted prompts for architecture, frontend, tests, or verify.

## Prompt Inputs And Variants

```mermaid
flowchart TD
    subgraph Inputs["Prompt inputs"]
        Answers["Answers payload<br/>name, stack, description,<br/>docker, services, auth, CI,<br/>demo mode, extra"]
        ConventionsTree["Bundled conventions tree<br/>global, language, stack,<br/>prompt manifests"]
        ConventionBundle["Compiled convention bundle<br/>stack-aware prompt block"]
        ClaudeTemplate["CLAUDE.md template<br/>if available"]
        DesignTemplate["Loaded design template content<br/>plus selected label"]
        MediaManifest["Media asset manifest<br/>with target directory and files"]
        PhaseSet["Current phase list<br/>and all phases for this stack"]
        Backend["Assigned backend"]
    end

    subgraph Builder["prompt_builder.py"]
        direction TB
        FullCheck{"All phases assigned<br/>to one backend?"}
        FullPrompt["Build full scaffold prompt<br/>build_prompt or build_prompt_codex"]

        PhaseSwitch{"Targeted phase type"}
        ArchPrompt["Architecture prompt<br/>best/default/codex variant"]
        FrontendPrompt["Frontend prompt<br/>best/default/codex variant"]
        TestsPrompt["Tests prompt<br/>best/default variant"]
        VerifyPrompt["Verify prompt<br/>best/default/codex variant"]

        FullCheck -- Yes --> FullPrompt
        FullCheck -- No --> PhaseSwitch
        PhaseSwitch --> ArchPrompt
        PhaseSwitch --> FrontendPrompt
        PhaseSwitch --> TestsPrompt
        PhaseSwitch --> VerifyPrompt
    end

    Answers --> Builder
    ConventionsTree --> ConventionBundle
    ConventionBundle --> Builder
    ClaudeTemplate --> Builder
    DesignTemplate --> Builder
    MediaManifest --> Builder
    PhaseSet --> Builder
    Backend --> Builder

    FullPrompt --> PhasePrompt["Final phase prompt"]
    ArchPrompt --> PhasePrompt
    FrontendPrompt --> PhasePrompt
    TestsPrompt --> PhasePrompt
    VerifyPrompt --> PhasePrompt
```

## What Changes Prompt Content

```mermaid
flowchart LR
    StackMeta["Stack metadata and defaults"] --> Prompt
    AuthRules["Auth provider metadata"] --> Prompt
    CIConfig["CI include/mode/actions"] --> Prompt
    DemoMode["Demo mode guidance"] --> Prompt
    DesignGuide["Design template block"] --> Prompt
    MediaFiles["Media manifest block"] --> Prompt
    ConventionsBlock["Compiled conventions block"] --> Prompt
    ExtraInstructions["User extra instructions"] --> Prompt
    ClaudeStarter["CLAUDE.md starter guidance"] --> Prompt
    PhaseInstructions["Phase-specific instructions"] --> Prompt
    Prompt["Assembled prompt text"]
```

## Notes

- Forge now compiles conventions from the bundled `conventions/` tree before prompt assembly, and `forge admin conventions` previews the same compiled bundle that the prompt builder consumes.
- Legacy `.forge/conventions.md` and `~/.forge/conventions.md` files remain compatibility overrides, not the primary maintainer source of truth.
- Secret scanning happens before execution, but after answers are collected and before prompts are handed to an AI CLI.
- Model selection is resolved outside the prompt builder and passed to the backend CLI command separately.
