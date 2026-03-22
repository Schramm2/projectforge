"""Tests for Homebrew formula generation."""

from pathlib import Path

from ubundiforge import __version__
from ubundiforge.homebrew import render_homebrew_formula, runtime_formula_resources

ROOT = Path(__file__).resolve().parent.parent


def test_runtime_formula_resources_resolve_recursive_runtime_dependencies():
    resources = runtime_formula_resources(ROOT / "uv.lock")
    names = [resource.name for resource in resources]

    assert names == [
        "annotated-doc",
        "click",
        "markdown-it-py",
        "mdurl",
        "prompt-toolkit",
        "pygments",
        "pyyaml",
        "questionary",
        "rich",
        "shellingham",
        "typer",
        "wcwidth",
    ]


def test_render_homebrew_formula_contains_expected_install_surface():
    formula = render_homebrew_formula(
        version=__version__,
        source_url=f"https://example.com/v{__version__}.tar.gz",
        source_sha256="abc123",
        resources=runtime_formula_resources(ROOT / "uv.lock"),
    )

    assert "class Ubundiforge < Formula" in formula
    assert 'depends_on "python@3.13"' in formula
    assert 'conflicts_with "forge"' in formula
    assert 'resource "typer" do' in formula
    assert "#{bin}/forge --dry-run --name brew-smoke" in formula
