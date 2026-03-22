"""Tests for convention loading and validation."""

from ubundiforge.convention_models import CompiledBundle
from ubundiforge.conventions import (
    MIN_CONVENTIONS_LENGTH,
    load_bundled_conventions,
    load_conventions,
    resolve_bundled_conventions_dir,
)


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
    monkeypatch.setattr("ubundiforge.conventions.CONVENTIONS_PATH", conv_path)
    monkeypatch.setattr("ubundiforge.conventions.FORGE_DIR", tmp_path)
    monkeypatch.setattr(
        "ubundiforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / ".forge" / "conventions.md",
    )

    content, warnings = load_conventions()
    assert content == ""
    assert any("empty" in w.lower() for w in warnings)


def test_short_conventions_warns(tmp_path, monkeypatch):
    conv_path = tmp_path / "conventions.md"
    conv_path.write_text("short")
    monkeypatch.setattr("ubundiforge.conventions.CONVENTIONS_PATH", conv_path)
    monkeypatch.setattr("ubundiforge.conventions.FORGE_DIR", tmp_path)
    monkeypatch.setattr(
        "ubundiforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / ".forge" / "conventions.md",
    )

    content, warnings = load_conventions()
    assert len(content.strip()) < MIN_CONVENTIONS_LENGTH
    assert any("short" in w.lower() for w in warnings)


def test_valid_conventions_no_warnings(tmp_path, monkeypatch):
    conv_path = tmp_path / "conventions.md"
    conv_path.write_text("x" * 100)
    monkeypatch.setattr("ubundiforge.conventions.CONVENTIONS_PATH", conv_path)
    monkeypatch.setattr("ubundiforge.conventions.FORGE_DIR", tmp_path)
    monkeypatch.setattr(
        "ubundiforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / ".forge" / "conventions.md",
    )

    content, warnings = load_conventions()
    assert len(content) == 100
    assert warnings == []


def test_missing_conventions_creates_default(tmp_path, monkeypatch):
    conv_path = tmp_path / "conventions.md"
    monkeypatch.setattr("ubundiforge.conventions.CONVENTIONS_PATH", conv_path)
    monkeypatch.setattr("ubundiforge.conventions.FORGE_DIR", tmp_path)
    monkeypatch.setattr(
        "ubundiforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / ".forge" / "conventions.md",
    )

    assert not conv_path.exists()
    content, warnings = load_conventions()
    assert conv_path.exists()
    assert "Ubundi" in content
    assert any("created" in w.lower() for w in warnings)


def test_load_conventions_prefers_bundled_tree(tmp_path, monkeypatch):
    root = tmp_path / "conventions"
    (root / "global").mkdir(parents=True)
    (root / "global" / "shared.md").write_text("Use strict typing.")
    monkeypatch.setattr("ubundiforge.conventions.BUNDLED_CONVENTIONS_DIR", root)
    monkeypatch.setattr(
        "ubundiforge.conventions.LOCAL_CONVENTIONS_PATH",
        tmp_path / ".forge" / "conventions.md",
    )

    content, warnings = load_conventions(stack="fastapi")

    assert "strict typing" in content
    assert warnings
    assert any("short" in w.lower() for w in warnings)


def test_load_conventions_stack_prefers_local_override(tmp_path, monkeypatch):
    root = tmp_path / "conventions"
    (root / "global").mkdir(parents=True)
    (root / "global" / "shared.md").write_text("Use strict typing in bundled content.")
    local = tmp_path / ".forge" / "conventions.md"
    local.parent.mkdir(parents=True)
    local.write_text("Local rules always win, even when we mention TODO items in prose.")

    monkeypatch.setattr("ubundiforge.conventions.BUNDLED_CONVENTIONS_DIR", root)
    monkeypatch.setattr("ubundiforge.conventions.LOCAL_CONVENTIONS_PATH", local)

    content, warnings = load_conventions(stack="fastapi")

    assert content == "Local rules always win, even when we mention TODO items in prose."
    assert warnings[0] == f"Using local conventions from {local}"
    assert any("local conventions" in w.lower() for w in warnings)


def test_load_conventions_stack_ignores_placeholder_local_override(tmp_path, monkeypatch):
    root = tmp_path / "conventions"
    (root / "global").mkdir(parents=True)
    (root / "global" / "shared.md").write_text("Use strict typing in bundled content.")
    local = tmp_path / ".forge" / "conventions.md"
    local.parent.mkdir(parents=True)
    local.write_text("TODO: add conventions")

    monkeypatch.setattr("ubundiforge.conventions.BUNDLED_CONVENTIONS_DIR", root)
    monkeypatch.setattr("ubundiforge.conventions.LOCAL_CONVENTIONS_PATH", local)

    content, warnings = load_conventions(stack="fastapi")

    assert "bundled content" in content
    assert (
        warnings[0]
        == f"Ignoring placeholder local conventions from {local}; using bundled stack conventions."
    )
    assert any("placeholder" in w.lower() for w in warnings)


def test_load_bundled_conventions_skips_legacy_local_and_user_files(tmp_path, monkeypatch):
    local = tmp_path / ".forge" / "conventions.md"
    local.parent.mkdir(parents=True)
    local.write_text("Local rules should not be used here.")
    user_path = tmp_path / "user-conventions.md"

    monkeypatch.setattr("ubundiforge.conventions.LOCAL_CONVENTIONS_PATH", local)
    monkeypatch.setattr("ubundiforge.conventions.CONVENTIONS_PATH", user_path)
    monkeypatch.setattr("ubundiforge.conventions.FORGE_DIR", tmp_path / "forge-home")
    monkeypatch.setattr(
        "ubundiforge.conventions.build_registry",
        lambda root=None: "registry",
    )
    monkeypatch.setattr(
        "ubundiforge.conventions.compile_bundle",
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
