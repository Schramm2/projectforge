"""Tests for convention drift detection."""

import json
from pathlib import Path

from ubundiforge.checks import CheckResult, detect_stack, run_checks


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
