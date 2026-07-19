"""Finalize a generated scaffold and record its local delivery evidence."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from projectforge.convention_models import ConventionContribution
from projectforge.ui import muted, status_line
from projectforge.verify import VerifyReport

PhaseBackend = tuple[str, str]


class ScaffoldRecordError(OSError):
    """The required project-local scaffold manifest could not be saved."""


@dataclass(frozen=True)
class ScaffoldCompletionSettings:
    """Inputs required to turn generated files into a completed Forge delivery."""

    answers: dict[str, Any]
    phase_backends: list[PhaseBackend]
    project_dir: Path
    conventions: str
    model_override: str | None
    backend_models: dict[str, str]
    approval_mode: str
    convention_sources: tuple[ConventionContribution, ...]
    verification_requested: bool
    verbose: bool
    scaffold_started_at: float
    sound_enabled: bool
    open_editor: bool
    preferred_editor: str
    agent_stats: dict[str, int] | None


@dataclass(frozen=True)
class ScaffoldCompletionDependencies:
    """Filesystem, verification, presentation, and desktop operations used at completion."""

    write_manifest: Callable[..., None]
    ensure_git: Callable[[Path], bool]
    verify: Callable[..., VerifyReport]
    write_verification: Callable[[VerifyReport, Path], None]
    append_quality: Callable[..., None]
    run_hook: Callable[[Path, dict[str, Any]], None]
    append_log: Callable[..., None]
    record_preferences: Callable[[dict[str, Any]], None]
    render_dashboard: Callable[..., None]
    write_card: Callable[..., None]
    inject_readme_badge: Callable[[Path], None]
    play_sound: Callable[..., None]
    open_project: Callable[..., None]


def complete_scaffold(
    *,
    console: Console,
    settings: ScaffoldCompletionSettings,
    dependencies: ScaffoldCompletionDependencies,
) -> None:
    """Persist required evidence, best-effort local history, and the final project handoff."""
    try:
        dependencies.write_manifest(
            settings.answers,
            settings.phase_backends,
            settings.project_dir,
            settings.conventions,
            model_override=settings.model_override,
            backend_models=settings.backend_models,
            approval_mode=settings.approval_mode,
            convention_sources=settings.convention_sources,
        )
    except OSError as exc:
        raise ScaffoldRecordError from exc

    git_initialized = dependencies.ensure_git(settings.project_dir)
    verification_report, evidence_saved = _run_verification(settings, dependencies)

    try:
        dependencies.append_quality(
            stack=settings.answers["stack"],
            phase_backends=settings.phase_backends,
            verify_report=verification_report,
            project_dir=settings.project_dir,
        )
    except OSError:
        evidence_saved = False

    dependencies.run_hook(settings.project_dir, settings.answers)
    elapsed = time.monotonic() - settings.scaffold_started_at
    try:
        dependencies.append_log(
            settings.answers,
            settings.phase_backends,
            settings.project_dir,
            verify_report=verification_report,
            verification_requested=settings.verification_requested,
            duration_seconds=elapsed,
        )
        dependencies.record_preferences(settings.answers)
    except OSError:
        evidence_saved = False

    dependencies.render_dashboard(
        console=console,
        answers=settings.answers,
        phase_backends=settings.phase_backends,
        project_dir=settings.project_dir,
        verify_report=verification_report,
        elapsed=elapsed,
        agent_stats=settings.agent_stats,
    )
    evidence_saved = _write_project_card(settings, dependencies) and evidence_saved

    if not evidence_saved:
        console.print(
            status_line(
                "The project was created, but Forge could not save some local history or "
                "verification files. Check that the project and Forge data folders are "
                "writable before the next run.",
                accent="amber",
            )
        )

    dependencies.play_sound(success=True, enabled=settings.sound_enabled)
    if not git_initialized:
        console.print(
            muted('Run git init && git add -A && git commit -m "Initial commit" manually.')
        )
    if settings.open_editor:
        dependencies.open_project(
            settings.project_dir,
            preferred_editor=settings.preferred_editor,
        )


def _run_verification(
    settings: ScaffoldCompletionSettings,
    dependencies: ScaffoldCompletionDependencies,
) -> tuple[VerifyReport | None, bool]:
    if not settings.verification_requested:
        return None, True

    report = dependencies.verify(
        settings.answers["stack"],
        settings.project_dir,
        verbose=settings.verbose,
    )
    try:
        dependencies.write_verification(report, settings.project_dir)
    except OSError:
        return report, False
    return report, True


def _write_project_card(
    settings: ScaffoldCompletionSettings,
    dependencies: ScaffoldCompletionDependencies,
) -> bool:
    scaffold_date = datetime.now(UTC).strftime("%Y-%m-%d")
    backends_used = sorted({backend for _, backend in settings.phase_backends})
    try:
        dependencies.write_card(
            settings.project_dir,
            name=settings.answers["name"],
            stack=settings.answers["stack"],
            backends=backends_used,
            date=scaffold_date,
        )
        dependencies.inject_readme_badge(settings.project_dir)
    except OSError:
        return False
    return True
