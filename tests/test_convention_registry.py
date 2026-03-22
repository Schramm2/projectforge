"""Tests for convention registry discovery and validation."""

from pathlib import Path

import pytest

from ubundiforge.convention_models import ConventionValidationError
from ubundiforge.convention_registry import build_registry


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    root = tmp_path / "conventions"

    _write(
        root / "global" / "metadata.yaml",
        """
id: global
label: Global
browse_label: Global conventions
markdown_files:
  - shared.md
""".strip(),
    )
    _write(root / "global" / "shared.md", "# Shared\n\nGlobal defaults.")

    _write(
        root / "languages" / "python" / "metadata.yaml",
        """
id: python
label: Python
browse_label: Python conventions
markdown_files:
  - style.md
""".strip(),
    )
    _write(root / "languages" / "python" / "style.md", "# Python\n\nPython guidance.")

    _write(
        root / "stacks" / "python-api" / "metadata.yaml",
        """
id: python-api
label: Python API base
language: python
markdown_files:
  - services.md
""".strip(),
    )
    _write(
        root / "stacks" / "python-api" / "services.md",
        "# Services\n\nKeep handlers thin.",
    )

    _write(
        root / "stacks" / "fastapi" / "metadata.yaml",
        """
id: fastapi
label: FastAPI
language: python
browse_label: FastAPI bundle
inherits:
  - stacks/python-api
markdown_files:
  - overview.md
  - structure.md
""".strip(),
    )
    _write(root / "stacks" / "fastapi" / "overview.md", "# FastAPI\n\nUse async endpoints.")
    _write(
        root / "stacks" / "fastapi" / "structure.md",
        "# Structure\n\nKeep API modules separate from services.",
    )

    _write(
        root / "manifests" / "bundles.yaml",
        """
default:
  label: global
  files:
    - global/shared.md
stack_overrides:
  fastapi:
    label: fastapi
    files:
      - languages/python/style.md
      - stacks/python-api/services.md
      - stacks/fastapi/overview.md
      - stacks/fastapi/structure.md
""".strip(),
    )
    _write(
        root / "manifests" / "browse-labels.yaml",
        """
fastapi: FastAPI
""".strip(),
    )

    return root


def test_build_registry_discovers_normalized_records_and_sources(sample_tree: Path) -> None:
    registry = build_registry(sample_tree)

    assert registry.root == sample_tree
    assert registry.record_ids() == (
        "global",
        "languages/python",
        "stacks/fastapi",
        "stacks/python-api",
    )
    assert registry.source_ids() == (
        "global/shared",
        "languages/python/style",
        "stacks/fastapi/overview",
        "stacks/fastapi/structure",
        "stacks/python-api/services",
    )

    fastapi = registry.stack("fastapi")
    assert fastapi.language == "python"
    assert fastapi.inherits == ("stacks/python-api",)
    assert registry.source("stacks/fastapi/structure").path.name == "structure.md"


def test_build_registry_rejects_missing_markdown_file(tmp_path: Path) -> None:
    root = tmp_path / "conventions"
    _write(
        root / "global" / "metadata.yaml",
        """
id: global
label: Global
markdown_files:
  - missing.md
""".strip(),
    )

    with pytest.raises(ConventionValidationError, match="missing.md"):
        build_registry(root)


def test_build_registry_rejects_broken_inheritance_id(tmp_path: Path) -> None:
    root = tmp_path / "conventions"
    _write(
        root / "global" / "metadata.yaml",
        """
id: global
label: Global
markdown_files:
  - shared.md
""".strip(),
    )
    _write(root / "global" / "shared.md", "# Shared")
    _write(
        root / "stacks" / "fastapi" / "metadata.yaml",
        """
id: fastapi
label: FastAPI
inherits:
  - stacks/missing
markdown_files:
  - overview.md
""".strip(),
    )
    _write(root / "stacks" / "fastapi" / "overview.md", "# FastAPI")

    with pytest.raises(ConventionValidationError, match="stacks/missing"):
        build_registry(root)


def test_build_registry_rejects_inheritance_cycles(tmp_path: Path) -> None:
    root = tmp_path / "conventions"
    _write(
        root / "global" / "metadata.yaml",
        """
id: global
label: Global
markdown_files:
  - shared.md
""".strip(),
    )
    _write(root / "global" / "shared.md", "# Shared")
    _write(
        root / "stacks" / "broken-base" / "metadata.yaml",
        """
id: broken-base
label: Broken base
inherits:
  - stacks/broken-stack
markdown_files:
  - base.md
""".strip(),
    )
    _write(root / "stacks" / "broken-base" / "base.md", "# Base")
    _write(
        root / "stacks" / "broken-stack" / "metadata.yaml",
        """
id: broken-stack
label: Broken stack
inherits:
  - stacks/broken-base
markdown_files:
  - overview.md
""".strip(),
    )
    _write(root / "stacks" / "broken-stack" / "overview.md", "# Broken")

    with pytest.raises(ConventionValidationError, match="cycle"):
        build_registry(root)


