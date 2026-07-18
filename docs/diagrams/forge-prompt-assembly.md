# Forge prompt assembly

Forge builds one execution prompt per phase and merged prompts for `--dry-run` or `--export`.

![ProjectForge phase prompt assembly](forge-prompt-assembly.svg)

[Edit the D2 source](forge-prompt-assembly.d2).

The builder combines the normalized answers, stack metadata, effective conventions, design and media context, starter guidance, the assigned phase set, and the selected provider. User-controlled text passes through secret scanning before execution.

When one provider owns every phase, Forge builds the full scaffold prompt. Multi-provider plans use targeted architecture, frontend, tests, or verify variants with provider-specific wording. Model and approval settings are provider CLI arguments rather than prompt content.
