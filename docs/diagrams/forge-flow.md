# UbundiForge — Flow Diagrams

## 1. User Flow (Product View)

How a developer goes from idea to running project with Forge.

```mermaid
flowchart TD
    Start([Developer runs **forge**]) --> FirstRun{First time?}

    FirstRun -- Yes --> Setup
    FirstRun -- No --> Describe

    subgraph Setup["0 — Setup wizard"]
        direction TB
        DetectAI[Detects installed AI tools<br/>Claude / Gemini / Codex]
        PickAI[Pick default AI backend<br/>+ per-backend model selection]
        DetectEditor[Detects installed editors<br/>Cursor / VS Code / Antigravity / Zed]
        PickEditor[Pick default editor]
        CheckGit[Check git + Docker + projects dir]
        Conventions[Creates conventions file<br/>~/.forge/conventions.md]
        DetectAI --> PickAI --> DetectEditor --> PickEditor --> CheckGit --> Conventions
    end

    Setup --> Describe

    subgraph Describe["1 — Describe your project"]
        Q1[Name your project]
        Q2[Pick a stack<br/>Next.js / FastAPI / FastAPI-AI /<br/>Full-stack / CLI tool /<br/>TS package / Worker]
        Q3[Describe what it does]
        Q1 --> Q2 --> Q3
    end

    Describe --> Options

    subgraph Options["2 — Choose options"]
        Docker[Docker setup?]
        Design[Design template?<br/>brand guide for frontend stacks]
        Demo[Demo mode?<br/>runs without real API keys]
        Customize{Want to customize?}
        Auth[Authentication<br/>Clerk / NextAuth / Supabase]
        Svc[Services<br/>PostgreSQL, OpenAI, AWS...]
        CI[CI/CD pipeline?]
        Extra[Any special instructions?]
        Docker --> Design --> Demo --> Customize
        Customize -- Yes --> Auth --> Svc --> CI --> Extra
        Customize -- No --> Skip[ ]
    end

    Options --> Route

    subgraph Route["3 — Multi-phase routing"]
        direction TB
        Phases[Router assigns each phase<br/>to the best available backend]
        PhaseList["Architecture → Claude<br/>Frontend → Gemini<br/>Tests → Codex<br/>Verify → Claude"]
        Merge[Adjacent same-backend<br/>phases get merged]
        Phases --> PhaseList --> Merge
    end

    Route --> Generate

    subgraph Generate["4 — Forge builds your project"]
        direction TB
        Conv[Loads your team's<br/>coding conventions]
        Prompt[Assembles phase-specific<br/>AI brief with specialist prompts]
        AI["Runs phases: arch serial,<br/>frontend+tests parallel,<br/>verify serial"]
        Conv --> Prompt --> AI
    end

    Generate --> Verify

    subgraph Verify["5 — Post-scaffold verification"]
        direction TB
        Install[Install dependencies<br/>uv sync / npm install]
        Checks[Run lint, typecheck,<br/>build, tests]
        Health[Start server and<br/>probe /health endpoint]
        Install --> Checks --> Health
    end

    Verify --> Output

    subgraph Output["6 — Ready to code"]
        direction LR
        Code[Complete project<br/>with all config,<br/>structure, and<br/>conventions baked in]
        Git[Git repo initialized<br/>with first commit]
        Next[Next steps printed:<br/>cd, env setup, dev cmd]
        Editor[Opens in your<br/>editor]
        Code ~~~ Git ~~~ Next ~~~ Editor
    end

    style Setup fill:#fce4ec,stroke:#E91E63,color:#1a1a1a
    style Describe fill:#e8f4f8,stroke:#2196F3,color:#1a1a1a
    style Options fill:#fff3e0,stroke:#FF9800,color:#1a1a1a
    style Route fill:#e0f2f1,stroke:#009688,color:#1a1a1a
    style Generate fill:#e8f5e9,stroke:#4CAF50,color:#1a1a1a
    style Verify fill:#fff9c4,stroke:#FBC02D,color:#1a1a1a
    style Output fill:#f3e5f5,stroke:#9C27B0,color:#1a1a1a
    style Start fill:#2196F3,stroke:#1565C0,color:#fff
```

