"""Tests for convention bundle compilation."""

from pathlib import Path

import pytest

from ubundiforge.convention_compiler import compile_bundle
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


def test_compile_bundle_merges_layers_in_deterministic_order(sample_tree: Path) -> None:
    registry = build_registry(sample_tree)

    bundle = compile_bundle(registry, stack="fastapi")
    expected_sources = (
        sample_tree / "global" / "shared.md",
        sample_tree / "languages" / "python" / "style.md",
        sample_tree / "stacks" / "python-api" / "services.md",
        sample_tree / "stacks" / "fastapi" / "overview.md",
        sample_tree / "stacks" / "fastapi" / "structure.md",
    )
    expected_prompt_block = "\n\n".join(path.read_text().strip() for path in expected_sources)

    assert bundle.bundle_id == "fastapi"
    assert bundle.sources == expected_sources
    assert bundle.prompt_block == expected_prompt_block


def test_compile_bundle_dedupes_cross_layer_overlaps_deterministically(
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
""".strip(),
    )
    _write(root / "global" / "shared.md", "# Shared\n\nGlobal defaults.")

    _write(
        root / "languages" / "python" / "metadata.yaml",
        """
id: python
label: Python
markdown_files:
  - ../../global/shared.md
  - style.md
""".strip(),
    )
    _write(root / "languages" / "python" / "style.md", "# Python\n\nLanguage guidance.")

    _write(
        root / "stacks" / "fastapi" / "metadata.yaml",
        """
id: fastapi
label: FastAPI
language: python
markdown_files:
  - overview.md
""".strip(),
    )
    _write(root / "stacks" / "fastapi" / "overview.md", "# FastAPI\n\nStack guidance.")

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
      - stacks/fastapi/overview.md
""".strip(),
    )

    registry = build_registry(root)
    bundle = compile_bundle(registry, stack="fastapi")

    assert bundle.sources == (
        root / "global" / "shared.md",
        root / "languages" / "python" / "style.md",
        root / "stacks" / "fastapi" / "overview.md",
    )
    assert bundle.prompt_block.count("# Shared") == 1
