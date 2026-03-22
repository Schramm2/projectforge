# src/ubundiforge/card.py
"""Forge card — SVG badge and project card generation."""

from pathlib import Path

_BADGE_MARKER = "<!-- forged-with-ubundiforge -->"


def generate_badge_svg() -> str:
    """Generate a shields.io-style 'forged with | UbundiForge' badge."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="170" height="20">'
        '<rect width="82" height="20" rx="3" fill="#A16EFA"/>'
        '<rect x="82" width="88" height="20" rx="3" fill="#2D365C"/>'
        '<rect x="82" width="4" height="20" fill="#2D365C"/>'
        '<text x="41" y="14" fill="#fff" font-family="sans-serif" '
        'font-size="11" text-anchor="middle" font-weight="bold">forged with</text>'
        '<text x="126" y="14" fill="#C6CEE6" font-family="sans-serif" '
        'font-size="11" text-anchor="middle">UbundiForge</text>'
        "</svg>"
    )


def generate_card_svg(
    *,
    name: str,
    stack: str,
    backends: list[str],
    date: str,
) -> str:
    """Generate a richer project card SVG."""
    backend_text = " + ".join(backends)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="360" height="120">'
        '<rect width="360" height="120" rx="8" fill="#1a1f35" stroke="#2D365C"/>'
        '<text x="20" y="35" fill="#A16EFA" font-family="sans-serif" font-size="18">&#x27E1;</text>'
        f'<text x="45" y="35" fill="#F7F9FF" font-family="sans-serif" '
        f'font-size="16" font-weight="bold">{name}</text>'
        '<text x="45" y="55" fill="#8893B3" font-family="sans-serif" '
        'font-size="11">Scaffolded with UbundiForge</text>'
        f'<circle cx="25" cy="90" r="4" fill="#75DCE6"/>'
        f'<text x="35" y="94" fill="#8893B3" font-family="sans-serif" font-size="11">{stack}</text>'
        f'<circle cx="120" cy="90" r="4" fill="#A16EFA"/>'
        f'<text x="130" y="94" fill="#8893B3" font-family="sans-serif" '
        f'font-size="11">{backend_text}</text>'
        f'<text x="270" y="94" fill="#8893B3" font-family="sans-serif" font-size="11">{date}</text>'
        "</svg>"
    )


def inject_badge_into_readme(project_dir: Path) -> None:
    """Inject a Forge badge into the project's README.md after the first heading."""
    readme = project_dir / "README.md"
    if not readme.exists():
        return

    content = readme.read_text()

    # Don't inject twice
    if _BADGE_MARKER in content:
        return

    badge_md = (
        f"\n{_BADGE_MARKER}\n"
        f"![UbundiForge]"
        f"(https://img.shields.io/badge/forged%20with-forge-A16EFA)\n"
    )

    # Insert after first heading
    lines = content.splitlines(keepends=True)
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            insert_idx = i + 1
            break

    lines.insert(insert_idx, badge_md)
    readme.write_text("".join(lines))


def write_card(project_dir: Path, *, name: str, stack: str, backends: list[str], date: str) -> None:
    """Write the project card SVG to .forge/card.svg."""
    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True, exist_ok=True)
    svg = generate_card_svg(name=name, stack=stack, backends=backends, date=date)
    (forge_dir / "card.svg").write_text(svg)
