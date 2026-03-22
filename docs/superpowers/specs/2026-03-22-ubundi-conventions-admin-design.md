# Ubundi Conventions Admin Design

## Summary

UbundiForge currently spreads convention logic across a single bundled Markdown blob, stack metadata, prompt assembly code, design templates, and maintainer docs. That makes it hard for Ubundi admins to inspect, update, and reason about how conventions affect a given stack or language.

This design introduces a layered conventions source tree backed by repo-managed files, plus a Forge admin experience that can browse, validate, preview, diff, and update the convention system without turning it into a separate CMS. The source of truth remains this repository, changes reflect immediately during local development in the repo, and released Forge versions distribute those updates to everyone else.

## Goals

- Make Ubundi conventions easy to browse by stack, language, and global rule family.
- Replace the current single-file convention model with a layered multi-folder source tree.
- Keep conventions human-editable with Markdown as the main authoring format.
- Preserve Forge's current prompt assembly model while changing the input source.
- Give repo admins an admin-level view for validation, preview, history, and diff inspection.
- Ensure prompt output is compiled from the new conventions source so prompt logic and admin-edited content cannot drift apart.

## Non-Goals

- Build a remote convention service or runtime pull-from-server model.
- Let per-project or per-user edits become the canonical Ubundi convention source.
- Replace git as the primary source of version history.
- Build a heavyweight fully custom content-management system.

## Product Decisions

- Canonical conventions are edited by repo admins only.
- The admin experience is hybrid: repo folders remain the source of truth, and Forge provides an admin screen on top.
- The conventions tree uses a hybrid format:
  - Markdown for convention content.
  - Small structured metadata files for inheritance, ordering, and prompt assembly.
- V1 includes browse, edit support, validation, preview, history, and diff capabilities.
- Convention changes affect local development in this repo immediately and ship broadly on the next Forge release.
- History and diffs come from git plus a lightweight manifest/index optimized for admin browsing.

## Proposed Source Tree

```text
conventions/
  global/
    shared.md
    prompt-policy.md
  languages/
    python/
      base.md
      testing.md
      packaging.md
      metadata.yaml
    typescript/
      base.md
      testing.md
      packaging.md
      metadata.yaml
  stacks/
    fastapi/
      overview.md
      structure.md
      prompt-rules.md
      metadata.yaml
    fastapi-ai/
      overview.md
      structure.md
      prompt-rules.md
      metadata.yaml
    nextjs/
      overview.md
      structure.md
      prompt-rules.md
      metadata.yaml
    both/
      overview.md
      structure.md
      prompt-rules.md
      metadata.yaml
  prompts/
    assembly-policy.md
    claude-md-policy.md
  manifests/
    conventions-index.yaml
    prompt-bundles.yaml
```

## Content Model

### Markdown convention files

Markdown files hold the actual human-readable Ubundi guidance. These files are written for admins first, not machines first. They should be easy to scan and easy to update in normal editor workflows.

Examples:

- `global/shared.md`: cross-project rules that apply widely.
- `languages/python/base.md`: Python coding and architecture conventions.
- `stacks/fastapi/structure.md`: FastAPI-specific structure and service guidance.
- `prompts/assembly-policy.md`: rules for how compiled conventions should be shaped when inserted into prompts.

### Metadata files

Each language or stack folder includes a small `metadata.yaml` file that describes:

- identifier
- title
- inheritance sources
- file ordering
- optional tags such as `backend`, `frontend`, `python`, `typescript`, `ai`
- whether a file participates in prompt compilation, admin browsing only, or both

These files are intentionally small so admins can safely edit them inline from Forge when making wiring changes.

### Manifest files

The `manifests/` directory provides a lightweight registry layer to support the admin experience. It does not become a second source of truth. Instead, it indexes and groups the source tree for fast browse, preview, and history views.

Examples:

- `conventions-index.yaml`: known convention groups, titles, and paths.
- `prompt-bundles.yaml`: default compilation bundles such as `fastapi`, `nextjs`, or `both`.

## Architecture

### 1. Conventions source layer

The new `conventions/` directory becomes the source of truth for canonical Ubundi conventions that ship with Forge.

Responsibilities:

- hold human-edited convention content
- define reusable global, language, and stack layers
- support clear stack-by-stack inspection

### 2. Convention registry

A new registry layer reads the `conventions/` tree, discovers source files, loads metadata, and builds an internal map of available layers and bundles.

Responsibilities:

- discover all convention files and metadata
- resolve identities and labels for admin browsing
- expose inheritance relationships
- surface malformed or missing metadata as validation errors

### 3. Convention compiler

A compiler layer resolves the selected layers into the compiled convention bundle that prompt assembly consumes.

Responsibilities:

