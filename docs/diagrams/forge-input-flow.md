# Forge Input Flow

This document covers how Forge gets from `forge` to a finalized `answers` payload.

## Current Behavior

- Auto-setup runs only when Forge has never been configured and the command is not prompt-only.
- Non-interactive mode kicks in when `--name`, `--stack`, and `--description` are all provided.
- Interactive mode now includes smart defaults from prior scaffolds and a review/edit loop before generation starts.

## Setup And Input Collection

```mermaid
flowchart TD
    Start["Run forge"] --> AutoSetup{"needs_setup()<br/>and not dry-run/export?"}

    AutoSetup -- Yes --> SetupWizard
    AutoSetup -- No --> InputMode

    subgraph SetupWizard["First-run setup in setup.py"]
        direction TB
        S1[1. Detect AI CLIs and readiness]
        S2[2. Show routing summary]
        S3[3. Save preferred model per ready backend]
        S4[4. Detect editors and choose default]
        S5[5. Check git and optional identity setup]
        S6[6. Check Docker availability]
        S7[7. Save default projects directory]
        S8[8. Create or confirm conventions and media folders]
        S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7 --> S8
    end

    SetupWizard --> PostSetup{"Create a project now?"}
    PostSetup -- Yes --> InputMode
    PostSetup -- No --> Exit1["Exit"]

    InputMode{"All required CLI flags provided?"} -- Yes --> NonInteractive
    InputMode -- No --> Interactive

    subgraph NonInteractive["Non-interactive path in cli.py"]
        direction TB
        N1["Normalize stack alias"]
        N2["Validate auth provider,<br/>design template, CI mode/actions"]
        N3["Resolve Docker default"]
        N4["Resolve media selection"]
        N5["Build answers dict"]
        N1 --> N2 --> N3 --> N4 --> N5
    end

    subgraph Interactive["Interactive path in prompts.py"]
        direction TB
        I1["Ask project basics:<br/>name, stack, description, Docker"]
        I2{"Dominant saved defaults<br/>available?"}
        I3["Offer usual setup"]
        I4["Ask design template and media collection"]
        I5["Ask auth, services, CI, and extra instructions"]
        I6["Ask demo mode"]
        I7["Show review panel"]
        I8{"Scaffold or edit?"}

        I1 --> I2
        I2 -- Yes --> I3
        I2 -- No --> I4
        I3 -- Use defaults --> I7
        I3 -- Skip defaults --> I4
        I4 --> I5 --> I6 --> I7 --> I8
        I8 -- Edit basics --> I1
        I8 -- Edit design/media --> I4
        I8 -- Edit integrations --> I5
        I8 -- Edit demo --> I6
        I8 -- Cancel --> Exit2["Exit"]
    end

    NonInteractive --> Answers["Final answers payload"]
    Interactive --> Answers
```

## Answers Shape

The finalized payload now consistently includes:

- `name`
- `stack`
- `description`
- `docker`
- `design_template`
- `media_collection`
- `auth_provider`
- `services`
- `ci` with `include`, `mode`, and `actions`
- `extra`
- `demo_mode`
