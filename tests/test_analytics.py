"""Tests for scaffold analytics."""

from io import StringIO

from rich.console import Console

from projectforge.analytics import aggregate_stats, render_stats


def test_aggregate_stats_empty():
    stats = aggregate_stats(scaffold_entries=[], quality_entries=[])
    assert stats["total_scaffolds"] == 0
    assert stats["success_rate"] is None
    assert stats["verified_scaffolds"] == 0
    assert stats["stacks"] == {}


def test_aggregate_stats_with_data():
    scaffolds = [
        {
            "name": "p1",
            "stack": "fastapi",
            "backends": ["claude"],
            "timestamp": "2026-03-20T10:00:00",
            "verification_status": "passed",
        },
        {
            "name": "p2",
            "stack": "fastapi",
            "backends": ["claude"],
            "timestamp": "2026-03-20T11:00:00",
            "verification_status": "failed",
        },
        {
            "name": "p3",
            "stack": "nextjs",
            "backends": ["antigravity"],
            "timestamp": "2026-03-20T12:00:00",
        },
    ]
    quality = [
        {
            "stack": "fastapi",
            "backend": "claude",
            "phase": "architecture",
            "lint_clean": True,
            "tests_passed": True,
            "typecheck_clean": True,
            "health_ok": True,
            "built": True,
        },
        {
            "stack": "fastapi",
            "backend": "claude",
            "phase": "architecture",
            "lint_clean": True,
            "tests_passed": False,
            "typecheck_clean": True,
            "health_ok": True,
            "built": True,
        },
    ]
    stats = aggregate_stats(scaffold_entries=scaffolds, quality_entries=quality)
    assert stats["total_scaffolds"] == 3
    assert stats["stacks"]["fastapi"] == 2
    assert stats["stacks"]["nextjs"] == 1
    assert "claude" in stats["backend_performance"]
    assert stats["success_rate"] == 0.5
    assert stats["verified_scaffolds"] == 2


def test_render_stats_no_error():
    """render_stats runs without error on sample data."""
    stats = {
        "total_scaffolds": 5,
        "success_rate": 0.8,
        "verified_scaffolds": 5,
        "stacks": {"fastapi": 3, "nextjs": 2},
        "backend_performance": {"claude": {"architecture": 0.9}},
        "recent": [],
    }
    console = Console(file=StringIO(), width=80)
    render_stats(console, stats)


def test_render_stats_empty():
    """render_stats gives a useful first-run message instead of a 0% failure rate."""
    stats = {
        "total_scaffolds": 0,
        "success_rate": None,
        "verified_scaffolds": 0,
        "stacks": {},
        "backend_performance": {},
        "recent": [],
    }
    output = StringIO()
    console = Console(file=output, width=80)
    render_stats(console, stats)
    assert "No scaffolds recorded yet" in output.getvalue()
