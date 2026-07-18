"""Tests for design template helpers and loading."""

from pathlib import Path

from projectforge.design_templates import (
    design_template_choices_for_stack,
    design_template_ids_for_stack,
    design_template_supported_for_stack,
    load_design_template,
)


def test_design_template_choices_are_available_for_frontend_stacks():
    choices = design_template_choices_for_stack("nextjs")

    assert choices
    assert choices[0][0] == "default-design-guide"


def test_design_template_ids_are_empty_for_backend_only_stacks():
    assert design_template_ids_for_stack("fastapi") == []


def test_design_template_supported_for_stack_checks_stack_capabilities():
    assert design_template_supported_for_stack("both", "default-design-guide") is True
    assert design_template_supported_for_stack("fastapi", "default-design-guide") is False


def test_load_design_template_prefers_local_override(tmp_path, monkeypatch):
    local_dir = tmp_path / ".forge" / "design-templates"
    local_dir.mkdir(parents=True)
    override_path = local_dir / "default-design-guide.md"
    override_path.write_text("Local override template content that is definitely long enough.")

    monkeypatch.setattr("projectforge.design_templates.LOCAL_DESIGN_TEMPLATES_DIR", local_dir)
    monkeypatch.setattr(
        "projectforge.design_templates.GLOBAL_DESIGN_TEMPLATES_DIR",
        tmp_path / "global-design-templates",
    )

    content, warnings = load_design_template("default-design-guide")

    assert content == "Local override template content that is definitely long enough."
    assert any("local design template" in warning.lower() for warning in warnings)


def test_load_design_template_returns_bundled_template():
    content, warnings = load_design_template("default-design-guide")

    assert content is not None
    assert "Default Design Guide" in content
    assert warnings == []


def test_load_design_template_hides_unreadable_file_detail(tmp_path, monkeypatch):
    template = tmp_path / "private-template.md"
    template.write_text("A sufficiently detailed design template for the test.")
    monkeypatch.setattr(
        "projectforge.design_templates._resolve_design_template_path",
        lambda *_args: template,
    )
    original_read_text = Path.read_text

    def unreadable(path: Path, *args, **kwargs):
        if path == template:
            raise OSError("private filesystem detail")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)

    content, warnings = load_design_template("default-design-guide")

    assert content is None
    assert warnings == [
        "Forge could not read the selected design template, so it will continue without "
        "template guidance. Check that the file is readable, then retry."
    ]
    assert "private filesystem detail" not in warnings[0]
