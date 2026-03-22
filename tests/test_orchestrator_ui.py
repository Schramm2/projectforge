"""Tests for orchestrator UI helpers: map_progress_to_activity and _render_decomposition_plan."""

from __future__ import annotations

import time

from ubundiforge.orchestrator import map_progress_to_activity
from ubundiforge.protocol import ProgressEvent


def _make_event(event_type: str, message: str = "some message") -> ProgressEvent:
    return ProgressEvent(
        task_id="task-1",
        agent_label="claude[arch]",
        event_type=event_type,
        message=message,
        timestamp=time.time(),
    )


class TestMapProgressToActivity:
    def test_started_event(self) -> None:
        event = _make_event("started", "Beginning scaffold")
        result = map_progress_to_activity(event)
        assert result == "claude[arch]: Beginning scaffold"

    def test_progress_event(self) -> None:
        event = _make_event("progress", "Writing models")
        result = map_progress_to_activity(event)
        assert result == "claude[arch]: Writing models"

    def test_completed_event(self) -> None:
        event = _make_event("completed", "Finished successfully")
        result = map_progress_to_activity(event)
        assert result == "claude[arch]: Done"

    def test_failed_event(self) -> None:
        event = _make_event("failed", "subprocess timed out")
        result = map_progress_to_activity(event)
        assert result == "claude[arch]: Failed — subprocess timed out"