- merge global, language, and stack layers
- apply deterministic ordering
- prevent duplicate inclusion
- stop on cycles or invalid references
- emit the final convention text and structured sections needed by prompt assembly

This preserves today's broad prompt-building behavior while replacing the current single Markdown blob with compiled layered inputs.

### 4. Prompt integration

`prompt_builder.py` should stop depending on one large conventions string as the primary authored source and instead consume compiled bundles generated by the new compiler.

Responsibilities:

- request the right bundle for the chosen stack
- continue injecting conventions into prompts in a familiar way
- keep design templates, stack metadata, and CI/auth sections compatible with the new convention source

### 5. Admin experience

Forge should add an admin entry point, such as `forge admin conventions`, that lets repo admins work with conventions without hunting through unrelated code.

Capabilities:

- browse by global, language, stack, and prompt policy
- inspect inheritance chains
- preview the compiled convention bundle for a selected stack
- preview prompt-facing output for a selected stack
- validate the conventions tree
- edit small metadata inline
- open long Markdown files in the editor
- inspect recent changes through git-backed history and diffs

### 6. History and diffs

History should come from git, but the admin view can present it in a conventions-aware way using the manifest/index.

Responsibilities:

- show recent commits touching convention files
- group changes by stack or rule family where possible
- show diffs for a selected stack bundle, not just a raw file path list
- degrade gracefully if git history is unavailable

## Admin User Experience

The admin UX should be practical and repo-native rather than app-heavy.

Example flow:

1. Run `forge admin conventions`.
2. Choose a scope such as `stack -> fastapi`.
3. View included global, language, and stack sources in compiled order.
4. Preview the compiled conventions bundle and prompt-facing output.
5. Edit metadata inline if inheritance or ordering needs to change.
6. Open Markdown source files in the editor for substantial content edits.
7. Re-run validation and preview.
8. Inspect git-backed history or diffs before committing.

This keeps long-form authoring where it belongs, in Markdown files, while still making the convention system understandable from inside Forge.

## Validation Rules

The validator should catch admin mistakes before they affect prompt generation.

Validation should include:

- missing referenced files
- broken inheritance references
- cycles in inheritance graphs
- duplicate layer inclusion
- conflicting ordering declarations
- empty or nearly empty required convention files
- missing required layers for known stack bundles
- manifest entries pointing to removed files

Validation output should always point to exact files and exact broken references where possible.

## Prompt Preview Behavior

Preview is a core part of the design because admins need to understand what the model will actually receive.

Preview modes should include:

- compiled convention bundle for a selected stack
- prompt-facing convention section only
- inheritance trace showing which files contributed content

This is especially important for stacks like `both`, where guidance may come from global rules, Python rules, TypeScript rules, and stack-specific rules at once.

## Migration Strategy

Migration should be incremental rather than a one-shot rewrite.

### Phase 1: establish the source tree

- add the new `conventions/` directory and initial metadata layout
- move existing convention content out of `DEFAULT_CONVENTIONS`
- map current stack-specific guidance into the new folders

### Phase 2: add registry and compiler

- implement discovery, indexing, inheritance, and compilation
- keep compatibility while the prompt builder still supports the current path

### Phase 3: switch prompt assembly

- move prompt assembly onto compiled convention bundles
- ensure generated prompt output remains equivalent or intentionally improved

### Phase 4: add admin flows

- add browse, validate, preview, metadata edit, and open-file flows
- add history and diff presentation on top of git

### Phase 5: retire the old single-blob source

- remove or slim down legacy bundled convention logic after parity is verified
- update maintainer docs so the new flow becomes the standard path

## Error Handling

Failure modes should be explicit and actionable.

- If metadata is invalid, validation should fail with clear file-level errors.
- If preview cannot compile due to inheritance problems, Forge should stop and explain the specific chain that failed.
- If a selected stack is missing required convention layers, Forge should list the missing layers and the expected paths.
- If git history is unavailable, the admin view should still allow browse, validation, and preview.
- If a manifest entry becomes stale, Forge should identify the stale reference and offer reindexing.

## Testing Strategy

Testing should focus on correctness, safety, and migration stability.

### Unit coverage

- source discovery
- metadata parsing
- inheritance resolution
- compilation ordering
- duplicate prevention
- validation failures
- manifest/index generation

### Integration coverage

- compiled bundle generation per stack
- prompt builder consuming compiled bundles
- admin preview output
- git-backed history and diff formatting

### Regression coverage

- prompt content parity for representative stacks
- migration from current defaults into the new structure
- compatibility for local development workflows in this repo

## Documentation Changes

Docs should make the new system obvious to maintainers.

Update:

- maintainer admin documentation
- stack extension guidance
- prompt architecture documentation
- any references that still direct admins to edit a single bundled conventions blob

## Open Questions

No unresolved product questions remain from this planning session. The next step is implementation planning and task breakdown.
