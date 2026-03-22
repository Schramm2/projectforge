"""Tests for convention bundle compilation."""

from pathlib import Path

import pytest

from ubundiforge.convention_compiler import compile_bundle
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
    _write(root / "stacks" / "broken-base" / "base.md", "# Base\n\nBroken base.")

    _write(
        root / "stacks" / "broken-stack" / "metadata.yaml",
        """
id: broken-stack
label: Broken stack
language: python
inherits:
  - stacks/broken-base
markdown_files:
  - overview.md
""".strip(),
    )
    _write(root / "stacks" / "broken-stack" / "overview.md", "# Broken\n\nBroken stack.")

    _write(
        root / "manifests" / "bundles.yaml",
        """
default:
  label: global
stack_overrides:
  fastapi:
    label: fastapi
  broken-stack:
    label: broken-stack
""".strip(),
    )
    _write(
        root / "manifests" / "browse-labels.yaml",
        """
fastapi: FastAPI
broken-stack: Broken stack
""".strip(),
    )

    return root


def test_compile_bundle_merges_global_language_and_stack_layers(sample_tree: Path) -> None:
    registry = build_registry(sample_tree)

    bundle = compile_bundle(registry, stack="fastapi")

    assert bundle.bundle_id == "fastapi"
    assert "Python" in bundle.prompt_block
    assert any(path.name == "structure.md" for path in bundle.sources)


def test_compile_bundle_rejects_inheritance_cycles(sample_tree: Path) -> None:
    registry = build_registry(sample_tree)

    with pytest.raises(ConventionValidationError):
        compile_bundle(registry, stack="broken-stack")
