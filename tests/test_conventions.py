"""Tests for convention loading and validation."""

from ubundiforge.conventions import MIN_CONVENTIONS_LENGTH, load_conventions


def test_empty_conventions_warns(tmp_path, monkeypatch):
    conv_path = tmp_path / "conventions.md"
    conv_path.write_text("")
    monkeypatch.setattr("ubundiforge.conventions.CONVENTIONS_PATH", conv_path)
    monkeypatch.setattr("ubundiforge.conventions.FORGE_DIR", tmp_path)

    content, warnings = load_conventions()
    assert content == ""
    assert any("empty" in w.lower() for w in warnings)


def test_short_conventions_warns(tmp_path, monkeypatch):
    conv_path = tmp_path / "conventions.md"
    conv_path.write_text("short")
    monkeypatch.setattr("ubundiforge.conventions.CONVENTIONS_PATH", conv_path)
    monkeypatch.setattr("ubundiforge.conventions.FORGE_DIR", tmp_path)

    content, warnings = load_conventions()
    assert len(content.strip()) < MIN_CONVENTIONS_LENGTH
    assert any("short" in w.lower() for w in warnings)


def test_valid_conventions_no_warnings(tmp_path, monkeypatch):
    conv_path = tmp_path / "conventions.md"
    conv_path.write_text("x" * 100)
    monkeypatch.setattr("ubundiforge.conventions.CONVENTIONS_PATH", conv_path)
    monkeypatch.setattr("ubundiforge.conventions.FORGE_DIR", tmp_path)

    content, warnings = load_conventions()
    assert len(content) == 100
    assert warnings == []


def test_missing_conventions_creates_default(tmp_path, monkeypatch):
    conv_path = tmp_path / "conventions.md"
    monkeypatch.setattr("ubundiforge.conventions.CONVENTIONS_PATH", conv_path)
    monkeypatch.setattr("ubundiforge.conventions.FORGE_DIR", tmp_path)

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

    content, warnings = load_conventions(stack="fastapi")

    assert "strict typing" in content
    assert warnings == []
