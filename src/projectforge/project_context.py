"""Consent-based project brief and nearby context handling."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from projectforge.safety import check_for_secrets

_CONTEXT_FILE_CANDIDATES = (
    "PROJECT.md",
    "PRODUCT.md",
    "PRD.md",
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
)
_MAX_CONTEXT_FILE_BYTES = 32_000
_MAX_CONTEXT_TOTAL_BYTES = 64_000
_BRIEF_FIELDS = (
    ("audience", "Intended users"),
    ("first_success", "First useful outcome"),
    ("constraints", "Constraints"),
    ("existing_systems", "Existing systems"),
    ("non_goals", "Non-goals"),
)


@dataclass(frozen=True)
class ContextSource:
    """One user-selected context file prepared for prompt assembly."""

    path: str
    content: str
    sha256: str


@dataclass(frozen=True)
class ContextLoadResult:
    """Loaded context sources and reader-facing warnings for skipped files."""

    sources: tuple[ContextSource, ...]
    warnings: tuple[str, ...]


def discover_context_files(root: Path | None = None) -> tuple[Path, ...]:
    """Find known context files near the invocation directory without recursive scanning."""
    base = (root or Path.cwd()).resolve()
    return tuple(
        candidate
        for relative_path in _CONTEXT_FILE_CANDIDATES
        if (candidate := base / relative_path).is_file()
    )


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def load_context_sources(
    selected: list[Path] | tuple[Path, ...],
    *,
    root: Path | None = None,
) -> ContextLoadResult:
    """Load only explicitly selected local Markdown files within bounded limits."""
    base = (root or Path.cwd()).resolve()
    sources: list[ContextSource] = []
    warnings: list[str] = []
    total_bytes = 0

    for candidate in selected:
        resolved = candidate.resolve()
        label = _display_path(resolved, base)
        try:
            resolved.relative_to(base)
        except ValueError:
            warnings.append(f"Skipped {label} because it is outside the folder Forge inspected.")
            continue

        if resolved.suffix.lower() != ".md" or not resolved.is_file():
            warnings.append(f"Skipped {label} because it is not a readable Markdown file.")
            continue

        try:
            size = resolved.stat().st_size
        except OSError:
            warnings.append(f"Skipped {label} because Forge could not read it as Markdown.")
            continue
        if size > _MAX_CONTEXT_FILE_BYTES:
            warnings.append(
                f"Skipped {label} because it is larger than the 32 KB per-file context limit."
            )
            continue
        if total_bytes + size > _MAX_CONTEXT_TOTAL_BYTES:
            warnings.append(
                f"Skipped {label} because the selected files exceed the 64 KB context limit."
            )
            continue

        try:
            raw = resolved.read_bytes()
            content = raw.decode("utf-8")
        except (OSError, UnicodeError):
            warnings.append(f"Skipped {label} because Forge could not read it as Markdown.")
            continue

        # Recheck after reading in case the file changed between stat and read.
        if len(raw) > _MAX_CONTEXT_FILE_BYTES:
            warnings.append(
                f"Skipped {label} because it is larger than the 32 KB per-file context limit."
            )
            continue
        if total_bytes + len(raw) > _MAX_CONTEXT_TOTAL_BYTES:
            warnings.append(
                f"Skipped {label} because the selected files exceed the 64 KB context limit."
            )
            continue
        if check_for_secrets(content):
            warnings.append(
                f"Skipped {label} because it appears to contain a credential. Remove credentials "
                "or choose another file."
            )
            continue

        total_bytes += len(raw)
        sources.append(
            ContextSource(
                path=label,
                content=content,
                sha256=f"sha256:{hashlib.sha256(raw).hexdigest()}",
            )
        )

    return ContextLoadResult(sources=tuple(sources), warnings=tuple(warnings))


def _source_value(source: ContextSource | dict, key: str) -> str:
    if isinstance(source, ContextSource):
        return str(getattr(source, key))
    return str(source.get(key, ""))


def extract_project_context_block(snapshot: str) -> str:
    """Extract the exact provider block from a reader-labeled local context snapshot."""
    start = snapshot.find("<project_context>")
    if start < 0:
        return ""
    closing = "</project_context>"
    end = snapshot.rfind(closing, start)
    if end < 0:
        return ""
    return snapshot[start : end + len(closing)].strip()


def build_project_context_block(answers: dict) -> str:
    """Render the user-approved project brief and file context for provider prompts."""
    saved_snapshot = answers.get("project_context_snapshot")
    if isinstance(saved_snapshot, str) and saved_snapshot.strip():
        return saved_snapshot.strip()

    brief = answers.get("project_brief") or {}
    if not isinstance(brief, dict):
        brief = {}
    brief_lines = [
        f"{label}: {value.strip()}"
        for key, label in _BRIEF_FIELDS
        if isinstance((value := brief.get(key, "")), str) and value.strip()
    ]
    sources = answers.get("context_sources") or ()
    if not isinstance(sources, (list, tuple)):
        sources = ()
    if not brief_lines and not sources:
        return ""

    lines = [
        "<project_context>",
        "This context was supplied or explicitly selected by the user. Use it to make project-",
        "specific decisions while preserving higher-priority task and convention instructions.",
    ]
    if brief_lines:
        lines.extend(["", "<project_brief>", *brief_lines, "</project_brief>"])
    for source in sources:
        path = _source_value(source, "path")
        content = _source_value(source, "content").strip()
        if not path or not content:
            continue
        lines.extend(
            [
                "",
                f'<selected_file path="{path}">',
                f"Selected file: {path}",
                content,
                "</selected_file>",
            ]
        )
    lines.append("</project_context>")
    return "\n".join(lines)
