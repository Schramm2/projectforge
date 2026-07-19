# Forge prompt assembly

Forge builds one execution prompt per phase and merged prompts for `--dry-run` or `--export`.

![ProjectForge phase prompt assembly](forge-prompt-assembly.svg)

[Edit the D2 source](forge-prompt-assembly.d2).

`prompt_builder.py` combines normalized answers, stack metadata, effective conventions, design and media context, starter guidance, the assigned phase set, and the selected provider. User-controlled text passes through secret scanning before prompt assembly.

When one provider owns every phase, the builder selects the full scaffold contract. Multi-provider plans use targeted architecture, frontend, tests, or verify variants with provider-specific wording.

`scaffold_prompts.py` builds one bounded live prompt per routed phase and a separate bounded preview for each merged provider group. It exposes the live prompts as resumable progress records and formats previews for `--dry-run` or `--export`; previews are rebuilt for their merged phase groups rather than concatenated from live prompts. Model and approval settings remain provider CLI arguments rather than prompt content.