def test_build_registry_rejects_duplicate_markdown_file_entries_within_record(
    tmp_path: Path,
) -> None:
    root = tmp_path / "conventions"
    _write(
        root / "global" / "metadata.yaml",
        """
id: global
label: Global
markdown_files:
  - shared.md
  - shared.md
""".strip(),
    )
    _write(root / "global" / "shared.md", "# Shared")

    with pytest.raises(ConventionValidationError, match="shared.md"):
        build_registry(root)


def test_build_registry_rejects_duplicate_stack_ids(tmp_path: Path) -> None:
    root = tmp_path / "conventions"
    _write(
        root / "global" / "metadata.yaml",
        """
id: global
label: Global
markdown_files:
  - shared.md
""".strip(),
    )
    _write(root / "global" / "shared.md", "# Shared")
    _write(
        root / "stacks" / "fastapi-one" / "metadata.yaml",
        """
id: fastapi
label: FastAPI One
markdown_files:
  - overview.md
""".strip(),
    )
    _write(root / "stacks" / "fastapi-one" / "overview.md", "# One")
    _write(
        root / "stacks" / "fastapi-two" / "metadata.yaml",
        """
id: fastapi
label: FastAPI Two
markdown_files:
  - overview.md
""".strip(),
    )
    _write(root / "stacks" / "fastapi-two" / "overview.md", "# Two")

    with pytest.raises(ConventionValidationError, match="Duplicate stack id"):
        build_registry(root)


def test_build_registry_rejects_duplicate_language_ids(tmp_path: Path) -> None:
    root = tmp_path / "conventions"
    _write(
        root / "global" / "metadata.yaml",
        """
id: global
label: Global
markdown_files:
  - shared.md
""".strip(),
    )
    _write(root / "global" / "shared.md", "# Shared")
    _write(
        root / "languages" / "python-one" / "metadata.yaml",
        """
id: python
label: Python One
markdown_files:
  - style.md
""".strip(),
    )
    _write(root / "languages" / "python-one" / "style.md", "# One")
    _write(
        root / "languages" / "python-two" / "metadata.yaml",
        """
id: python
label: Python Two
markdown_files:
  - style.md
""".strip(),
    )
    _write(root / "languages" / "python-two" / "style.md", "# Two")

    with pytest.raises(ConventionValidationError, match="Duplicate language id"):
        build_registry(root)


def test_build_registry_rejects_manifest_missing_default_source(sample_tree: Path) -> None:
    _write(
        sample_tree / "manifests" / "bundles.yaml",
        """
default:
  label: global
  files: []
stack_overrides:
  fastapi:
    label: fastapi
    files:
      - languages/python/style.md
      - stacks/python-api/services.md
      - stacks/fastapi/overview.md
      - stacks/fastapi/structure.md
""".strip(),
    )

    with pytest.raises(ConventionValidationError, match="global/shared.md"):
        build_registry(sample_tree)


def test_build_registry_rejects_manifest_missing_inherited_stack_source(
    sample_tree: Path,
) -> None:
    _write(
        sample_tree / "manifests" / "bundles.yaml",
        """
default:
  label: global
  files:
    - global/shared.md
stack_overrides:
  fastapi:
    label: fastapi
    files:
      - languages/python/style.md
      - stacks/fastapi/overview.md
      - stacks/fastapi/structure.md
""".strip(),
    )

    with pytest.raises(ConventionValidationError, match="stacks/python-api/services.md"):
        build_registry(sample_tree)


def test_build_registry_rejects_manifest_missing_language_source(
    sample_tree: Path,
) -> None:
    _write(
        sample_tree / "manifests" / "bundles.yaml",
        """
default:
  label: global
  files:
    - global/shared.md
stack_overrides:
  fastapi:
    label: fastapi
    files:
      - stacks/python-api/services.md
      - stacks/fastapi/overview.md
      - stacks/fastapi/structure.md
""".strip(),
    )

    with pytest.raises(ConventionValidationError, match="languages/python/style.md"):
        build_registry(sample_tree)


def test_build_registry_smoke_checks_real_bundled_tree() -> None:
    root = Path(__file__).resolve().parents[1] / "conventions"

    registry = build_registry(root)

    assert registry.root == root.resolve()
    assert registry.stack("fastapi").language == "python"
    assert "global/shared" in registry.source_ids()
