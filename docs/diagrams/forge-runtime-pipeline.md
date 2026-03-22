# Forge Runtime Pipeline

This document shows the end-to-end scaffold path across modules after Forge has a finalized `answers` payload.

## Current Behavior

- The main scaffold pipeline lives in `cli.py` and delegates to focused helper modules.
- Media copy happens before AI execution so generated code can reference imported assets immediately.
- Verification, quality memory, scaffold logs, and preference learning all happen after generation.

## End-To-End Module Flow

```mermaid
flowchart TD
    CLI["CLI command"] --> Setup["Setup wizard"]
    CLI --> Prompts["Interactive answers"]
    CLI --> Router["Phase routing and merge"]
    CLI --> Quality["Read quality memory"]

    CLI --> Conventions["Load conventions and template"]
    CLI --> Design["Load design template"]
    CLI --> Media["Scan media and build manifest"]
    CLI --> Safety["Secret scan"]
    CLI --> Builder["Build phase prompts"]

    Media --> Copy["Copy media into project"]
    Builder --> Runner["Run scaffold phases"]
    Copy --> Runner

    Runner --> Manifest["Write scaffold manifest"]
    Manifest --> Git["Initialize git"]
    Git --> Verify["Run verify checks"]
    Verify --> QualityWrite["Write quality signals"]
    QualityWrite --> Hook["Run post scaffold hook"]
    Hook --> Log["Append scaffold log"]
    Log --> Prefs["Record preferences"]
    Prefs --> Dashboard["Render dashboard"]
    Dashboard --> Card["Write project card and badge README"]
    Card --> Sound["Play completion sound"]
    Sound --> Editor["Open preferred editor"]
```

## Post-Scaffold Outputs

- Project manifest at `.forge/scaffold.json`
- Conventions snapshot at `.forge/conventions-snapshot.md`
- Optional imported media files in the stack-specific asset directory
- Optional git repository initialization
- Verification report used for dashboard rendering and quality-memory updates
- Global scaffold history in `~/.forge/scaffold.log`
- Updated preference memory in `~/.forge/preferences.json`
- Updated quality memory in `~/.forge/quality.jsonl`

## Related But Separate Paths

- `checks.py` powers `forge check` and `forge check --fix`
- `evolutions.py` powers `forge evolve`
- `replay` rebuilds prompts from `.forge/scaffold.json` instead of running the normal questionnaire