## 2. Internal Pipeline

How data flows through Forge's modules during a scaffold run.

```mermaid
flowchart LR
    subgraph CLI["cli.py"]
        Entry[Entry point<br/>parse flags + options]
    end

    subgraph Prompts["prompts.py"]
        Interactive[Interactive Q&A<br/>questionary prompts]
    end

    subgraph ScaffoldOpts["scaffold_options.py"]
        AuthOpts[Auth providers<br/>CI actions<br/>per-stack options]
    end

    subgraph Stacks["stacks.py"]
        Meta[Stack metadata<br/>structure, libs, commands]
        Cross[Cross-recipe defaults<br/>Python + TS + Docker standards]
    end

    subgraph Conv["conventions.py"]
        Load[Load conventions<br/>local → global → default]
        Template[Load CLAUDE.md<br/>template]
    end

    subgraph DesignTpl["design_templates.py"]
        TplMeta[Template metadata<br/>+ stack compatibility]
        TplLoad[Load template<br/>local → global → bundled]
    end

    subgraph Safety["safety.py"]
        Scan[Regex secret<br/>detection]
    end

    subgraph Router["router.py"]
        PhaseRoute[Multi-phase routing<br/>pick backend per phase]
        Merge[Merge adjacent<br/>same-backend phases]
        Fallback[Fallback chain<br/>claude → gemini → codex]
        Detect[Keyword detection<br/>codex-suitable projects]
    end

    subgraph Config["config.py"]
        Check[Check backend<br/>on PATH]
    end

    subgraph Builder["prompt_builder.py"]
        PhasePrompt[Phase-specific prompts<br/>with specialist variants<br/>+ demo mode block<br/>+ design template block]
    end

    subgraph Runner["runner.py"]
        Exec[Build subprocess cmd<br/>serial + parallel execution]
        GitInit[Ensure git init]
        EditorOpen[Open in editor]
    end

    subgraph VerifyMod["verify.py"]
        InstallDeps[Install deps]
        RunChecks[Lint / typecheck /<br/>build / test]
        HealthProbe[Health endpoint probe]
    end

    Entry -->|flags provided| Stacks
    Entry -->|interactive mode| Interactive
    Interactive --> ScaffoldOpts
    Interactive --> Stacks

    Entry --> Conv
    Entry --> DesignTpl
    Entry --> Safety
    Entry --> Router

    Router --> Config
    Router --> Merge
    Conv --> Builder
    DesignTpl --> Builder
    Stacks --> Builder
    ScaffoldOpts --> Builder
    Safety -->|pass| Builder

    Builder -->|per phase| Runner
    Exec --> GitInit
    GitInit --> VerifyMod
    VerifyMod --> EditorOpen
```

## 3. Prompt Assembly

What gets composed into the final prompt that the AI CLI receives. Each phase generates its own prompt with specialist variants.

