# UbundiForge — Flow Diagrams

## 1. User Flow (Product View)

How a developer goes from idea to running project with Forge.

```mermaid
flowchart TD
    Start([Developer runs **forge**]) --> Describe

    subgraph Describe["1 — Describe your project"]
        Q1[Name your project]
        Q2[Pick a stack<br/>Next.js / FastAPI / Full-stack /<br/>CLI tool / TS package / Worker]
        Q3[Describe what it does]
        Q1 --> Q2 --> Q3
    end

    Describe --> Options

    subgraph Options["2 — Choose options"]
        Docker[Docker setup?]
        Customize{Want to customize?}
        Auth[Authentication<br/>Clerk / NextAuth / Supabase]
        Svc[Services<br/>PostgreSQL, OpenAI, AWS...]
        CI[CI/CD pipeline?]
        Extra[Any special instructions?]
        Docker --> Customize
        Customize -- Yes --> Auth --> Svc --> CI --> Extra
        Customize -- No --> Skip[ ]
    end

    Options --> Generate

    subgraph Generate["3 — Forge builds your project"]
        Conv[Loads your team's<br/>coding conventions]
        Prompt[Assembles a detailed<br/>AI brief from your choices]
        AI[Hands off to an AI<br/>coding assistant<br/>Claude / Gemini / Codex]
        Conv --> Prompt --> AI
    end

    Generate --> Output

    subgraph Output["4 — Ready to code"]
        direction LR
        Code[Complete project<br/>with all config,<br/>structure, and<br/>conventions baked in]
        Git[Git repo initialized<br/>with first commit]
        Editor[Opens in your<br/>editor]
        Code ~~~ Git ~~~ Editor
    end

    style Describe fill:#e8f4f8,stroke:#2196F3,color:#1a1a1a
    style Options fill:#fff3e0,stroke:#FF9800,color:#1a1a1a
    style Generate fill:#e8f5e9,stroke:#4CAF50,color:#1a1a1a
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

    subgraph Safety["safety.py"]
        Scan[Regex secret<br/>detection]
    end

    subgraph Router["router.py"]
        Pick[Pick backend<br/>for stack type]
        Fallback[Fallback chain<br/>claude → gemini → codex]
    end

    subgraph Config["config.py"]
        Check[Check backend<br/>on PATH]
    end

    subgraph Builder["prompt_builder.py"]
        Assemble[Assemble prompt:<br/>details + stack guidance<br/>+ conventions + CI<br/>+ cross-recipe defaults]
    end

    subgraph Runner["runner.py"]
        Exec[Build subprocess cmd<br/>run AI CLI in project dir]
        GitInit[Ensure git init]
        EditorOpen[Open in editor]
    end

    Entry -->|flags provided| Stacks
    Entry -->|interactive mode| Interactive
    Interactive --> ScaffoldOpts
    Interactive --> Stacks

    Entry --> Conv
    Entry --> Safety
    Entry --> Router

    Router --> Config
    Conv --> Builder
    Stacks --> Builder
    ScaffoldOpts --> Builder
    Safety -->|pass| Builder

    Builder --> Runner
    Runner --> GitInit
    GitInit --> EditorOpen
```

## 3. Prompt Assembly

What gets composed into the final prompt that the AI CLI receives.

```mermaid
flowchart TD
    subgraph Inputs
        Answers[User answers<br/>name, stack, description,<br/>docker, services, auth, CI]
        ConvFile[conventions.md<br/>brand, coding standards,<br/>architecture, git rules]
        StackMeta[Stack metadata<br/>structure, libraries,<br/>dev commands, env hints]
        CrossDefaults[Cross-recipe defaults<br/>Python / TS / Docker<br/>standards]
        CIConfig[CI configuration<br/>mode + selected actions]
        AuthMeta[Auth provider metadata<br/>libraries + env hints]
        ClaudeMD[CLAUDE.md template<br/>optional]
    end

    subgraph Assembly["prompt_builder.py"]
        Header[PROJECT DETAILS<br/>name, stack, description, docker]
        StackSection[STACK-SPECIFIC GUIDANCE<br/>structure, libs, commands,<br/>services, auth, env hints]
        CISection[CI GUIDANCE<br/>workflow actions or<br/>blank template]
        CrossSection[CROSS-PROJECT STANDARDS<br/>tooling, naming, testing,<br/>docker best practices]
        ConvSection[CONVENTIONS<br/>full conventions.md content]
        Instructions[INSTRUCTIONS<br/>what to generate]
        ExtraSection[EXTRA INSTRUCTIONS<br/>user's freeform input]
        TemplateSection[CLAUDE.MD TEMPLATE<br/>if provided]
    end

    Answers --> Header
    StackMeta --> StackSection
    AuthMeta --> StackSection
    CIConfig --> CISection
    CrossDefaults --> CrossSection
    ConvFile --> ConvSection
    Answers --> ExtraSection
    ClaudeMD --> TemplateSection

    Header --> Prompt
    StackSection --> Prompt
    CISection --> Prompt
    CrossSection --> Prompt
    ConvSection --> Prompt
    Instructions --> Prompt
    ExtraSection --> Prompt
    TemplateSection --> Prompt

    Prompt[Final prompt string] --> AICLI[AI CLI subprocess<br/>claude / gemini / codex]
```
