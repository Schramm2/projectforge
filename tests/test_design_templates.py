"""Tests for design template helpers and loading."""

from ubundiforge.design_templates import (
    design_template_choices_for_stack,
    design_template_ids_for_stack,
    design_template_supported_for_stack,
    load_design_template,
)


def test_design_template_choices_are_available_for_frontend_stacks():
    choices = design_template_choices_for_stack("nextjs")

    assert choices
    assert choices[0][0] == "ubundi-brand-guide"


def test_design_template_ids_are_empty_for_backend_only_stacks():
    assert design_template_ids_for_stack("fastapi") == []


def test_design_template_supported_for_stack_checks_stack_capabilities():
    assert design_template_supported_for_stack("both", "ubundi-brand-guide") is True
    assert design_template_supported_for_stack("fastapi", "ubundi-brand-guide") is False


def test_load_design_template_prefers_local_override(tmp_path, monkeypatch):
    local_dir = tmp_path / ".forge" / "design-templates"
    local_dir.mkdir(parents=True)
    override_path = local_dir / "ubundi-brand-guide.md"
    override_path.write_text("Local override template content that is definitely long enough.")

    monkeypatch.setattr("ubundiforge.design_templates.LOCAL_DESIGN_TEMPLATES_DIR", local_dir)
    monkeypatch.setattr(
        "ubundiforge.design_templates.GLOBAL_DESIGN_TEMPLATES_DIR",
        tmp_path / "global-design-templates",
    )

    content, warnings = load_design_template("ubundi-brand-guide")

    assert content == "Local override template content that is definitely long enough."
    assert any("local design template" in warning.lower() for warning in warnings)


def test_load_design_template_returns_bundled_template():
    content, warnings = load_design_template("ubundi-brand-guide")

    assert content is not None
    assert "Ubundi Brand Guide" in content
    assert warnings == []
