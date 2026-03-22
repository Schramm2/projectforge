"""Loads bundled convention bundles plus narrow legacy compatibility fallbacks."""

import re
from pathlib import Path

from .convention_compiler import compile_bundle as _compile_bundle
from .convention_models import CompiledBundle
from .convention_registry import build_registry as _build_registry

_PLACEHOLDER_LOCAL_EXACT_LINES = {
    "todo",
    "tbd",
    "placeholder",
    "your conventions here",
    "add conventions",
    "replace me",
    "coming soon",
}

_PLACEHOLDER_TODO_LINE_RE = re.compile(
    r"^todo(?:\s*[:\-–—]\s*(?:add|write|fill in|replace|define|document|fix)\b.*)?$"
)


def resolve_bundled_conventions_dir(
    package_conventions_dir: Path | None = None,
    repo_conventions_dir: Path | None = None,
) -> Path:
    """Return the bundled conventions directory for package or repo execution."""

    package_dir = package_conventions_dir or Path(__file__).resolve().with_name("conventions")
    repo_dir = repo_conventions_dir or Path(__file__).resolve().parents[2] / "conventions"
    return package_dir if package_dir.exists() else repo_dir


BUNDLED_CONVENTIONS_DIR = resolve_bundled_conventions_dir()

FORGE_DIR = Path.home() / ".forge"
CONVENTIONS_PATH = FORGE_DIR / "conventions.md"
CLAUDE_MD_TEMPLATE_PATH = Path(__file__).parent / "templates" / "claude-md-template.md"

MIN_CONVENTIONS_LENGTH = 50

LOCAL_CONVENTIONS_PATH = Path.cwd() / ".forge" / "conventions.md"

_LEGACY_DEFAULT_CONVENTION_PARTS = [
    "global/shared.md",
    "global/frontend-brand.md",
    "global/frontend-communication.md",
    "global/typescript-standards.md",
    "global/python-standards.md",
    "global/python-architecture.md",
    "global/project-files.md",
    "global/git.md",
]


def _read_text(path: Path) -> str:
    if path.exists():
        return path.read_text()
    return ""


def _compose_text(root: Path, relative_paths: list[str]) -> str:
    parts = [
        _read_text(root / relative_paths_item).strip() for relative_paths_item in relative_paths
    ]
    content = "\n\n".join(part for part in parts if part)
    if content:
        return content
    return "# Ubundi Project Conventions\n\nFollow the bundled conventions."


LEGACY_DEFAULT_CONVENTIONS = _compose_text(
    BUNDLED_CONVENTIONS_DIR,
    _LEGACY_DEFAULT_CONVENTION_PARTS,
)
# Backward-compatible alias for legacy callers and tests that still reference the old name.
DEFAULT_CONVENTIONS = LEGACY_DEFAULT_CONVENTIONS


def build_registry(root: Path | None = None):
    """Build the conventions registry for the bundled or provided tree."""

    return _build_registry(root or BUNDLED_CONVENTIONS_DIR)


def compile_bundle(registry, stack: str | None = None) -> CompiledBundle:
    """Compile a prompt block from the registry and optional stack id."""

    return _compile_bundle(registry, stack=stack)


def load_bundled_conventions(stack: str | None = None) -> tuple[str, list[str]]:
    """Load compiled bundled conventions without consulting legacy local/user files."""

    bundle = compile_bundle(build_registry(), stack=stack)
    return bundle.prompt_block, list(bundle.warnings)


def _load_conventions_file(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    content = path.read_text()

    if not content.strip():
        warnings.append("Conventions file is empty — scaffolds will lack guidance.")
    elif len(content.strip()) < MIN_CONVENTIONS_LENGTH:
        warnings.append("Conventions file is very short — consider adding more detail.")

    return content, warnings


def _looks_placeholder_local_conventions(content: str) -> bool:
    lines = [line.lstrip("#>*- ").strip().lower() for line in content.splitlines() if line.strip()]
    if not lines:
        return True

    for line in lines:
        if line in _PLACEHOLDER_LOCAL_EXACT_LINES:
            continue
        if _PLACEHOLDER_TODO_LINE_RE.match(line):
            continue
        return False

    return True


def _load_local_conventions(path: Path) -> tuple[str, list[str]]:
    content, warnings = _load_conventions_file(path)
    warnings.insert(0, f"Using local conventions from {path}")
    return content, warnings


def load_conventions(stack: str | None = None) -> tuple[str, list[str]]:
    """Load bundled conventions first and use legacy files only as a compatibility fallback."""

    if LOCAL_CONVENTIONS_PATH.exists():
        local_content = LOCAL_CONVENTIONS_PATH.read_text()
        if stack is None or not _looks_placeholder_local_conventions(local_content):
            return _load_local_conventions(LOCAL_CONVENTIONS_PATH)

    if stack is not None:
        bundle_text, bundle_warnings = load_bundled_conventions(stack)
        warnings = list(bundle_warnings)
        if LOCAL_CONVENTIONS_PATH.exists():
            warnings.insert(
                0,
                (
                    "Ignoring placeholder local conventions from "
                    f"{LOCAL_CONVENTIONS_PATH}; using bundled stack conventions."
                ),
            )
        return bundle_text, warnings

    warnings: list[str] = []

    source = CONVENTIONS_PATH
    if not source.exists():
        FORGE_DIR.mkdir(parents=True, exist_ok=True)
        source.write_text(LEGACY_DEFAULT_CONVENTIONS)
        warnings.append("Created legacy compatibility conventions at ~/.forge/conventions.md")

    content, source_warnings = _load_conventions_file(source)
    warnings.extend(source_warnings)

    return content, warnings


def load_claude_md_template() -> str | None:
    """Load the CLAUDE.md template from ~/.forge/claude-md-template.md.

    Returns None if the file doesn't exist — the prompt builder will
    fall back to its generic instruction.
    """

    if CLAUDE_MD_TEMPLATE_PATH.exists():
        return CLAUDE_MD_TEMPLATE_PATH.read_text()
    return None
