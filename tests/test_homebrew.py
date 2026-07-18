"""Tests for Homebrew formula generation and release packaging."""

import tomllib
from pathlib import Path

from projectforge import __version__
from projectforge.homebrew import (
    DEFAULT_HOMEPAGE,
    DEFAULT_REPOSITORY,
    DEFAULT_SOURCE_URL,
    DISTRIBUTION_NAME,
    render_homebrew_formula,
    runtime_formula_resources,
    write_homebrew_formula,
)

ROOT = Path(__file__).resolve().parent.parent


def test_homebrew_defaults_use_canonical_public_repository():
    assert DISTRIBUTION_NAME == "matt-projectforge"
    assert DEFAULT_HOMEPAGE == "https://github.com/Schramm2/projectforge"
    assert DEFAULT_REPOSITORY == "https://github.com/Schramm2/projectforge"
    assert DEFAULT_SOURCE_URL == (
        f"https://github.com/Schramm2/projectforge/archive/refs/tags/v{__version__}.tar.gz"
    )


def test_write_homebrew_formula_requires_release_archive_checksum(tmp_path):
    try:
        write_homebrew_formula(
            tmp_path / "projectforge.rb",
            lock_path=ROOT / "uv.lock",
        )
    except TypeError as exc:
        assert "source_sha256" in str(exc)
    else:
        raise AssertionError("release archive checksum must be explicit")


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
    assert all(
        resource.url.startswith(
            f"https://files.pythonhosted.org/packages/source/{resource.name[0]}/{resource.name}/"
        )
        for resource in resources
    )


def test_render_homebrew_formula_contains_expected_install_surface():
    formula = render_homebrew_formula(
        version=__version__,
        source_url=f"https://example.com/v{__version__}.tar.gz",
        source_sha256="abc123",
        resources=runtime_formula_resources(ROOT / "uv.lock"),
    )

    assert "class Projectforge < Formula" in formula
    assert 'depends_on "python@3.13"' in formula
    assert 'conflicts_with "forge"' in formula
    assert 'resource "typer" do' in formula
    assert "#{bin}/projectforge --dry-run --name brew-smoke" in formula
    assert 'shell_output("#{bin}/forge --version")' in formula


def test_package_metadata_installs_collision_free_and_compatibility_commands():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]

    assert project["name"] == "matt-projectforge"
    assert project["scripts"] == {
        "projectforge": "projectforge.__main__:main",
        "forge": "projectforge.__main__:main",
    }


def test_release_workflow_verifies_real_tap_access_before_tagging():
    workflow = (ROOT / ".github/workflows/release-homebrew.yml").read_text()

    preflight = workflow.index("Verify tap publication access")
    create_tag = workflow.index("Create and push release tag")

    assert preflight < create_tag
    assert ".permissions.push" in workflow
    assert "Compare generated formula with Homebrew tap" in workflow
    assert "steps.tap_sync.outputs.already_synced != 'true'" in workflow


def test_release_workflow_publishes_pypi_only_after_homebrew_release_job():
    workflow = (ROOT / ".github/workflows/release-homebrew.yml").read_text()

    assert "publish-pypi:" in workflow
    assert "needs: release" in workflow
    assert "if: needs.release.outputs.publish_release == 'true'" in workflow
    assert "id-token: write" in workflow
    assert "https://pypi.org/p/matt-projectforge" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
