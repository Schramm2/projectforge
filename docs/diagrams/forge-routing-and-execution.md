# Forge routing and execution

Forge chooses a provider per scaffold phase, merges adjacent phases owned by the same provider, and then runs the resulting execution windows.

## Provider selection

![ProjectForge provider routing logic](forge-routing-logic.svg)

[Edit the routing D2 source](forge-routing-logic.d2).

An explicit `--use` value assigns one provider to every phase. Automatic routing starts from the stack's phase list, removes providers that are not ready, applies the specialist mapping, falls back in deterministic order, and may use local quality evidence when an alternative wins by more than `0.1`.

## Phase merging and execution

![ProjectForge phase merging and execution strategy](forge-execution-strategy.svg)

[Edit the execution D2 source](forge-execution-strategy.d2).

Standard mode runs architecture first, may run frontend and tests in parallel, and runs verify last. `--agents` keeps phase windows sequential while allowing independent tasks inside the active phase to run in parallel before reconciliation.

Prompt-only runs print or export merged prompts and make no provider call.
