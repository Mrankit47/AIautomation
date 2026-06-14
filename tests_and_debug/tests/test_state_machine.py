"""Unit tests for strict state machine status transitions."""

from __future__ import annotations

import pytest
import uuid

from backend.models.artwork import Artwork, ArtworkStatus
from backend.core.exceptions import WorkflowException


def test_valid_transitions():
    """Test that valid status transitions succeed."""
    artwork = Artwork(
        id=uuid.uuid4(),
        title="Test Art",
        status=ArtworkStatus.UPLOADED,
    )

    # UPLOADED -> ANALYZING (valid)
    artwork.transition_to(ArtworkStatus.ANALYZING)
    assert artwork.status == ArtworkStatus.ANALYZING

    # ANALYZING -> PROCESSING (valid)
    artwork.transition_to(ArtworkStatus.PROCESSING)
    assert artwork.status == ArtworkStatus.PROCESSING

    # PROCESSING -> PUBLISHING (valid)
    artwork.transition_to(ArtworkStatus.PUBLISHING)
    assert artwork.status == ArtworkStatus.PUBLISHING

    # PUBLISHING -> COMPLETED (valid)
    artwork.transition_to(ArtworkStatus.COMPLETED)
    assert artwork.status == ArtworkStatus.COMPLETED


def test_invalid_transitions():
    """Test that invalid transitions raise WorkflowException."""
    artwork = Artwork(
        id=uuid.uuid4(),
        title="Test Art",
        status=ArtworkStatus.UPLOADED,
    )

    # UPLOADED -> COMPLETED is invalid (should skip analyzing/processing)
    with pytest.raises(WorkflowException) as exc_info:
        artwork.transition_to(ArtworkStatus.COMPLETED)
    assert "Invalid status transition" in str(exc_info.value)

    # Terminal state transitions
    artwork.status = ArtworkStatus.COMPLETED
    with pytest.raises(WorkflowException):
        artwork.transition_to(ArtworkStatus.UPLOADED)


def test_recovery_transition():
    """Test that transition from FAILED back to UPLOADED is allowed."""
    artwork = Artwork(
        id=uuid.uuid4(),
        title="Test Art",
        status=ArtworkStatus.FAILED,
    )

    artwork.transition_to(ArtworkStatus.UPLOADED)
    assert artwork.status == ArtworkStatus.UPLOADED
