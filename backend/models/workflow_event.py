"""Workflow event model — tracks every LangGraph node execution.

Each workflow_events row represents a single node execution attempt
within a workflow run, providing a full audit trail with timing data.
"""

from __future__ import annotations

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin


class WorkflowEvent(UUIDMixin, TimestampMixin, Base):
    """Records a single node execution event within a workflow run."""

    __tablename__ = "workflow_events"

    # ── Foreign Key ──────────────────────────────────────────────────────
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Event Data ───────────────────────────────────────────────────────
    node_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="LangGraph node name, e.g. 'analyze_artwork', 'generate_reel'",
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Event type: started, completed, failed, skipped, retrying",
    )

    # ── Timing ───────────────────────────────────────────────────────────
    started_at: Mapped[str | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[str | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Execution duration in milliseconds",
    )

    # ── Error & Metadata ─────────────────────────────────────────────────
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True,
        comment="Node-specific data: track selected, tokens used, etc.",
    )

    # ── Retry Info ───────────────────────────────────────────────────────
    attempt_number: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False,
        comment="Attempt number for retry tracking (1 = first attempt)",
    )

    # ── Relationships ────────────────────────────────────────────────────
    workflow_run: Mapped["WorkflowRun"] = relationship(
        "WorkflowRun",
        back_populates="events",
    )

    def __repr__(self) -> str:
        return (
            f"<WorkflowEvent node={self.node_name} "
            f"type={self.event_type} run={self.workflow_run_id}>"
        )


from backend.models.workflow_run import WorkflowRun  # noqa: E402, F401
