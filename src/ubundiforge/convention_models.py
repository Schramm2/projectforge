"""Shared models for convention discovery and compilation."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


class ConventionValidationError(ValueError):
    """Raised when convention metadata cannot be compiled safely."""


@dataclass(frozen=True)
class ConventionSource:
    """A markdown source file that can contribute to a compiled bundle."""

    source_id: str
    path: Path
    record_id: str | None = None


@dataclass(frozen=True)
class ConventionRecord:
    """Metadata describing a convention layer."""

    record_id: str
    metadata_id: str
    kind: str
    path: Path
    label: str
    browse_label: str | None = None
    language: str | None = None
    inherits: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConventionRegistry:
    """Normalized registry for convention metadata and source files."""

    root: Path
    records: Mapping[str, ConventionRecord]
    sources: Mapping[str, ConventionSource]
    browse_labels: Mapping[str, str]
    bundle_definitions: Mapping[str, object]
    stack_record_ids: Mapping[str, str] = field(default_factory=dict)
    language_record_ids: Mapping[str, str] = field(default_factory=dict)

    def record_ids(self) -> tuple[str, ...]:
        return tuple(self.records)

    def source_ids(self) -> tuple[str, ...]:
        return tuple(self.sources)

    def record(self, record_id: str) -> ConventionRecord:
        try:
            return self.records[record_id]
        except KeyError as exc:
            raise ConventionValidationError(f"Unknown convention record: {record_id}") from exc

    def source(self, source_id: str) -> ConventionSource:
        try:
            return self.sources[source_id]
        except KeyError as exc:
            raise ConventionValidationError(f"Unknown convention source: {source_id}") from exc

    def global_record(self) -> ConventionRecord | None:
        return self.records.get("global")

    def language(self, language_id: str) -> ConventionRecord:
        record_id = self.language_record_ids.get(language_id, f"languages/{language_id}")
        return self.record(record_id)

    def stack(self, stack_id: str) -> ConventionRecord:
        record_id = self.stack_record_ids.get(stack_id, f"stacks/{stack_id}")
        return self.record(record_id)


@dataclass(frozen=True)
class CompiledBundle:
    """A deterministic conventions bundle ready for prompt construction."""

    bundle_id: str
    prompt_block: str
    sources: tuple[Path, ...]
    warnings: tuple[str, ...] = ()
