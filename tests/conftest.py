"""Global pytest safety fixtures."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_forge_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every test away from the developer's real ``~/.forge`` state."""

    forge_home = tmp_path / "forge-home"
    monkeypatch.setenv("FORGE_HOME", str(forge_home))

    patches = {
        "ubundiforge.conventions.FORGE_DIR": forge_home,
        "ubundiforge.conventions.CONVENTIONS_PATH": forge_home / "conventions.md",
        "ubundiforge.conventions.PROFILES_DIR": forge_home / "profiles",
        "ubundiforge.scaffold_log.FORGE_DIR": forge_home,
        "ubundiforge.scaffold_log.SCAFFOLD_LOG_PATH": forge_home / "scaffold.log",
        "ubundiforge.quality.FORGE_DIR": forge_home,
        "ubundiforge.quality.QUALITY_LOG_PATH": forge_home / "quality.jsonl",
        "ubundiforge.preferences.FORGE_DIR": forge_home,
        "ubundiforge.preferences.PREFERENCES_PATH": forge_home / "preferences.json",
        "ubundiforge.setup.FORGE_DIR": forge_home,
        "ubundiforge.setup.CONFIG_PATH": forge_home / "config.json",
        "ubundiforge.setup.CONVENTIONS_PATH": forge_home / "conventions.md",
        "ubundiforge.doctor.CONFIG_PATH": forge_home / "config.json",
        "ubundiforge.convention_profiles.PROFILES_DIR": forge_home / "profiles",
        "ubundiforge.design_templates.GLOBAL_DESIGN_TEMPLATES_DIR": (
            forge_home / "design-templates"
        ),
        "ubundiforge.runner.HOOKS_DIR": forge_home / "hooks",
        "ubundiforge.runner.POST_SCAFFOLD_HOOK": forge_home / "hooks" / "post-scaffold.sh",
        "ubundiforge.orchestrator.QUALITY_LOG_PATH": forge_home / "quality.jsonl",
        "ubundiforge.cli.SCAFFOLD_LOG_PATH": forge_home / "scaffold.log",
    }
    for target, value in patches.items():
        monkeypatch.setattr(target, value)
