"""Convention bundle compilation for stack-aware prompts."""

from .convention_models import (
    CompiledBundle,
    ConventionRecord,
    ConventionRegistry,
    ConventionValidationError,
)

_MIN_BUNDLE_LENGTH = 50


def _resolve_sources_for_record(
    registry: ConventionRegistry,
    record: ConventionRecord,
    *,
    active: tuple[str, ...] = (),
) -> tuple[str, ...]:
    if record.record_id in active:
        cycle = " -> ".join((*active, record.record_id))
        raise ConventionValidationError(f"Convention inheritance cycle detected: {cycle}")

    source_ids: list[str] = []
    seen: set[str] = set()

    for inherited_id in record.inherits:
        inherited_record = registry.record(inherited_id)
        for source_id in _resolve_sources_for_record(
            registry,
            inherited_record,
            active=(*active, record.record_id),
        ):
            if source_id in seen:
                continue
            seen.add(source_id)
            source_ids.append(source_id)

    for source_id in record.source_ids:
        if source_id in seen:
            continue
        seen.add(source_id)
        source_ids.append(source_id)

    return tuple(source_ids)


def _all_sources_bundle(registry: ConventionRegistry, bundle_id: str) -> CompiledBundle:
    sources = tuple(source.path for source in registry.sources.values())
    prompt_block = "\n\n".join(
        path.read_text().strip() for path in sources if path.read_text().strip()
    ).strip()
    warnings: list[str] = []
    if not prompt_block:
        warnings.append("Conventions bundle is empty.")
    elif len(prompt_block) < _MIN_BUNDLE_LENGTH:
        warnings.append("Conventions bundle is very short — consider adding more detail.")
    return CompiledBundle(
        bundle_id=bundle_id,
        prompt_block=prompt_block,
        sources=sources,
        warnings=tuple(warnings),
    )


def compile_bundle(registry: ConventionRegistry, stack: str | None = None) -> CompiledBundle:
    """Compile a deterministic prompt bundle for the requested stack."""

    if not registry.records:
        return _all_sources_bundle(registry, stack or "default")

    records: list[ConventionRecord] = []
    global_record = registry.global_record()
    if global_record is not None:
        records.append(global_record)

    bundle_id = stack or "default"
    if stack is not None:
        stack_record = registry.stack(stack)
        if stack_record.language:
            records.append(registry.language(stack_record.language))
        records.append(stack_record)

    ordered_source_ids: list[str] = []
    seen_source_ids: set[str] = set()
    for record in records:
        for source_id in _resolve_sources_for_record(registry, record):
            if source_id in seen_source_ids:
                continue
            seen_source_ids.add(source_id)
            ordered_source_ids.append(source_id)

    if not ordered_source_ids and registry.sources:
        return _all_sources_bundle(registry, bundle_id)

    ordered_paths = tuple(registry.source(source_id).path for source_id in ordered_source_ids)
    prompt_block = "\n\n".join(
        path.read_text().strip() for path in ordered_paths if path.read_text().strip()
    ).strip()

    warnings: list[str] = []
    if not prompt_block:
        warnings.append("Conventions bundle is empty.")
    elif len(prompt_block) < _MIN_BUNDLE_LENGTH:
        warnings.append("Conventions bundle is very short — consider adding more detail.")

    return CompiledBundle(
        bundle_id=bundle_id,
        prompt_block=prompt_block,
        sources=ordered_paths,
        warnings=tuple(warnings),
    )
