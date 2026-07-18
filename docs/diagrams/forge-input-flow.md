# Forge input flow

Forge reaches one normalized answers payload through either the interactive questionnaire or validated CLI flags.

![ProjectForge setup and input collection flow](forge-input-flow.svg)

[Edit the D2 source](forge-input-flow.d2).

## Current behavior

- Auto-setup runs only when Forge has not been configured and the command is not prompt-only.
- Non-interactive mode starts when `--name`, `--stack`, and `--description` are all present.
- Interactive mode offers learned defaults and ends with a review-and-edit gate.
- Both paths resolve the same structured options before routing begins.

The final payload includes the project name, stack, description, Docker choice, design and media selections, auth and service choices, CI configuration, extra instructions, and demo mode.
