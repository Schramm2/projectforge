"""Tests for convention loading and validation."""

import pytest

from projectforge.convention_models import CompiledBundle, ConventionValidationError
from projectforge.conventions import (
    MIN_CONVENTIONS_LENGTH,
    load_bundled_conventions,
    load_conventions,
    load_conventions_bundle,
    resolve_bundled_conventions_dir,
    resolve_forge_dir,
)


def test_resolve_forge_dir_honors_environment_override(tmp_path, monkeypatch):
    forge_home = tmp_path / "isolated-forge-home"
    monkeypatch.setenv("FORGE_HOME", str(forge_home))

    assert resolve_forge_dir() == forge_home


def test_resolve_bundled_conventions_dir_prefers_package_dir(tmp_path):
    package_dir = tmp_path / "package" / "conventions"
    repo_dir = tmp_path / "repo" / "conventions"
    package_dir.mkdir(parents=True)
    repo_dir.mkdir(parents=True)

    assert resolve_bundled_conventions_dir(package_dir, repo_dir) == package_dir


def test_resolve_bundled_conventions_dir_falls_back_to_repo_dir(tmp_path):
    package_dir = tmp_path / "package" / "conventions"
    repo_dir = tmp_path / "repo" / "conventions"
    repo_dir.mkdir(parents=True)

    assert resolve_bundled_conventions_dir(package_dir, repo_dir) == repo_dir


def test_empty_conventions_warns(tmp_path, monkeypatch):
    conv_path = tmp_path / "conventions.md"
    conv_path.write_text("")
    monkeypatch.setattr("projectforge.conventions.CONVENTIONS_PATH", conv_path)
    monkeypatch.setattr("projectforge.conventions.FORGE_DIR", tmp_path)
    monkeypatch.setattr(
        "projectforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / ".forge" / "conventions.md",
    )

    content, warnings = load_conventions()
    assert content == ""
    assert any("empty" in w.lower() for w in warnings)


def test_short_conventions_warns(tmp_path, monkeypatch):
    conv_path = tmp_path / "conventions.md"
    conv_path.write_text("short")
    monkeypatch.setattr("projectforge.conventions.CONVENTIONS_PATH", conv_path)
    monkeypatch.setattr("projectforge.conventions.FORGE_DIR", tmp_path)
    monkeypatch.setattr(
        "projectforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / ".forge" / "conventions.md",
    )

    content, warnings = load_conventions()
    assert len(content.strip()) < MIN_CONVENTIONS_LENGTH
    assert any("short" in w.lower() for w in warnings)


def test_valid_conventions_no_warnings(tmp_path, monkeypatch):
    conv_path = tmp_path / "conventions.md"
    conv_path.write_text("x" * 100)
    monkeypatch.setattr("projectforge.conventions.CONVENTIONS_PATH", conv_path)
    monkeypatch.setattr("projectforge.conventions.FORGE_DIR", tmp_path)
    monkeypatch.setattr(
        "projectforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / ".forge" / "conventions.md",
    )

    content, warnings = load_conventions()
    assert len(content) == 100
    assert warnings == []


def test_missing_conventions_creates_default(tmp_path, monkeypatch):
    conv_path = tmp_path / "conventions.md"
    monkeypatch.setattr("projectforge.conventions.CONVENTIONS_PATH", conv_path)
    monkeypatch.setattr("projectforge.conventions.FORGE_DIR", tmp_path)
    monkeypatch.setattr(
        "projectforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / ".forge" / "conventions.md",
    )

    assert not conv_path.exists()
    content, warnings = load_conventions()
    assert conv_path.exists()
    assert "Default" in content
    assert any("created" in w.lower() for w in warnings)


def test_load_conventions_prefers_bundled_tree(tmp_path, monkeypatch):
    root = tmp_path / "conventions"
    (root / "global").mkdir(parents=True)
    (root / "global" / "shared.md").write_text("Use strict typing.")
    monkeypatch.setattr("projectforge.conventions.BUNDLED_CONVENTIONS_DIR", root)
    monkeypatch.setattr(
        "projectforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / ".forge" / "conventions.md",
    )

    content, warnings = load_conventions(stack="fastapi")

    assert "strict typing" in content
    assert warnings
    assert any("short" in w.lower() for w in warnings)


def test_load_conventions_stack_composes_bundle_before_local_override(tmp_path, monkeypatch):
    root = tmp_path / "conventions"
    (root / "global").mkdir(parents=True)
    (root / "global" / "shared.md").write_text("Use strict typing in bundled content.")
    local = tmp_path / ".forge" / "conventions.md"
    local.parent.mkdir(parents=True)
    local.write_text("Local rules always win, even when we mention TODO items in prose.")

    monkeypatch.setattr("projectforge.conventions.BUNDLED_CONVENTIONS_DIR", root)
    monkeypatch.setattr("projectforge.conventions.LOCAL_CONVENTIONS_PATH", local)

    content, warnings = load_conventions(stack="fastapi")

    assert content.index("bundled content") < content.index("Local rules always win")
    assert warnings[0] == f"Using local conventions from {local}"
    assert any("local conventions" in w.lower() for w in warnings)


