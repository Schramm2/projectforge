"""Global pytest safety fixtures."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_forge_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every test away from the developer's real ``~/.forge`` state."""

    forge_home = tmp_path / "forge-home"
    monkeypatch.setenv("FORGE_HOME", str(forge_home))

    patches = {
        "projectforge.conventions.FORGE_DIR": forge_home,
        "projectforge.conventions.CONVENTIONS_PATH": forge_home / "conventions.md",
        "projectforge.conventions.PROFILES_DIR": forge_home / "profiles",
        "projectforge.scaffold_log.FORGE_DIR": forge_home,
        "projectforge.scaffold_log.SCAFFOLD_LOG_PATH": forge_home / "scaffold.log",
        "projectforge.quality.FORGE_DIR": forge_home,
        "projectforge.quality.QUALITY_LOG_PATH": forge_home / "quality.jsonl",
        "projectforge.preferences.FORGE_DIR": forge_home,
        "projectforge.preferences.PREFERENCES_PATH": forge_home / "preferences.json",
        "projectforge.setup.FORGE_DIR": forge_home,
        "projectforge.setup.CONFIG_PATH": forge_home / "config.json",
        "projectforge.setup.CONVENTIONS_PATH": forge_home / "conventions.md",
        "projectforge.doctor.CONFIG_PATH": forge_home / "config.json",
        "projectforge.convention_profiles.PROFILES_DIR": forge_home / "profiles",
        "projectforge.design_templates.GLOBAL_DESIGN_TEMPLATES_DIR": (
            forge_home / "design-templates"
        ),
        "projectforge.runner.HOOKS_DIR": forge_home / "hooks",
        "projectforge.runner.POST_SCAFFOLD_HOOK": forge_home / "hooks" / "post-scaffold.sh",
        "projectforge.orchestrator.QUALITY_LOG_PATH": forge_home / "quality.jsonl",
        "projectforge.cli.SCAFFOLD_LOG_PATH": forge_home / "scaffold.log",
    }
    for target, value in patches.items():
        monkeypatch.setattr(target, value)
