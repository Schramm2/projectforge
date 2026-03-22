"""Scaffold analytics — aggregation and rendering for forge stats."""

from collections import Counter

from rich.console import Console
from rich.text import Text

from ubundiforge.quality import SIGNAL_KEYS
from ubundiforge.ui import ACCENTS, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, muted


def aggregate_stats(
    *,
    scaffold_entries: list[dict],
    quality_entries: list[dict],
) -> dict:
    """Aggregate scaffold history and quality signals into summary stats."""
    total = len(scaffold_entries)
    stacks: dict[str, int] = dict(Counter(e.get("stack", "unknown") for e in scaffold_entries))

    # Backend performance: {backend: {phase: success_rate}}
    backend_perf: dict[str, dict[str, float]] = {}
    by_backend_phase: dict[tuple[str, str], list[dict]] = {}
    for q in quality_entries:
        key = (q.get("backend", ""), q.get("phase", ""))
        by_backend_phase.setdefault(key, []).append(q)

    for (backend, phase), entries in by_backend_phase.items():
        if not backend:
            continue
        successes = sum(1 for e in entries if all(e.get(k, False) for k in SIGNAL_KEYS))
        rate = successes / len(entries) if entries else 0.0
        backend_perf.setdefault(backend, {})[phase] = round(rate, 2)

    # Overall success rate from quality signals
    if quality_entries:
        all_success = sum(1 for e in quality_entries if all(e.get(k, False) for k in SIGNAL_KEYS))
        success_rate = round(all_success / len(quality_entries), 2)
    else:
        success_rate = 0.0

    recent = scaffold_entries[-5:] if scaffold_entries else []

    return {
        "total_scaffolds": total,
        "success_rate": success_rate,
        "stacks": stacks,
        "backend_performance": backend_perf,
        "recent": recent,
    }


def render_stats(console: Console, stats: dict) -> None:
    """Render the forge stats dashboard."""
    header = Text()
    header.append("Forge Stats", style=f"bold {ACCENTS['violet']}")
    console.print()
    console.print(header)
    console.print()

    # Top-level metrics
    metrics = Text("  ")
    metrics.append(str(stats["total_scaffolds"]), style=f"bold {ACCENTS['amber']}")
    metrics.append(" scaffolds  ", style=TEXT_MUTED)
    metrics.append(f"{stats['success_rate']:.0%}", style=f"bold {ACCENTS['aqua']}")
    metrics.append(" success rate", style=TEXT_MUTED)
    console.print(metrics)
    console.print()

    # Stack distribution
    if stats["stacks"]:
        console.print(muted("  STACKS"))
        max_count = max(stats["stacks"].values())
        for stack, count in sorted(stats["stacks"].items(), key=lambda x: -x[1]):
            bar_width = int(16 * count / max_count)
            line = Text("  ")
            line.append(f"{stack:<16}", style=TEXT_SECONDARY)
            line.append("█" * bar_width, style=ACCENTS["violet"])
            line.append("░" * (16 - bar_width), style=ACCENTS["indigo"])
            line.append(f" {count}", style=TEXT_MUTED)
            console.print(line)
        console.print()

    # Backend performance
    if stats["backend_performance"]:
        console.print(muted("  BACKEND PERFORMANCE"))
        for backend, phases in sorted(stats["backend_performance"].items()):
            parts = [f"{phase} {rate:.0%}" for phase, rate in sorted(phases.items())]
            line = Text("  ")
            line.append(f"{backend:<8}", style=f"bold {TEXT_PRIMARY}")
            line.append(" · ".join(parts), style=ACCENTS["aqua"])
            console.print(line)
        console.print()

    # Recent scaffolds
    if stats["recent"]:
        console.print(muted("  RECENT"))
        for entry in reversed(stats["recent"]):
            line = Text("  ")
            line.append(entry.get("name", "?"), style=TEXT_SECONDARY)
            line.append(f"  {entry.get('stack', '?')}", style=TEXT_MUTED)
            line.append(f"  {entry.get('timestamp', '')[:10]}", style=TEXT_MUTED)
            console.print(line)
        console.print()