def test_stack_bundle_composes_profile_user_and_project_layers_with_hashes(
    tmp_path, monkeypatch
):
    root = tmp_path / "bundled"
    (root / "global").mkdir(parents=True)
    (root / "global" / "shared.md").write_text("Bundled defaults apply first.")
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "default.md").write_text("Selected profile applies second.")
    user_path = tmp_path / "user-wide.md"
    user_path.write_text("User-wide rules apply third.")
    local_path = tmp_path / "project" / ".forge" / "conventions.md"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("Project-local rules apply last.")

    monkeypatch.setattr("projectforge.conventions.BUNDLED_CONVENTIONS_DIR", root)
    monkeypatch.setattr("projectforge.conventions.PROFILES_DIR", profiles_dir)
    monkeypatch.setattr("projectforge.conventions.CONVENTIONS_PATH", user_path)
    monkeypatch.setattr("projectforge.conventions.LOCAL_CONVENTIONS_PATH", local_path)

    bundle = load_conventions_bundle(stack="fastapi", profile="default")

    assert bundle.prompt_block.index("Bundled defaults") < bundle.prompt_block.index(
        "Selected profile"
    )
    assert bundle.prompt_block.index("Selected profile") < bundle.prompt_block.index("User-wide")
    assert bundle.prompt_block.index("User-wide") < bundle.prompt_block.index("Project-local")
    assert [item.source_id for item in bundle.contributions][-3:] == [
        "profile:default",
        "user-wide",
        "project-local",
    ]
    assert all(item.sha256.startswith("sha256:") for item in bundle.contributions)


def test_stack_bundle_rejects_credential_shaped_user_content(tmp_path, monkeypatch):
    root = tmp_path / "bundled"
    (root / "global").mkdir(parents=True)
    (root / "global" / "shared.md").write_text("Safe bundled defaults for every project.")
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "default.md").write_text(
        "Never print ghp_abcdefghijklmnopqrstuvwxyz1234567890"
    )
    monkeypatch.setattr("projectforge.conventions.BUNDLED_CONVENTIONS_DIR", root)
    monkeypatch.setattr("projectforge.conventions.PROFILES_DIR", profiles_dir)
    monkeypatch.setattr("projectforge.conventions.CONVENTIONS_PATH", tmp_path / "missing.md")
    monkeypatch.setattr(
        "projectforge.conventions.LOCAL_CONVENTIONS_PATH", tmp_path / "missing-local.md"
    )

    with pytest.raises(ConventionValidationError, match="credential-like"):
        load_conventions_bundle(stack="fastapi")


def test_load_conventions_stack_ignores_placeholder_local_override(tmp_path, monkeypatch):
    root = tmp_path / "conventions"
    (root / "global").mkdir(parents=True)
    (root / "global" / "shared.md").write_text("Use strict typing in bundled content.")
    local = tmp_path / ".forge" / "conventions.md"
    local.parent.mkdir(parents=True)
    local.write_text("TODO: add conventions")

    monkeypatch.setattr("projectforge.conventions.BUNDLED_CONVENTIONS_DIR", root)
    monkeypatch.setattr("projectforge.conventions.LOCAL_CONVENTIONS_PATH", local)

    content, warnings = load_conventions(stack="fastapi")

    assert "bundled content" in content
    assert any("ignoring placeholder conventions" in warning.lower() for warning in warnings)
    assert any("placeholder" in w.lower() for w in warnings)


def test_load_bundled_conventions_skips_legacy_local_and_user_files(tmp_path, monkeypatch):
    local = tmp_path / ".forge" / "conventions.md"
    local.parent.mkdir(parents=True)
    local.write_text("Local rules should not be used here.")
    user_path = tmp_path / "user-conventions.md"

    monkeypatch.setattr("projectforge.conventions.LOCAL_CONVENTIONS_PATH", local)
    monkeypatch.setattr("projectforge.conventions.CONVENTIONS_PATH", user_path)
    monkeypatch.setattr("projectforge.conventions.FORGE_DIR", tmp_path / "forge-home")
    monkeypatch.setattr(
        "projectforge.conventions.build_registry",
        lambda root=None: "registry",
    )
    monkeypatch.setattr(
        "projectforge.conventions.compile_bundle",
        lambda registry, stack=None: CompiledBundle(
            bundle_id=stack or "default",
            prompt_block=f"Compiled bundle for {stack}",
            sources=(),
            warnings=("bundle warning",),
        ),
    )

    content, warnings = load_bundled_conventions("fastapi")

    assert content == "Compiled bundle for fastapi"
    assert warnings == ["bundle warning"]
    assert not user_path.exists()


def test_load_conventions_stack_keeps_bundle_warnings_when_bundle_is_empty(tmp_path, monkeypatch):
    user_path = tmp_path / "user-conventions.md"

    monkeypatch.setattr("projectforge.conventions.CONVENTIONS_PATH", user_path)
    monkeypatch.setattr("projectforge.conventions.FORGE_DIR", tmp_path / "forge-home")
    monkeypatch.setattr(
        "projectforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / ".forge" / "conventions.md",
    )
    monkeypatch.setattr(
        "projectforge.conventions.load_conventions_bundle",
        lambda stack=None, profile="default": CompiledBundle(
            bundle_id=stack or "default",
            prompt_block="",
            sources=(),
            warnings=("bundle warning",),
        ),
    )

    content, warnings = load_conventions(stack="fastapi")

    assert content == ""
    assert warnings == ["bundle warning"]
    assert not user_path.exists()
