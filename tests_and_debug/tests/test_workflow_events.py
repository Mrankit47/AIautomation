"""Unit tests for workflow events model and ordering."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend.models.workflow_run import WorkflowRun
from backend.models.workflow_event import WorkflowEvent


def test_workflow_event_creation():
    """Test that a WorkflowEvent instance can be initialized with correct fields."""
    run_id = uuid.uuid4()
    started = datetime.now(timezone.utc)
    completed = datetime.now(timezone.utc)

    event = WorkflowEvent(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        node_name="analyze_artwork",
        event_type="completed",
        started_at=started,
        completed_at=completed,
        duration_ms=1200,
        error_message=None,
        event_metadata={"tokens_used": 150},
        attempt_number=1,
    )

    assert event.node_name == "analyze_artwork"
    assert event.event_type == "completed"
    assert event.duration_ms == 1200
    assert event.event_metadata == {"tokens_used": 150}
    assert event.attempt_number == 1
    assert event.workflow_run_id == run_id


def test_workflow_run_relationship():
    """Test the back-populated relationship between WorkflowRun and WorkflowEvent."""
    run = WorkflowRun(
        id=uuid.uuid4(),
        artwork_id=uuid.uuid4(),
        workflow_version="v1",
        status="running",
    )

    event1 = WorkflowEvent(
        id=uuid.uuid4(),
        node_name="analyze_artwork",
        event_type="completed",
        created_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc),
    )
    event2 = WorkflowEvent(
        id=uuid.uuid4(),
        node_name="generate_reel",
        event_type="started",
        created_at=datetime(2026, 6, 13, 12, 5, 0, tzinfo=timezone.utc),
    )

    run.events = [event1, event2]

    # Verify back-population
    assert event1.workflow_run == run
    assert event2.workflow_run == run
    assert len(run.events) == 2
