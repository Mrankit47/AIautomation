"""Unit tests for transient error retry decorator/helper in nodes."""

from __future__ import annotations

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.graph.nodes import _retry_on_transient
from backend.core.exceptions import ValidationException, AuthenticationException


@pytest.mark.asyncio
async def test_retry_on_transient_success_eventually() -> None:
    """Test that a transient error is retried and eventually succeeds."""
    call_count = 0

    async def transient_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("Transient network issue")
        return "success-data"

    # Mock _emit_event to avoid DB connection requirement
    with patch("backend.graph.nodes._emit_event") as mock_emit:
        result = await _retry_on_transient(
            coro_factory=transient_operation,
            node_name="test_node",
            workflow_run_id="00000000-0000-0000-0000-000000000000",
            max_retries=3,
            base_delay=0.01,  # Short delay for fast tests
        )

        assert result == "success-data"
        assert call_count == 3
        # Should have emitted 2 "retrying" events and 1 "completed" event
        assert mock_emit.call_count == 3


@pytest.mark.asyncio
async def test_retry_on_transient_fails_immediately_on_non_retryable() -> None:
    """Test that non-retryable errors (e.g. ValidationException) raise immediately without retrying."""
    call_count = 0

    async def invalid_operation():
        nonlocal call_count
        call_count += 1
        raise ValidationException("Invalid media format")

    with patch("backend.graph.nodes._emit_event") as mock_emit:
        with pytest.raises(ValidationException):
            await _retry_on_transient(
                coro_factory=invalid_operation,
                node_name="test_node",
                workflow_run_id="00000000-0000-0000-0000-000000000000",
                max_retries=3,
                base_delay=0.01,
            )

        assert call_count == 1
        # Should emit 1 "failed" event
        mock_emit.assert_called_once()


@pytest.mark.asyncio
async def test_retry_on_transient_exhausts_retries() -> None:
    """Test that if transient errors persist, it exhausts retries and raises last exception."""
    call_count = 0

    async def persistent_failure():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("Persistent network crash")

    with patch("backend.graph.nodes._emit_event") as mock_emit:
        with pytest.raises(RuntimeError) as exc_info:
            await _retry_on_transient(
                coro_factory=persistent_failure,
                node_name="test_node",
                workflow_run_id="00000000-0000-0000-0000-000000000000",
                max_retries=2,  # Try 1 + 2 retries = 3 calls total
                base_delay=0.01,
            )

        assert "Persistent network crash" in str(exc_info.value)
        assert call_count == 3
        # Should emit 2 "retrying" events and 1 "failed" event
        assert mock_emit.call_count == 3
