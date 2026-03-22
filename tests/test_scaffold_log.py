"""Tests for scaffold logging and manifest generation."""

import json

from ubundiforge.scaffold_log import append_scaffold_log, write_scaffold_manifest


def test_append_scaffold_log_creates_file(tmp_path, monkeypatch):
    log_path = tmp_path / "scaffold.log"
    monkeypatch.setattr("ubundiforge.scaffold_log.SCAFFOLD_LOG_PATH", log_path)
    monkeypatch.setattr("ubundiforge.scaffold_log.FORGE_DIR", tmp_path)

    answers = {"name": "demo", "stack": "nextjs", "demo_mode": True}
    phase_backends = [("architecture", "claude"), ("tests", "codex")]

    append_scaffold_log(answers, phase_backends, tmp_path / "demo")

    assert log_path.exists()
    entry = json.loads(log_path.read_text().strip())
    assert entry["name"] == "demo"
    assert entry["stack"] == "nextjs"
    assert set(entry["backends"]) == {"claude", "codex"}
    assert entry["demo_mode"] is True
    assert "timestamp" in entry


def test_append_scaffold_log_appends(tmp_path, monkeypatch):
    log_path = tmp_path / "scaffold.log"
    monkeypatch.setattr("ubundiforge.scaffold_log.SCAFFOLD_LOG_PATH", log_path)
    monkeypatch.setattr("ubundiforge.scaffold_log.FORGE_DIR", tmp_path)

    for name in ("alpha", "beta"):
        answers = {"name": name, "stack": "fastapi"}
        append_scaffold_log(answers, [("architecture", "claude")], tmp_path / name)

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["name"] == "alpha"
    assert json.loads(lines[1])["name"] == "beta"


def test_write_scaffold_manifest(tmp_path):
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()

    answers = {
        "name": "my-project",
        "stack": "fastapi",
        "description": "A test project",
        "design_template": "ubundi-dark",
        "media_collection": "brand-a",
        "auth_provider": None,
        "demo_mode": False,
    }
    phase_backends = [("architecture", "claude"), ("tests", "claude")]

    write_scaffold_manifest(
        answers,
        phase_backends,
        project_dir,
        "conventions content here",
        model_override="opus",
        backend_models={"claude": "opus"},
    )

    manifest_path = project_dir / ".forge" / "scaffold.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["name"] == "my-project"
    assert manifest["stack"] == "fastapi"
    assert manifest["backends"] == ["claude"]
    assert manifest["model_override"] == "opus"
    assert manifest["design_template"] == "ubundi-dark"
    assert manifest["conventions_hash"].startswith("sha256:")
    assert "forge_version" in manifest
    assert "timestamp" in manifest
    assert len(manifest["routing"]) == 2


def test_write_scaffold_manifest_creates_forge_dir(tmp_path):
    project_dir = tmp_path / "new-project"
    project_dir.mkdir()

    write_scaffold_manifest(
        {"name": "new-project", "stack": "nextjs"},
        [("architecture", "gemini")],
        project_dir,
        "conventions",
    )

    assert (project_dir / ".forge" / "scaffold.json").exists()


def test_write_scaffold_manifest_saves_conventions_snapshot(tmp_path):
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    conventions = "# My Conventions\n\nUse strict typing.\n"
    write_scaffold_manifest(
        {"name": "test-project", "stack": "fastapi"},
        [("architecture", "claude")],
        project_dir,
        conventions,
    )

    snapshot = project_dir / ".forge" / "conventions-snapshot.md"
    assert snapshot.exists()
    assert snapshot.read_text() == conventions
