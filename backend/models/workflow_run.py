"""Workflow run ORM model — tracks each execution of the artwork pipeline."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin


from sqlalchemy.ext.hybrid import hybrid_property

class WorkflowStatus(str, enum.Enum):
    """Status of a workflow execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"

# Validate that all enum values match PostgreSQL native uppercase constraints
for _member in WorkflowStatus:
    if _member.value != _member.value.upper():
        raise ValueError(
            f"WorkflowStatus member '{_member.name}' has non-uppercase value '{_member.value}'. "
            "Values must be uppercase to match PostgreSQL native enum constraints."
        )




class WorkflowRun(UUIDMixin, TimestampMixin, Base):
    """Records a single execution of the artwork processing workflow."""

    __tablename__ = "workflow_runs"

    # ── Foreign Key ──────────────────────────────────────────────────────
    artwork_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artworks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Execution Metadata ───────────────────────────────────────────────
    workflow_version: Mapped[str] = mapped_column(
        String(20), default="v1", nullable=False
    )
    _db_status: Mapped[WorkflowStatus] = mapped_column(
        "status",
        Enum(
            "PENDING",
            "RUNNING",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
            name="workflow_status",
            native_enum=True,
            values_callable=lambda x: ["PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"]
        ),
        default=WorkflowStatus.PENDING,
        nullable=False,
    )

    @hybrid_property
    def status(self) -> WorkflowStatus:
        if self._db_status == WorkflowStatus.COMPLETED and self.error_history:
            return WorkflowStatus.COMPLETED_WITH_WARNINGS
        return self._db_status

    @status.setter
    def status(self, value: WorkflowStatus) -> None:
        if value == WorkflowStatus.COMPLETED_WITH_WARNINGS:
            self._db_status = WorkflowStatus.COMPLETED
        else:
            self._db_status = value

    current_node: Mapped[str | None] = mapped_column(String(100), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Timing ───────────────────────────────────────────────────────────
    started_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Results ──────────────────────────────────────────────────────────
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_history: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    # ── Publishing Status ────────────────────────────────────────────────
    instagram_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    youtube_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pinterest_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tiktok_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Error ────────────────────────────────────────────────────────────
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    artwork: Mapped["Artwork"] = relationship(
        "Artwork",
        back_populates="workflow_runs",
    )

    def __repr__(self) -> str:
        return f"<WorkflowRun id={self.id} status={self.status.value}>"


from backend.models.artwork import Artwork  # noqa: E402, F401
