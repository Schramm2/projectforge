"""Safe lifecycle helpers for user-owned convention profiles."""

from __future__ import annotations

import re
from pathlib import Path

from projectforge.convention_models import ConventionValidationError
from projectforge.conventions import PROFILES_DIR
from projectforge.safety import check_for_secrets

_PROFILE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
_MAX_IMPORT_BYTES = 1_000_000
_INSTRUCTION_FILE_CANDIDATES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
)
_GUIDED_SECTIONS = (
    ("toolchain", "Toolchain"),
    ("testing", "Testing and verification"),
    ("architecture", "Architecture and organization"),
    ("code_style", "Code style and typing"),
    ("git_docs", "Git and documentation"),
    ("guardrails", "Rules Forge should respect"),
)
_PROFILE_TEMPLATE = """# Convention Profile

Record preferences that should apply across projects using this profile. Leave a section blank
when Forge's bundled defaults are sufficient. Keep credentials, customer data, and machine-specific
paths out of this file.

## Toolchain

## Testing and verification

## Architecture and organization

## Code style and typing

## Git and documentation

## Rules Forge should respect
"""


def profile_path(name: str) -> Path:
    """Resolve a validated profile name beneath the user profile directory."""
    if not _PROFILE_NAME_RE.fullmatch(name):
        raise ConventionValidationError(
            "That convention profile name is not valid. Start with a letter or number and use "
            "only letters, numbers, dots, hyphens, or underscores."
        )
    return PROFILES_DIR / f"{name}.md"


def list_profiles() -> tuple[str, ...]:
    """List available profile names in deterministic order."""
    if not PROFILES_DIR.exists():
        return ()
    return tuple(sorted(path.stem for path in PROFILES_DIR.glob("*.md") if path.is_file()))


def _write_new_profile(destination: Path, content: str) -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("x") as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise ConventionValidationError(
            "That convention profile already exists. Choose a new name, or edit the existing "
            "profile."
        ) from exc
    return destination


def initialize_profile(name: str = "default") -> Path:
    """Create a non-destructive starter profile."""
    return _write_new_profile(profile_path(name), _PROFILE_TEMPLATE)


def discover_instruction_files(root: Path | None = None) -> tuple[Path, ...]:
    """Return known instruction files at the selected directory without recursive scanning."""
    base = (root or Path.cwd()).resolve()
    return tuple(
        candidate
        for relative_path in _INSTRUCTION_FILE_CANDIDATES
        if (candidate := base / relative_path).is_file()
    )


def _read_import_source(source: Path) -> str:
    """Read and validate one bounded Markdown instruction source."""
    if source.suffix.lower() != ".md" or not source.is_file():
        raise ConventionValidationError("Choose an existing `.md` file, then run the import again.")
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise ConventionValidationError(
            "Forge could not read that Markdown file. Check that it exists and is readable, "
            "then retry."
        ) from exc
    if size > _MAX_IMPORT_BYTES:
        raise ConventionValidationError(
            "That Markdown file is larger than 1 MB. Split or shorten it, then import the "
            "smaller file."
        )
    try:
        content = source.read_text()
    except (OSError, UnicodeError) as exc:
        raise ConventionValidationError(
            "Forge could not read that Markdown file. Check that it exists and is readable, "
            "then retry."
        ) from exc
    if check_for_secrets(content):
        raise ConventionValidationError(
            "Forge found content that looks like a credential. Remove secrets and use "
            "placeholders, then retry."
        )
    return content


def save_profile_content(name: str, content: str) -> Path:
    """Persist previewed, validated convention profile content without re-reading sources."""
    if len(content.encode()) > _MAX_IMPORT_BYTES:
        raise ConventionValidationError(
            "That convention profile is larger than 1 MB. Shorten it, then retry."
        )
    if check_for_secrets(content):
        raise ConventionValidationError(
            "Forge found content that looks like a credential. Remove secrets and use "
            "placeholders, then retry."
        )
    return _write_new_profile(profile_path(name), content)


def import_profile(source: Path, name: str) -> Path:
    """Import a bounded Markdown instruction file as a new profile."""
    return save_profile_content(name, _read_import_source(source))


def build_import_profile_content(sources: list[Path]) -> str:
    """Validate selected instruction files and render their combined profile content."""
    if not sources:
        raise ConventionValidationError("Select at least one instruction file to import.")

    sections: list[str] = ["# Imported Convention Profile"]
    total_size = 0
    for source in sources:
        content = _read_import_source(source)
        total_size += len(content.encode())
        if total_size > _MAX_IMPORT_BYTES:
            raise ConventionValidationError(
                "The selected instruction files are larger than 1 MB together. Select fewer "
                "files or shorten them, then retry."
            )
        sections.append(f"## Source: {source.name}\n\n{content.strip()}")
    return "\n\n".join(sections).strip() + "\n"


def import_profile_sources(sources: list[Path], name: str) -> Path:
    """Combine explicitly selected instruction files into a new convention profile."""
    return save_profile_content(name, build_import_profile_content(sources))


def build_guided_profile_content(answers: dict[str, str]) -> str:
    """Validate interview answers and render a convention profile for preview."""
    sections = ["# Convention Profile"]
    for key, heading in _GUIDED_SECTIONS:
        value = answers.get(key, "").strip()
        if not value:
            continue
        if check_for_secrets(value):
            raise ConventionValidationError(
                "Forge found content that looks like a credential. Remove secrets and use "
                "placeholders, then retry."
            )
        sections.append(f"## {heading}\n\n{value}")

    if len(sections) == 1:
        raise ConventionValidationError(
            "Add at least one durable preference, or use Forge defaults for now."
        )
    return "\n\n".join(sections) + "\n"


def create_guided_profile(name: str, answers: dict[str, str]) -> Path:
    """Create a profile from the convention preferences supplied in the setup interview."""
    return save_profile_content(name, build_guided_profile_content(answers))
