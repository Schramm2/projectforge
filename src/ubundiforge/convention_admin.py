"""Admin helpers for browsing and previewing bundled conventions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Group, RenderableType
from rich.text import Text

from .convention_compiler import compile_bundle
from .convention_history import GitHistoryResult
from .convention_models import ConventionRecord, ConventionRegistry, ConventionValidationError
from .ui import (
    grouped_lines,
    make_history_panel,
    make_panel,
    make_path_table,
    subtle,
)


@dataclass(frozen=True)
class ConventionScopeItem:
    """A browseable convention item within an admin scope."""

    key: str
    label: str
    target: str


@dataclass(frozen=True)
class ConventionScope:
    """A top-level admin scope."""

    name: str
    label: str
    items: tuple[ConventionScopeItem, ...]


def _scope_item(key: str, label: str, target: str) -> ConventionScopeItem:
    return ConventionScopeItem(key=key, label=label, target=target)


def _record_item(record: ConventionRecord) -> ConventionScopeItem:
    label = record.browse_label or record.label
    return _scope_item(record.metadata_id, label, record.record_id)


def list_scopes(registry: ConventionRegistry) -> tuple[ConventionScope, ...]:
    """List the admin browse scopes backed by the existing registry/manifests."""

    global_items: tuple[ConventionScopeItem, ...] = ()
    global_record = registry.global_record()
    if global_record is not None:
        global_items = (_record_item(global_record),)

    language_items = tuple(
        _record_item(registry.language(language_id))
        for language_id in sorted(registry.language_record_ids)
    )
    stack_items = tuple(
        _record_item(registry.stack(stack_id)) for stack_id in sorted(registry.stack_record_ids)
    )

    prompt_items: list[ConventionScopeItem] = []
    bundle_definitions = registry.bundle_definitions
    if "default" in bundle_definitions:
        prompt_items.append(_scope_item("default", "Default bundle", "default"))
    stack_overrides = bundle_definitions.get("stack_overrides")
    if isinstance(stack_overrides, dict):
        for stack_id in sorted(stack_overrides):
            label = registry.browse_labels.get(stack_id)
            if not isinstance(label, str) or not label.strip():
                label = registry.stack(stack_id).browse_label or registry.stack(stack_id).label
            prompt_items.append(_scope_item(stack_id, label, stack_id))

    return (
        ConventionScope(name="global", label="Global", items=global_items),
        ConventionScope(name="language", label="Language", items=language_items),
        ConventionScope(name="stack", label="Stack", items=stack_items),
        ConventionScope(name="prompt", label="Prompt", items=tuple(prompt_items)),
    )


def _resolve_record(registry: ConventionRegistry, target: str) -> ConventionRecord:
    cleaned = target.strip()
    if not cleaned:
        raise ConventionValidationError("A convention target is required.")
    if cleaned == "global":
        record = registry.global_record()
        if record is None:
            raise ConventionValidationError("Global conventions are not configured.")
        return record
    if cleaned in registry.stack_record_ids:
        return registry.stack(cleaned)
    if cleaned in registry.language_record_ids:
        return registry.language(cleaned)
    return registry.record(cleaned)


def _append_chain(
    registry: ConventionRegistry,
    record: ConventionRecord,
    chain: list[ConventionRecord],
    seen: set[str],
) -> None:
    for inherited_id in record.inherits:
        inherited_record = registry.record(inherited_id)
        _append_chain(registry, inherited_record, chain, seen)
    if record.record_id not in seen:
        seen.add(record.record_id)
        chain.append(record)


def resolve_record_chain(registry: ConventionRegistry, target: str) -> tuple[ConventionRecord, ...]:
    """Resolve the effective compilation chain for a record or stack id."""

    record = _resolve_record(registry, target)
    chain: list[ConventionRecord] = []
    seen: set[str] = set()

    global_record = registry.global_record()
    if global_record is not None and record.record_id != global_record.record_id:
        _append_chain(registry, global_record, chain, seen)

    if record.kind == "stacks" and record.language:
        _append_chain(registry, registry.language(record.language), chain, seen)

    _append_chain(registry, record, chain, seen)
    return tuple(chain)


def render_validation_summary(registry: ConventionRegistry) -> RenderableType:
    """Render a concise validation success summary for the registry."""

    lines = [
        Text("Validation passed", style="bold"),
        subtle(f"Root: {registry.root}"),
        subtle(f"{len(registry.records)} records"),
        subtle(f"{len(registry.sources)} markdown sources"),
    ]
    return make_panel(grouped_lines(lines), title="Conventions", accent="aqua")


def render_inheritance_trace(registry: ConventionRegistry, target: str) -> RenderableType:
    """Render the effective record chain for a stack or record id."""

    chain = resolve_record_chain(registry, target)
    chain_text = " -> ".join(record.record_id for record in chain)
    lines = [
        subtle(f"Target: {target}"),
        Text(chain_text, style="bold"),
    ]
    return make_panel(grouped_lines(lines), title="Inheritance Trace", accent="violet")


def render_record_summary(registry: ConventionRegistry, target: str) -> RenderableType:
    """Render a browse-friendly summary for a record-backed convention target."""

    record = _resolve_record(registry, target)
    paths = tuple(registry.source(source_id).path for source_id in record.source_ids)
    details = make_panel(
        grouped_lines(
            [
                subtle(f"Record: {record.record_id}"),
                subtle(f"Label: {record.browse_label or record.label}"),
                subtle(f"Language: {record.language or 'n/a'}"),
            ]
        ),
        title="Convention Record",
        accent="aqua",
    )
    return Group(
        details,
        render_inheritance_trace(registry, record.record_id),
        make_path_table(paths, root=registry.root, title="Editable Markdown"),
    )


def render_bundle_preview(registry: ConventionRegistry, stack: str | None) -> RenderableType:
    """Render a compiled bundle preview using the existing compiler."""

    bundle = compile_bundle(registry, stack=stack)
    relative_sources = tuple(path.relative_to(registry.root) for path in bundle.sources)
    preview_lines = [line for line in bundle.prompt_block.splitlines() if line.strip()]
    excerpt = preview_lines[:8]

    if not excerpt:
        excerpt = ["(empty bundle)"]

    excerpt_lines = [
        Text(line, style="bold") if index == 0 else line for index, line in enumerate(excerpt)
    ]
    preview_panel = make_panel(
        grouped_lines(excerpt_lines),
        title="Prompt Excerpt",
        accent="amber",
    )

    summary_lines = [subtle(f"{len(bundle.sources)} source files")]
    for warning in bundle.warnings:
        summary_lines.append(subtle(f"Warning: {warning}"))

    return Group(
        make_panel(
            grouped_lines(summary_lines),
            title=f"Compiled bundle: {bundle.bundle_id}",
            accent="aqua",
        ),
        make_path_table(relative_sources, title="Bundle Sources", accent="violet"),
        preview_panel,
    )


def render_history_result(result: GitHistoryResult) -> RenderableType:
    """Render a git history result in the repo's existing Rich style."""

    if result.available:
        return make_history_panel(
            result.entries,
            title=f"History: {result.target}",
            accent="amber",
        )
    return make_panel(
        grouped_lines([subtle(result.message)]),
        title=f"History: {result.target}",
        accent="amber",
    )


def _normalize_relative_markdown_path(relative_path: str) -> str:
    cleaned = relative_path.strip().strip("/")
    if cleaned.startswith("conventions/"):
        return cleaned.removeprefix("conventions/")
    return cleaned


def resolve_open_path(root: Path, relative_path: str) -> Path:
    """Resolve a safe, editable markdown path within the conventions tree."""

    normalized = _normalize_relative_markdown_path(relative_path)
    if not normalized.endswith(".md"):
        raise ConventionValidationError("Only markdown files can be opened from conventions.")

    resolved_root = root.resolve()
    candidate = (resolved_root / normalized).resolve()
    if resolved_root not in candidate.parents:
        raise ConventionValidationError("Requested markdown path is outside the conventions tree.")
    if not candidate.exists():
        raise ConventionValidationError(f"Convention markdown file not found: {normalized}")
    return candidate
