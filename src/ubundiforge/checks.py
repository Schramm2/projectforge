"""Convention drift detection — deterministic project audit against Ubundi standards."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    """Result of a single convention check."""

    name: str
    category: str
    passed: bool
    severity: str = "fail"  # pass, warn, fail
    detail: str = ""
    fixable: bool = False


def detect_stack(project_dir: Path) -> str:
    """Detect the project stack from manifest or config files."""
    manifest = project_dir / ".forge" / "scaffold.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text())
            if stack := data.get("stack"):
                return stack
        except (json.JSONDecodeError, OSError):
            pass

    has_python = (project_dir / "pyproject.toml").exists()
    has_node = (project_dir / "package.json").exists()

    if has_python and has_node:
        return "both"
    if has_python:
        return "python"
    if has_node:
        return "node"
    return "unknown"


# --- Check definitions ---


def _check_file_exists(project_dir: Path, filename: str, category: str, **kwargs) -> CheckResult:
    """Check that a file exists."""
    exists = (project_dir / filename).exists()
    return CheckResult(
        name=filename,
        category=category,
        passed=exists,
        severity="fail" if not exists else "pass",
        detail="" if exists else f"Missing {filename}",
        fixable=kwargs.get("fixable", False),
    )


def _check_dir_exists(project_dir: Path, dirname: str, category: str, **kwargs) -> CheckResult:
    """Check that a directory exists."""
    exists = (project_dir / dirname).is_dir()
    return CheckResult(
        name=dirname + "/",
        category=category,
        passed=exists,
        severity="warn" if not exists else "pass",
        detail="" if exists else f"Missing {dirname}/ directory",
        fixable=kwargs.get("fixable", False),
    )


def _check_ci_present(project_dir: Path) -> CheckResult:
    """Check for GitHub Actions CI."""
    ci_dir = project_dir / ".github" / "workflows"
    has_ci = ci_dir.is_dir() and any(ci_dir.glob("*.yml"))
    return CheckResult(
        name="CI workflow",
        category="tooling",
        passed=has_ci,
        severity="warn" if not has_ci else "pass",
        detail="" if has_ci else "No .github/workflows/*.yml found",
    )


def _check_pre_commit(project_dir: Path) -> CheckResult:
    """Check for pre-commit config."""
    exists = (project_dir / ".pre-commit-config.yaml").exists()
    return CheckResult(
        name="pre-commit hooks",
        category="tooling",
        passed=exists,
        severity="warn" if not exists else "pass",
        detail="" if exists else "Missing .pre-commit-config.yaml",
    )


def _check_health_endpoint(project_dir: Path) -> CheckResult:
    """Check for a health endpoint in Python API projects."""
    for pattern in ("**/health*.py", "**/routes/health*"):
        if list(project_dir.glob(pattern)):
            return CheckResult(
                name="/health endpoint",
                category="runtime",
                passed=True,
            )
    return CheckResult(
        name="/health endpoint",
        category="runtime",
        passed=False,
        severity="warn",
        detail="No health endpoint file found",
    )


def _check_docker_nonroot(project_dir: Path) -> CheckResult:
    """Check Dockerfile uses non-root user."""
    dockerfile = project_dir / "Dockerfile"
    if not dockerfile.exists():
        return CheckResult(
            name="Docker non-root user",
            category="runtime",
            passed=True,
            detail="No Dockerfile (skipped)",
        )
    content = dockerfile.read_text()
    has_user = "adduser" in content.lower() or "user " in content.lower()
    return CheckResult(
        name="Docker non-root user",
        category="runtime",
        passed=has_user,
        severity="warn" if not has_user else "pass",
        detail="" if has_user else "Dockerfile should create and switch to a non-root user",
    )


def _check_ruff_config(project_dir: Path) -> CheckResult:
    """Check for Ruff configuration in pyproject.toml."""
    toml = project_dir / "pyproject.toml"
    if not toml.exists():
        return CheckResult(
            name="Ruff config",
            category="tooling",
            passed=False,
            severity="warn",
            detail="No pyproject.toml",
        )
    content = toml.read_text()
    has_ruff = "[tool.ruff" in content
    return CheckResult(
        name="Ruff config",
        category="tooling",
        passed=has_ruff,
        severity="warn" if not has_ruff else "pass",
        detail="" if has_ruff else "No [tool.ruff] section in pyproject.toml",
    )


def _check_mypy_strict(project_dir: Path) -> CheckResult:
    """Check for MyPy strict mode configuration."""
    toml = project_dir / "pyproject.toml"
    if not toml.exists():
        return CheckResult(
            name="MyPy strict",
            category="tooling",
            passed=False,
            severity="warn",
            detail="No pyproject.toml",
        )
    content = toml.read_text()
    has_mypy = "[tool.mypy]" in content or "--strict" in content
    return CheckResult(
        name="MyPy strict",
        category="tooling",
        passed=has_mypy,
        severity="warn" if not has_mypy else "pass",
        detail="" if has_mypy else "No MyPy strict mode configured",
    )


def _check_docker_healthcheck(project_dir: Path) -> CheckResult:
    """Check Dockerfile has a HEALTHCHECK directive."""
    dockerfile = project_dir / "Dockerfile"
    if not dockerfile.exists():
        return CheckResult(
            name="Docker HEALTHCHECK",
            category="runtime",
            passed=True,
            detail="No Dockerfile (skipped)",
        )
    content = dockerfile.read_text()
    has_healthcheck = "HEALTHCHECK" in content
    return CheckResult(
        name="Docker HEALTHCHECK",
        category="runtime",
        passed=has_healthcheck,
        severity="warn" if not has_healthcheck else "pass",
        detail="" if has_healthcheck else "Dockerfile missing HEALTHCHECK directive",
    )


def run_checks(project_dir: Path) -> list[CheckResult]:
    """Run all convention checks against a project directory."""
    stack = detect_stack(project_dir)
    results: list[CheckResult] = []

    # Structure checks (universal)
    results.append(_check_file_exists(project_dir, "README.md", "structure"))
    results.append(_check_file_exists(project_dir, ".gitignore", "structure"))
    results.append(_check_dir_exists(project_dir, "tests", "structure"))

    # Python-specific structure
    if stack in ("python", "fastapi", "fastapi-ai", "python-cli", "python-worker", "both"):
        results.append(_check_file_exists(project_dir, "pyproject.toml", "structure"))
        results.append(_check_file_exists(project_dir, ".env.example", "structure", fixable=True))
        results.append(_check_file_exists(project_dir, "CLAUDE.md", "structure", fixable=True))
        results.append(_check_dir_exists(project_dir, "agent_docs", "structure", fixable=True))

    # Node-specific structure
    if stack in ("node", "nextjs", "ts-package", "both"):
        results.append(_check_file_exists(project_dir, "package.json", "structure"))
        results.append(_check_file_exists(project_dir, "tsconfig.json", "structure"))

    # Tooling checks
    results.append(_check_ci_present(project_dir))
    results.append(_check_pre_commit(project_dir))

    if stack in ("python", "fastapi", "fastapi-ai", "python-cli", "python-worker", "both"):
        results.append(_check_ruff_config(project_dir))
        results.append(_check_mypy_strict(project_dir))

    # Runtime checks (API stacks only)
    if stack in ("fastapi", "fastapi-ai", "both"):
        results.append(_check_health_endpoint(project_dir))
        results.append(_check_docker_nonroot(project_dir))
        results.append(_check_docker_healthcheck(project_dir))

    return results


def generate_fix(project_dir: Path, check: CheckResult) -> bool:
    """Generate a fix for a fixable check. Returns True if fixed."""
    if not check.fixable or check.passed:
        return False

    name = check.name.rstrip("/")

    if name == "CLAUDE.md":
        (project_dir / "CLAUDE.md").write_text(
            f"# {project_dir.name}\n\n## Project structure\n\nTODO: Document project structure.\n"
        )
        return True

    if name == ".env.example":
        (project_dir / ".env.example").write_text(
            "# Environment variables\n# Copy to .env and fill in values\nENV=development\n"
        )
        return True

    if name == "agent_docs":
        agent_dir = project_dir / "agent_docs"
        agent_dir.mkdir(exist_ok=True)
        (agent_dir / "architecture.md").write_text(
            f"# {project_dir.name} — Architecture\n\nTODO: Document architecture.\n"
        )
        return True

    return False
