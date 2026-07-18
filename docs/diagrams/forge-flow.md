# ProjectForge diagrams

Start with the product map for the system boundary, then use the user journey for the install-to-handoff path. The remaining diagrams explain one part of the product in more detail.

## Product map

![ProjectForge product map](forge-product-map.svg)

[Read the product overview](forge-product-overview.md) or edit the [D2 source](forge-product-map.d2).

## Choose a diagram

| Question | Diagram |
| --- | --- |
| How does a new user get from installation to a verified project? | [New user journey](forge-user-journey.md) |
| What does Forge own, and what stays with the provider or generated project? | [Product overview](forge-product-overview.md) |
| What can I do after the first scaffold? | [Project lifecycle](forge-project-lifecycle.md) |
| How does first-run setup and input collection work? | [Input flow](forge-input-flow.md) |
| How are providers chosen and phases scheduled? | [Routing and execution](forge-routing-and-execution.md) |
| What goes into each provider prompt? | [Prompt assembly](forge-prompt-assembly.md) |
| What happens during a live scaffold? | [Runtime pipeline](forge-runtime-pipeline.md) |
| What crosses the provider boundary, and what evidence stays local? | [Trust boundaries](forge-trust-boundaries.md) |

## Editing and rendering

The `.d2` files are the editable source of truth. Render one diagram from the repository root:

```bash
docs/diagrams/render.sh docs/diagrams/forge-user-journey.d2
```

Run `docs/diagrams/render.sh` with no arguments to rebuild every SVG in this folder.
