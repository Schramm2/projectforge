"""Design template options and template loading for scaffold prompts."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DesignTemplateOption:
    """Metadata for a selectable design template."""

    label: str
    prompt_description: str
    template_filename: str


DESIGN_TEMPLATE_ORDER = ("ubundi-brand-guide",)

DESIGN_TEMPLATE_OPTIONS: dict[str, DesignTemplateOption] = {
    "ubundi-brand-guide": DesignTemplateOption(
        label="Ubundi Brand Guide",
        prompt_description="Ubundi's dark, modern, glassy visual language for apps and sites.",
        template_filename="ubundi-brand-guide.md",
    ),
}

DESIGN_TEMPLATE_SUPPORTED_STACKS = {"nextjs", "both"}
MIN_DESIGN_TEMPLATE_LENGTH = 50

BUNDLED_DESIGN_TEMPLATES_DIR = Path(__file__).parent / "templates" / "design-templates"
LOCAL_DESIGN_TEMPLATES_DIR = Path.cwd() / ".forge" / "design-templates"
GLOBAL_DESIGN_TEMPLATES_DIR = Path.home() / ".forge" / "design-templates"


def design_template_choices_for_stack(stack: str) -> list[tuple[str, str]]:
    """Return ordered design template choices for a stack."""
    template_ids = design_template_ids_for_stack(stack)
    return [
        (template_id, DESIGN_TEMPLATE_OPTIONS[template_id].label)
        for template_id in template_ids
    ]


def design_template_ids_for_stack(stack: str) -> list[str]:
    """Return ordered design template ids supported by a stack."""
    if stack not in DESIGN_TEMPLATE_SUPPORTED_STACKS:
        return []

    return list(DESIGN_TEMPLATE_ORDER)


def design_template_supported_for_stack(stack: str, template_id: str) -> bool:
    """Return whether a specific design template is supported for a stack."""
    return template_id in design_template_ids_for_stack(stack)


def load_design_template(template_id: str | None) -> tuple[str | None, list[str]]:
    """Load a selected design template from local, global, or bundled sources."""
    warnings: list[str] = []

    if not template_id:
        return None, warnings

    option = DESIGN_TEMPLATE_OPTIONS.get(template_id)
    if option is None:
        warnings.append(f"Unknown design template '{template_id}' — skipping template guidance.")
        return None, warnings

    source = _resolve_design_template_path(template_id, option.template_filename)
    if source is None or not source.exists():
        warnings.append(
            f"Design template '{template_id}' is configured but its file could not be found."
        )
        return None, warnings

    if source.parent == LOCAL_DESIGN_TEMPLATES_DIR:
        warnings.append(f"Using local design template from {source}")
    elif source.parent == GLOBAL_DESIGN_TEMPLATES_DIR:
        warnings.append(f"Using global design template from {source}")

    content = source.read_text()
    if not content.strip():
        warnings.append("Design template file is empty — frontend scaffolds will ignore it.")
    elif len(content.strip()) < MIN_DESIGN_TEMPLATE_LENGTH:
        warnings.append("Design template file is very short — consider adding more detail.")

    return content, warnings


def _resolve_design_template_path(template_id: str, template_filename: str) -> Path | None:
    """Resolve a template path, preferring local and global overrides."""
    override_filename = f"{template_id}.md"
    for directory in (LOCAL_DESIGN_TEMPLATES_DIR, GLOBAL_DESIGN_TEMPLATES_DIR):
        candidate = directory / override_filename
        if candidate.exists():
            return candidate

    bundled = BUNDLED_DESIGN_TEMPLATES_DIR / template_filename
    if bundled.exists():
        return bundled

    return None
