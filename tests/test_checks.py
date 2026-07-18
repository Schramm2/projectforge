"""Tests for convention drift detection."""

import json
from pathlib import Path
from unittest.mock import patch

from projectforge.checks import CheckResult, detect_stack, run_checks


def test_detect_stack_python(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    assert detect_stack(tmp_path) == "python"


def test_detect_stack_node(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    assert detect_stack(tmp_path) == "node"


def test_detect_stack_both(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    (tmp_path / "package.json").write_text('{"name": "test"}')
    assert detect_stack(tmp_path) == "both"


def test_detect_stack_unknown(tmp_path: Path):
    assert detect_stack(tmp_path) == "unknown"


def test_detect_stack_from_manifest(tmp_path: Path):
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir()
    (forge_dir / "scaffold.json").write_text(json.dumps({"stack": "fastapi"}))
    assert detect_stack(tmp_path) == "fastapi"


def test_run_checks_empty_dir(tmp_path: Path):
    results = run_checks(tmp_path)
    assert len(results) > 0
    assert all(isinstance(r, CheckResult) for r in results)


def test_run_checks_well_structured_python(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    (tmp_path / "tests").mkdir()
    (tmp_path / "README.md").write_text("# Test\n")
    (tmp_path / ".gitignore").write_text("__pycache__/\n")
    results = run_checks(tmp_path)
    passed = [r for r in results if r.passed]
    assert len(passed) >= 3  # at least pyproject, tests, readme pass


def test_check_result_has_category():
    result = CheckResult(name="README.md", category="structure", passed=True)
    assert result.category == "structure"


def test_empty_project_checks_include_recovery_steps(tmp_path: Path):
    details = {result.name: result.detail for result in run_checks(tmp_path)}

    assert details["README.md"] == (
        "README.md is missing. Add it to meet the project structure convention."
    )
    assert details["tests/"] == (
        "tests/ is missing. Create it if this project should use that convention."
    )
    assert details["CI workflow"] == (
        "No CI workflow was found. Add one under `.github/workflows/` to run project checks "
        "automatically."
    )
    assert details["pre-commit hooks"] == (
        ".pre-commit-config.yaml is missing. Add the repository's pre-commit checks."
    )


def test_fastapi_checks_explain_each_recovery(tmp_path: Path):
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir()
    (forge_dir / "scaffold.json").write_text(json.dumps({"stack": "fastapi"}))
    (tmp_path / "Dockerfile").write_text("FROM python:3.12\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")

    details = {result.name: result.detail for result in run_checks(tmp_path)}

    assert "Add a health route" in details["/health endpoint"]
    assert "add a `USER` instruction" in details["Docker non-root user"]
    assert "Add a `tool.ruff` section" in details["Ruff config"]
    assert "strict = true" in details["MyPy strict"]
    assert "Add one that verifies the app is ready" in details["Docker HEALTHCHECK"]
    assert "forge check --fix" in details[".env.example"]
    assert "forge check --fix" in details["agent_docs/"]


def test_check_hides_unreadable_project_file_detail(tmp_path: Path):
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir()
    (forge_dir / "scaffold.json").write_text(json.dumps({"stack": "fastapi"}))
    (tmp_path / "Dockerfile").write_text("FROM python:3.12\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
    original_read_text = Path.read_text

    def unreadable(path: Path, *args, **kwargs):
        if path.name in {"Dockerfile", "pyproject.toml"}:
            raise OSError("private filesystem detail")
        return original_read_text(path, *args, **kwargs)

    with patch.object(Path, "read_text", unreadable):
        results = run_checks(tmp_path)

    details = [result.detail for result in results]
    assert (
        details.count("Forge could not read Dockerfile. Check that it is readable, then retry.")
        == 2
    )
    assert (
        details.count("Forge could not read pyproject.toml. Check that it is readable, then retry.")
        == 2
    )
    assert all("private filesystem detail" not in detail for detail in details)
