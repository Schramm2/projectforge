"""Loads convention sources from the bundled tree and legacy ~/.forge/ files."""

from dataclasses import dataclass
from pathlib import Path

import yaml

_PLACEHOLDER_LOCAL_MARKERS = (
    "todo",
    "tbd",
    "placeholder",
    "your conventions here",
    "add conventions",
    "replace me",
    "coming soon",
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

_DEFAULT_CONVENTIONS_PARTS = [
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
        _read_text(root / relative_paths_item).strip()
        for relative_paths_item in relative_paths
    ]
    content = "\n\n".join(part for part in parts if part)
    if content:
        return content
    return "# Ubundi Project Conventions\n\nFollow the bundled conventions."


DEFAULT_CONVENTIONS = _compose_text(BUNDLED_CONVENTIONS_DIR, _DEFAULT_CONVENTIONS_PARTS)


@dataclass(frozen=True)
class CompiledBundle:
    """A compiled conventions bundle."""

    prompt_block: str
    warnings: list[str]


def _read_yaml(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text())
    if isinstance(data, dict):
        return data
    return {}


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped


def _discover_markdown_files(root: Path) -> list[Path]:
    files = [path for path in root.rglob("*.md") if "manifests" not in path.parts]
    return sorted(files)


def _bundle_files_from_manifest(
    root: Path,
    registry: dict[str, object],
    stack: str | None,
) -> list[Path]:
    bundle_definitions = registry.get("bundle_definitions")
    if not isinstance(bundle_definitions, dict):
        return []

    selected: list[str] = []

    default_bundle = bundle_definitions.get("default")
    if isinstance(default_bundle, dict):
        files = default_bundle.get("files")
        if isinstance(files, list):
            selected.extend(str(item) for item in files)

    if stack:
        stack_overrides = bundle_definitions.get("stack_overrides")
        if isinstance(stack_overrides, dict):
            override = stack_overrides.get(stack)
            if isinstance(override, dict):
                files = override.get("files")
                if isinstance(files, list):
                    selected.extend(str(item) for item in files)

    return [root / rel_path for rel_path in selected]


def build_registry(root: Path | None = None) -> dict[str, object]:
    """Build a lightweight registry of the bundled conventions tree."""

    resolved_root = root or BUNDLED_CONVENTIONS_DIR
    manifests_dir = resolved_root / "manifests"

    metadata: dict[str, dict[str, object]] = {}
    for metadata_path in sorted(resolved_root.rglob("metadata.yaml")):
        if "manifests" in metadata_path.parts:
            continue
        relative_dir = metadata_path.parent.relative_to(resolved_root).as_posix()
        metadata[relative_dir] = _read_yaml(metadata_path)

    return {
        "root": resolved_root,
        "bundle_definitions": _read_yaml(manifests_dir / "bundles.yaml"),
        "browse_labels": _read_yaml(manifests_dir / "browse-labels.yaml"),
        "metadata": metadata,
    }


def compile_bundle(registry: dict[str, object], stack: str | None = None) -> CompiledBundle:
    """Compile a prompt block from the registry and optional stack id."""

    root = registry["root"]
    if not isinstance(root, Path):
        root = BUNDLED_CONVENTIONS_DIR

    bundle_files = _bundle_files_from_manifest(root, registry, stack)
    if not bundle_files:
        bundle_files = _discover_markdown_files(root)

    bundle_files = _dedupe_paths([path for path in bundle_files if path.exists()])
    content_parts = [path.read_text().strip() for path in bundle_files if path.read_text().strip()]
    prompt_block = "\n\n".join(content_parts).strip()

    warnings: list[str] = []
    if not prompt_block:
        warnings.append("Conventions bundle is empty.")
    elif len(prompt_block) < MIN_CONVENTIONS_LENGTH:
        warnings.append("Conventions bundle is very short — consider adding more detail.")

    return CompiledBundle(prompt_block=prompt_block, warnings=warnings)


def _load_conventions_file(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    content = path.read_text()

    if not content.strip():
        warnings.append("Conventions file is empty — scaffolds will lack guidance.")
    elif len(content.strip()) < MIN_CONVENTIONS_LENGTH:
        warnings.append("Conventions file is very short — consider adding more detail.")

    return content, warnings


def _looks_placeholder_local_conventions(content: str) -> bool:
    stripped = content.strip().lower()
    if not stripped:
        return True
    return any(marker in stripped for marker in _PLACEHOLDER_LOCAL_MARKERS)


def _load_local_conventions(path: Path) -> tuple[str, list[str]]:
    content, warnings = _load_conventions_file(path)
    warnings.insert(0, f"Using local conventions from {path}")
    return content, warnings


def load_conventions(stack: str | None = None) -> tuple[str, list[str]]:
    """Load conventions, preferring the bundled tree for stack-aware requests."""

    if LOCAL_CONVENTIONS_PATH.exists():
        local_content = LOCAL_CONVENTIONS_PATH.read_text()
        if stack is None or not _looks_placeholder_local_conventions(local_content):
            return _load_local_conventions(LOCAL_CONVENTIONS_PATH)

    if stack is not None:
        bundle = compile_bundle(build_registry(), stack=stack)
        if bundle.prompt_block:
            warnings = list(bundle.warnings)
            if LOCAL_CONVENTIONS_PATH.exists():
                warnings.insert(
                    0,
                    (
                        "Ignoring placeholder local conventions from "
                        f"{LOCAL_CONVENTIONS_PATH}; using bundled stack conventions."
                    ),
                )
            return bundle.prompt_block, warnings

    warnings: list[str] = []

    source = CONVENTIONS_PATH
    if not source.exists():
        FORGE_DIR.mkdir(parents=True, exist_ok=True)
        source.write_text(DEFAULT_CONVENTIONS)
        warnings.append("Created default conventions at ~/.forge/conventions.md")

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
