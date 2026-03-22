"""Tests for convention admin and history helpers."""

from pathlib import Path
from subprocess import CompletedProcess

import pytest
from rich.console import Console

from ubundiforge.convention_registry import build_registry


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _render_to_string(renderable) -> str:
    console = Console(record=True, width=120)
    console.print(renderable)
    return console.export_text()


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
    _write(root / "stacks" / "python-api" / "services.md", "# Services\n\nKeep handlers thin.")

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
global: Global conventions
fastapi: FastAPI
""".strip(),
    )

    return root


def test_list_scopes_covers_global_language_stack_and_prompt(sample_tree: Path) -> None:
    from ubundiforge.convention_admin import list_scopes

    registry = build_registry(sample_tree)

    scopes = list_scopes(registry)

    assert tuple(scope.name for scope in scopes) == ("global", "language", "stack", "prompt")
    assert tuple(item.key for item in scopes[1].items) == ("python",)
    assert tuple(item.key for item in scopes[2].items) == ("fastapi", "python-api")
    assert tuple(item.key for item in scopes[3].items) == ("default", "fastapi")


def test_render_inheritance_trace_shows_compilation_order(sample_tree: Path) -> None:
    from ubundiforge.convention_admin import render_inheritance_trace

    registry = build_registry(sample_tree)

    output = _render_to_string(render_inheritance_trace(registry, "fastapi"))

    assert "global" in output
    assert "languages/python" in output
    assert "stacks/python-api" in output
    assert "stacks/fastapi" in output


def test_render_compiled_bundle_preview_lists_bundle_sources(sample_tree: Path) -> None:
    from ubundiforge.convention_admin import render_bundle_preview

    registry = build_registry(sample_tree)

    output = _render_to_string(render_bundle_preview(registry, "fastapi"))

    assert "Compiled bundle: fastapi" in output
    assert "global/shared.md" in output
    assert "stacks/fastapi/structure.md" in output
    assert "Use async endpoints." in output


def test_resolve_markdown_open_path_only_allows_convention_markdown(sample_tree: Path) -> None:
    from ubundiforge.convention_admin import resolve_open_path
    from ubundiforge.convention_models import ConventionValidationError

    resolved = resolve_open_path(sample_tree, "languages/python/style.md")

    assert resolved == sample_tree / "languages" / "python" / "style.md"

    with pytest.raises(ConventionValidationError, match="markdown"):
        resolve_open_path(sample_tree, "languages/python/metadata.yaml")

    with pytest.raises(ConventionValidationError, match="outside"):
        resolve_open_path(sample_tree, "../README.md")


def test_load_history_gracefully_handles_missing_git(monkeypatch, sample_tree: Path) -> None:
    from ubundiforge.convention_history import load_history

    def _missing_git(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("ubundiforge.convention_history.subprocess.run", _missing_git)

    history = load_history(sample_tree, "stacks/fastapi")

    assert history.available is False
    assert history.entries == ()
    assert "git" in history.message.lower()


def test_load_history_reads_non_interactive_git_log(monkeypatch, sample_tree: Path) -> None:
    from ubundiforge.convention_history import load_history

    seen_commands: list[list[str]] = []

    def _fake_run(command, **kwargs):
        seen_commands.append(command)
        return CompletedProcess(
            command,
            0,
            stdout="abc123 Add FastAPI overview\n",
            stderr="",
        )

    monkeypatch.setattr("ubundiforge.convention_history.subprocess.run", _fake_run)

    history = load_history(sample_tree, "stacks/fastapi")

    assert history.available is True
    assert history.entries == ("abc123 Add FastAPI overview",)
    assert seen_commands == [["git", "log", "--oneline", "--", "conventions/stacks/fastapi"]]