```mermaid
flowchart TD
    subgraph Inputs
        Answers[User answers<br/>name, stack, description,<br/>docker, services, auth, CI]
        ConvFile[conventions.md<br/>brand, coding standards,<br/>architecture, git rules]
        StackMeta[Stack metadata<br/>structure, libraries,<br/>dev commands, env hints]
        CrossDefaults[Cross-recipe defaults<br/>Python / TS / Docker<br/>standards]
        CIConfig[CI configuration<br/>mode + selected actions]
        AuthMeta[Auth provider metadata<br/>libraries + env hints]
        DesignTplInput[Design template<br/>brand guide, tokens,<br/>typography, components]
        ClaudeMD[CLAUDE.md template<br/>optional]
        DemoFlag[Demo mode flag<br/>zero-config env fallbacks]
        PhaseCtx[Phase context<br/>which phases, position<br/>in pipeline, prior work]
    end

    subgraph Assembly["prompt_builder.py"]
        direction TB
        Variant{Specialist backend<br/>for this phase?}
        BestPrompt[Best prompt variant<br/>role + structured XML<br/>+ detailed guidance]
        DefaultPrompt[Default prompt variant<br/>general instructions]
        Variant -- Yes --> BestPrompt
        Variant -- No --> DefaultPrompt

        Header[PROJECT DETAILS<br/>name, stack, description, docker]
        StackSection[STACK-SPECIFIC GUIDANCE<br/>structure, libs, commands,<br/>services, auth, env hints]
        DemoSection[DEMO MODE<br/>env fallbacks, mock data,<br/>auth bypass, banners]
        CISection[CI GUIDANCE<br/>workflow actions or<br/>blank template]
        CrossSection[CROSS-PROJECT STANDARDS<br/>tooling, naming, testing,<br/>docker best practices]
        ConvSection[CONVENTIONS<br/>full conventions.md content]
        DesignTplSection[DESIGN TEMPLATE<br/>brand tokens, typography,<br/>component patterns]
        Instructions[INSTRUCTIONS<br/>phase-specific tasks]
        ExtraSection[EXTRA INSTRUCTIONS<br/>user's freeform input]
        TemplateSection[CLAUDE.MD TEMPLATE<br/>if provided]
    end

    Answers --> Header
    StackMeta --> StackSection
    AuthMeta --> StackSection
    DemoFlag --> DemoSection
    CIConfig --> CISection
    CrossDefaults --> CrossSection
    ConvFile --> ConvSection
    DesignTplInput --> DesignTplSection
    PhaseCtx --> Instructions
    Answers --> ExtraSection
    ClaudeMD --> TemplateSection

    BestPrompt --> Prompt
    DefaultPrompt --> Prompt
    Header --> Prompt
    StackSection --> Prompt
    DemoSection --> Prompt
    CISection --> Prompt
    CrossSection --> Prompt
    ConvSection --> Prompt
    DesignTplSection --> Prompt
    Instructions --> Prompt
    ExtraSection --> Prompt
    TemplateSection --> Prompt

    Prompt[Final phase prompt] --> AICLI[AI CLI subprocess<br/>claude / gemini / codex<br/>with per-backend model]
```

## 4. Multi-Phase Routing

How the router decides which backend handles each scaffold phase.

```mermaid
flowchart TD
    Start[Stack + Description] --> Override{--use flag?}

    Override -- Yes --> Single[All phases → forced backend]
    Override -- No --> Detect

    Detect{Description matches<br/>codex phrases?} -- Yes --> CodxArch[Architecture → Codex]
    Detect -- No --> IdealArch[Architecture → Claude]

    CodxArch --> FrontendCheck
    IdealArch --> FrontendCheck

    FrontendCheck{Stack has<br/>frontend phase?}
    FrontendCheck -- Yes --> FrontendRoute[Frontend → Gemini]
    FrontendCheck -- No --> TestRoute

    FrontendRoute --> TestRoute[Tests → Codex]
    TestRoute --> VerifyRoute[Verify → Claude]

    VerifyRoute --> Available{Backend<br/>installed?}
    Available -- Yes --> Use[Use ideal backend]
    Available -- No --> FallbackChain["Fallback: claude → gemini → codex"]

    subgraph MergeStep["Phase Merging"]
        direction LR
        Before["[arch:claude, front:gemini,<br/>tests:codex, verify:claude]"]
        After["Group 1: arch → claude<br/>Group 2: front → gemini<br/>Group 3: tests → codex<br/>Group 4: verify → claude"]
        Before -->|merge adjacent| After
    end

    Use --> MergeStep
    FallbackChain --> MergeStep

    MergeStep --> ExecStrategy

    subgraph ExecStrategy["Execution Strategy"]
        direction TB
        Serial1["Step 1: Architecture<br/>serial — creates project structure"]
        Parallel["Step 2: Frontend + Tests<br/>parallel — independent directories"]
        Serial2["Step 3: Verify<br/>serial — needs all prior work"]
        Serial1 --> Parallel --> Serial2
    end

    style MergeStep fill:#e0f2f1,stroke:#009688,color:#1a1a1a
    style ExecStrategy fill:#e8f5e9,stroke:#4CAF50,color:#1a1a1a
```
