"""Safe lifecycle helpers for user-owned convention profiles."""

from __future__ import annotations

import re
from pathlib import Path

from projectforge.convention_models import ConventionValidationError
from projectforge.conventions import PROFILES_DIR
from projectforge.safety import check_for_secrets

_PROFILE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
_MAX_IMPORT_BYTES = 1_000_000
_PROFILE_TEMPLATE = """# Convention Profile

Add durable preferences for projects using this profile. Keep credentials,
customer data, and machine-specific paths out of convention files.
"""


def profile_path(name: str) -> Path:
    """Resolve a validated profile name beneath the user profile directory."""
    if not _PROFILE_NAME_RE.fullmatch(name):
        raise ConventionValidationError(f"Invalid conventions profile: {name}")
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
            f"Conventions profile already exists: {destination.stem}"
        ) from exc
    return destination


def initialize_profile(name: str = "default") -> Path:
    """Create a non-destructive starter profile."""
    return _write_new_profile(profile_path(name), _PROFILE_TEMPLATE)


def import_profile(source: Path, name: str) -> Path:
    """Import a bounded Markdown instruction file as a new profile."""
    if source.suffix.lower() != ".md" or not source.is_file():
        raise ConventionValidationError("Convention imports must be existing Markdown files.")
    try:
        size = source.stat().st_size
        content = source.read_text()
    except OSError as exc:
        raise ConventionValidationError(f"Could not read convention source: {source}") from exc
    if size > _MAX_IMPORT_BYTES:
        raise ConventionValidationError("Convention import exceeds the 1 MB safety limit.")
    secret_types = check_for_secrets(content)
    if secret_types:
        labels = ", ".join(secret_types)
        raise ConventionValidationError(
            f"Convention import contains credential-like content: {labels}."
        )
    return _write_new_profile(profile_path(name), content)
