"""Helpers for generating a Homebrew formula from Forge metadata."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from ubundiforge import __version__

FORMULA_NAME = "ubundiforge"
DEFAULT_HOMEPAGE = "https://github.com/matthewubundi/UbundiForge"
DEFAULT_REPOSITORY = "https://github.com/matthewubundi/UbundiForge"
DEFAULT_SOURCE_URL = f"{DEFAULT_REPOSITORY}/archive/refs/tags/v{__version__}.tar.gz"
DEFAULT_SOURCE_SHA256 = "REPLACE_WITH_RELEASE_TARBALL_SHA256"
DEFAULT_PYTHON_FORMULA = "python@3.13"
PROJECT_DESCRIPTION = "Scaffold Ubundi-style projects with AI coding tools and shared conventions"


@dataclass(frozen=True)
class FormulaResource:
    """A Python package resource included in the Homebrew formula."""

    name: str
    url: str
    sha256: str


def _package_index(lock_data: dict) -> dict[str, dict]:
    """Index packages from uv.lock by normalized name."""
    return {package["name"]: package for package in lock_data["package"]}


def _runtime_dependency_names(lock_data: dict) -> list[str]:
    """Return Forge's direct runtime dependencies from uv.lock metadata."""
    packages = _package_index(lock_data)
    project = packages[FORMULA_NAME]
    requires_dist = project["metadata"]["requires-dist"]
    return sorted({requirement["name"] for requirement in requires_dist})


def _include_dependency(dependency: dict) -> bool:
    """Return whether a dependency should be included for Homebrew runtime installs."""
    marker = dependency.get("marker", "")
    if "win32" in marker.lower() or "windows" in marker.lower():
        return False
    return True


def runtime_formula_resources(lock_path: Path) -> list[FormulaResource]:
    """Resolve all recursive runtime resources needed by the Homebrew formula."""
    lock_data = tomllib.loads(lock_path.read_text())
    packages = _package_index(lock_data)

    pending = list(_runtime_dependency_names(lock_data))
    seen: set[str] = set()
    resources: list[FormulaResource] = []

    while pending:
        name = pending.pop(0)
        if name in seen:
            continue
        seen.add(name)

        package = packages[name]
        sdist = package.get("sdist")
        if sdist is None:
            raise ValueError(f"Package {name!r} has no sdist entry in {lock_path}.")

        resources.append(
            FormulaResource(
                name=name,
                url=sdist["url"],
                sha256=sdist["hash"].removeprefix("sha256:"),
            )
        )

        for dependency in package.get("dependencies", []):
            if not _include_dependency(dependency):
                continue
            dependency_name = dependency["name"]
            if dependency_name not in seen:
                pending.append(dependency_name)

    return sorted(resources, key=lambda resource: resource.name)


def render_homebrew_formula(
    *,
    version: str,
    source_url: str,
    source_sha256: str,
    resources: list[FormulaResource],
    homepage: str = DEFAULT_HOMEPAGE,
    python_formula: str = DEFAULT_PYTHON_FORMULA,
) -> str:
    """Render a Homebrew formula for Forge."""
    resource_blocks = "\n\n".join(
        (
            f'  resource "{resource.name}" do\n'
            f'    url "{resource.url}"\n'
            f'    sha256 "{resource.sha256}"\n'
            "  end"
        )
        for resource in resources
    )

    return f'''class Ubundiforge < Formula
  include Language::Python::Virtualenv

  desc "{PROJECT_DESCRIPTION}"
  homepage "{homepage}"
  url "{source_url}"
  sha256 "{source_sha256}"
  license "MIT"
  head "{DEFAULT_REPOSITORY}.git", branch: "main"

  depends_on "{python_formula}"

  conflicts_with "forge", because: "both install a forge executable"

{resource_blocks}

  def install
    virtualenv_install_with_resources
  end

  test do
    command = "#{{bin}}/forge --dry-run --name brew-smoke --stack fastapi " \\
              "--description 'Homebrew smoke test' --no-docker --no-open --no-verify"
    output = shell_output(command)
    assert_match "Homebrew smoke test", output
    assert_match "Routing Plan", output
  end
end
'''


def write_homebrew_formula(
    output_path: Path,
    *,
    lock_path: Path,
    version: str = __version__,
    source_url: str = DEFAULT_SOURCE_URL,
    source_sha256: str = DEFAULT_SOURCE_SHA256,
    homepage: str = DEFAULT_HOMEPAGE,
    python_formula: str = DEFAULT_PYTHON_FORMULA,
) -> Path:
    """Generate and write the Homebrew formula to disk."""
    formula = render_homebrew_formula(
        version=version,
        source_url=source_url,
        source_sha256=source_sha256,
        resources=runtime_formula_resources(lock_path),
        homepage=homepage,
        python_formula=python_formula,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(formula)
    return output_path
