"""Orchestrator — filesystem snapshotting and context accumulation (partial, Task 7).

Task 8 will extend this module with plan/execute/reconcile/report logic.
"""

from __future__ import annotations

import os
from pathlib import Path

from ubundiforge.protocol import AgentTask

CONTEXT_CAP = 12_000  # characters

# File extensions whose contents are inlined into context summaries
_CODE_EXTENSIONS = {".py", ".ts", ".json"}
_MAX_INLINE_FILES = 10
_MAX_INLINE_LINES = 200


def snapshot_directory(project_dir: Path) -> dict[str, float]:
    """Snapshot all files under *project_dir* with their modification times.

    Returns a mapping of ``{relative_path_str: mtime}`` for every regular file
    found recursively under the directory.
    """
    result: dict[str, float] = {}
    for root, _dirs, files in os.walk(project_dir):
        for name in files:
            abs_path = Path(root) / name
            rel = abs_path.relative_to(project_dir)
            result[str(rel)] = abs_path.stat().st_mtime
    return result


def diff_snapshots(
    before: dict[str, float],
    after: dict[str, float],
) -> tuple[list[str], list[str]]:
    """Compare two snapshots.

    Returns ``(files_created, files_modified)`` where:
    - *files_created* — keys present in *after* but not *before*.
    - *files_modified* — keys present in both but whose mtime increased.
    """
    files_created: list[str] = []
    files_modified: list[str] = []

    for path, mtime in after.items():
        if path not in before:
            files_created.append(path)
        elif mtime > before[path]:
            files_modified.append(path)

    return files_created, files_modified


def build_context_summary(
    task: AgentTask,
    files_created: list[str],
    files_modified: list[str],
    project_dir: Path,
) -> str:
    """Build a context string for *task* after it ran.

    Includes:
    - Task description
    - Lists of files created and modified
    - Inline content (first ``_MAX_INLINE_LINES`` lines) of up to
      ``_MAX_INLINE_FILES`` ``.py`` / ``.ts`` / ``.json`` files.
    """
    lines: list[str] = []
    lines.append(f"## Task: {task.description}")
    lines.append("")

    if files_created:
        lines.append("Files created:")
        for f in files_created:
            lines.append(f"  {f}")

    if files_modified:
        lines.append("Files modified:")
        for f in files_modified:
            lines.append(f"  {f}")

    # Inline code content for up to _MAX_INLINE_FILES eligible files
    all_changed = files_created + files_modified
    eligible = [f for f in all_changed if Path(f).suffix in _CODE_EXTENSIONS][:_MAX_INLINE_FILES]

    for rel in eligible:
        abs_path = project_dir / rel
        if not abs_path.is_file():
            continue
        try:
            content_lines = abs_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        snippet = "\n".join(content_lines[:_MAX_INLINE_LINES])
        lines.append("")
        lines.append(f"### {rel}")
        lines.append("```")
        lines.append(snippet)
        lines.append("```")

    return "\n".join(lines)


def accumulate_context(existing: str, new_summary: str) -> str:
    """Append *new_summary* to *existing* context.

    When the combined length exceeds ``CONTEXT_CAP``:

    1. Split *existing* into double-newline-separated sections (oldest first).
    2. Compress oldest sections: keep only lines starting with
       ``"Completed:"`` or ``"Files created:"`` or ``"Files modified:"``.
    3. If still over cap, drop oldest sections entirely until under cap.

    The most-recent summary always retains its full content.
    """
    separator = "\n\n"
    if existing.strip():
        combined = existing.rstrip() + separator + new_summary.strip()
    else:
        combined = new_summary.strip()

    if len(combined) <= CONTEXT_CAP:
        return combined

    # Split into sections (oldest first)
    sections = combined.split(separator)

    # --- Pass 1: compress older sections (all except the last) ---
    def _compress(section: str) -> str:
        keep_prefixes = ("Completed:", "Files created:", "Files modified:", "## Task:")
        compressed_lines = [
            line for line in section.splitlines() if any(line.startswith(p) for p in keep_prefixes)
        ]
        return "\n".join(compressed_lines)

    compressed: list[str] = []
    for i, section in enumerate(sections):
        if i < len(sections) - 1:
            compressed.append(_compress(section))
        else:
            compressed.append(section)

    combined = separator.join(s for s in compressed if s.strip())
    if len(combined) <= CONTEXT_CAP:
        return combined

    # --- Pass 2: drop oldest sections until within cap ---
    while len(sections) > 1 and len(combined) > CONTEXT_CAP:
        sections.pop(0)
        compressed.pop(0)
        combined = separator.join(s for s in compressed if s.strip())

    # Hard truncate as a last resort (should rarely trigger)
    return combined[:CONTEXT_CAP]
