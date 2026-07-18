#!/usr/bin/env python3
"""Validate the repository's portable Forge operator skill package."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "forge-scaffold"


def main() -> int:
    skill_path = SKILL_ROOT / "SKILL.md"
    text = skill_path.read_text()
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise SystemExit("SKILL.md must contain YAML frontmatter")
    metadata = yaml.safe_load(parts[1])
    if set(metadata) != {"name", "description"}:
        raise SystemExit("Skill frontmatter must contain only name and description")
    if metadata["name"] != "forge-scaffold" or not metadata["description"].startswith("Use when"):
        raise SystemExit("Skill routing metadata is invalid")

    agent = yaml.safe_load((SKILL_ROOT / "agents" / "openai.yaml").read_text())
    interface = agent.get("interface", {})
    if not 25 <= len(interface.get("short_description", "")) <= 64:
        raise SystemExit("Skill short_description must contain 25-64 characters")
    if "$forge-scaffold" not in interface.get("default_prompt", ""):
        raise SystemExit("Skill default_prompt must explicitly name $forge-scaffold")
    if agent.get("policy", {}).get("allow_implicit_invocation") is not True:
        raise SystemExit("Skill implicit invocation policy is missing")

    expected = {
        "SKILL.md",
        "agents/openai.yaml",
        "references/evidence-and-recovery.md",
        "references/workflows.md",
    }
    actual = {str(path.relative_to(SKILL_ROOT)) for path in SKILL_ROOT.rglob("*") if path.is_file()}
    if actual != expected:
        raise SystemExit(f"Unexpected skill package surface: {sorted(actual ^ expected)}")

    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        if not (SKILL_ROOT / target).is_file():
            raise SystemExit(f"Broken skill reference: {target}")

    stale = re.compile(r"v0\.4\.1|dangerously-skip|\byolo\b|PyPI|CHANGELOG|README\.md", re.I)
    for path in sorted(SKILL_ROOT.rglob("*")):
        if path.is_file() and stale.search(path.read_text()):
            raise SystemExit(f"Stale or unsafe skill content in {path.relative_to(ROOT)}")

    print("Forge operator skill package is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
