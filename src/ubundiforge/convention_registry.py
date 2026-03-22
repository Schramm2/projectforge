"""Registry discovery and validation for bundled conventions."""

from pathlib import Path

import yaml

from .convention_models import (
    ConventionRecord,
    ConventionRegistry,
    ConventionSource,
    ConventionValidationError,
)


def _default_conventions_root() -> Path:
    package_dir = Path(__file__).resolve().with_name("conventions")
    repo_dir = Path(__file__).resolve().parents[2] / "conventions"
    return package_dir if package_dir.exists() else repo_dir


def _read_yaml(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text())
    if isinstance(data, dict):
        return data
    return {}


def _normalize_record_id(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _normalize_source_id(path: Path, root: Path) -> str:
    return path.relative_to(root).with_suffix("").as_posix()


def _normalize_inherit_id(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConventionValidationError(f"Invalid inherited convention id: {value!r}")
    return value.strip().removesuffix(".md")


def _metadata_kind(record_id: str) -> str:
    if "/" not in record_id:
        return record_id
    return record_id.split("/", 1)[0]


def _discover_all_markdown_sources(root: Path) -> dict[str, ConventionSource]:
    sources: dict[str, ConventionSource] = {}
    for path in sorted(root.rglob("*.md")):
        if "manifests" in path.parts:
            continue
        source_id = _normalize_source_id(path, root)
        sources[source_id] = ConventionSource(source_id=source_id, path=path)
    return sources


def _discover_records(
    root: Path,
) -> tuple[
    dict[str, ConventionRecord],
    dict[str, ConventionSource],
    dict[str, str],
    dict[str, str],
]:
    records: dict[str, ConventionRecord] = {}
    sources = _discover_all_markdown_sources(root)
    stack_record_ids: dict[str, str] = {}
    language_record_ids: dict[str, str] = {}
    resolved_root = root.resolve()

    for metadata_path in sorted(root.rglob("metadata.yaml")):
        if "manifests" in metadata_path.parts:
            continue

        record_dir = metadata_path.parent
        record_id = _normalize_record_id(record_dir, root)
        metadata = _read_yaml(metadata_path)

        metadata_id = str(metadata.get("id") or record_dir.name)
        label = str(metadata.get("label") or metadata_id)
        browse_label = metadata.get("browse_label")
        if browse_label is not None:
            browse_label = str(browse_label)
        language = metadata.get("language")
        if language is not None:
            language = str(language)

        markdown_files = metadata.get("markdown_files") or []
        if not isinstance(markdown_files, list):
            raise ConventionValidationError(
                f"Convention record {record_id} has invalid markdown_files metadata."
            )

        source_ids: list[str] = []
        resolved_paths: set[Path] = set()
        for markdown_file in markdown_files:
            if not isinstance(markdown_file, str) or not markdown_file.strip():
                raise ConventionValidationError(
                    f"Convention record {record_id} has an invalid markdown file entry."
                )

            source_path = (record_dir / markdown_file).resolve()
            if source_path in resolved_paths:
                raise ConventionValidationError(
                    f"Convention record {record_id} includes {markdown_file} more than once."
                )
            resolved_paths.add(source_path)

            if not source_path.exists():
                raise ConventionValidationError(
                    "Convention record "
                    f"{record_id} references missing markdown file {markdown_file}."
                )
            if resolved_root not in source_path.parents and source_path != resolved_root:
                raise ConventionValidationError(
                    "Convention record "
                    f"{record_id} references markdown outside the conventions tree."
                )

            source_id = _normalize_source_id(source_path, resolved_root)
            source_ids.append(source_id)
            sources[source_id] = ConventionSource(
                source_id=source_id,
                path=source_path,
                record_id=record_id,
            )

        inherits_value = metadata.get("inherits") or []
        if isinstance(inherits_value, str):
            inherits = (_normalize_inherit_id(inherits_value),)
        elif isinstance(inherits_value, list):
            inherits = tuple(_normalize_inherit_id(item) for item in inherits_value)
        else:
            raise ConventionValidationError(
                f"Convention record {record_id} has invalid inherits metadata."
            )

        record = ConventionRecord(
            record_id=record_id,
            metadata_id=metadata_id,
            kind=_metadata_kind(record_id),
            path=record_dir,
            label=label,
            browse_label=browse_label,
            language=language,
            inherits=inherits,
            source_ids=tuple(source_ids),
        )
        records[record_id] = record

        if record.kind == "stacks":
            stack_record_ids[metadata_id] = record_id
        elif record.kind == "languages":
            language_record_ids[metadata_id] = record_id

    return records, sources, stack_record_ids, language_record_ids


def _validate_references(registry: ConventionRegistry) -> None:
    for record in registry.records.values():
        for inherited_id in record.inherits:
            if inherited_id not in registry.records:
                raise ConventionValidationError(
                    f"Convention record {record.record_id} inherits unknown record {inherited_id}."
                )


def _validate_bundle_manifests(registry: ConventionRegistry) -> None:
    bundle_definitions = registry.bundle_definitions
    if not bundle_definitions:
        return

    if "default" in bundle_definitions and registry.global_record() is None:
        raise ConventionValidationError("Bundle manifests require a global convention layer.")

    stack_overrides = bundle_definitions.get("stack_overrides") or {}
    if not isinstance(stack_overrides, dict):
        raise ConventionValidationError("Bundle manifests define invalid stack_overrides metadata.")

    for stack_id in stack_overrides:
        stack_record = registry.stack_record_ids.get(stack_id)
        if stack_record is None:
            raise ConventionValidationError(
                f"Bundle manifests reference missing stack layer {stack_id}."
            )

        record = registry.records[stack_record]
        if record.language and record.language not in registry.language_record_ids:
            raise ConventionValidationError(
                f"Bundle manifests require a language layer for stack {stack_id}."
            )


def build_registry(root: Path | None = None) -> ConventionRegistry:
    """Load and validate a conventions registry from disk."""

    resolved_root = (root or _default_conventions_root()).resolve()
    manifests_dir = resolved_root / "manifests"
    records, sources, stack_record_ids, language_record_ids = _discover_records(resolved_root)
    registry = ConventionRegistry(
        root=resolved_root,
        records=records,
        sources=dict(sorted(sources.items())),
        browse_labels=_read_yaml(manifests_dir / "browse-labels.yaml"),
        bundle_definitions=_read_yaml(manifests_dir / "bundles.yaml"),
        stack_record_ids=stack_record_ids,
        language_record_ids=language_record_ids,
    )
    _validate_references(registry)
    _validate_bundle_manifests(registry)
    return registry
