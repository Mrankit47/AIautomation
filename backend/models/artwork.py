"""Artwork ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin


from sqlalchemy.ext.hybrid import hybrid_property

class ArtworkStatus(str, enum.Enum):
    """Lifecycle status of an artwork through the processing pipeline."""

    UPLOADED = "UPLOADED"
    ANALYZING = "ANALYZING"
    PROCESSING = "PROCESSING"
    PUBLISHING = "PUBLISHING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"

# Validate that all enum values match PostgreSQL native uppercase constraints
for _member in ArtworkStatus:
    if _member.value != _member.value.upper():
        raise ValueError(
            f"ArtworkStatus member '{_member.name}' has non-uppercase value '{_member.value}'. "
            "Values must be uppercase to match PostgreSQL native enum constraints."
        )


# ── Phase 8: Strict State Machine Transitions ────────────────────────────
VALID_STATUS_TRANSITIONS: dict[ArtworkStatus, set[ArtworkStatus]] = {
    ArtworkStatus.UPLOADED: {ArtworkStatus.ANALYZING, ArtworkStatus.FAILED},
    ArtworkStatus.ANALYZING: {ArtworkStatus.PROCESSING, ArtworkStatus.FAILED},
    ArtworkStatus.PROCESSING: {
        ArtworkStatus.PUBLISHING,
        ArtworkStatus.COMPLETED,
        ArtworkStatus.COMPLETED_WITH_WARNINGS,
        ArtworkStatus.FAILED,
    },
    ArtworkStatus.PUBLISHING: {
        ArtworkStatus.COMPLETED,
        ArtworkStatus.COMPLETED_WITH_WARNINGS,
        ArtworkStatus.FAILED,
    },
    ArtworkStatus.COMPLETED: set(),  # Terminal state
    ArtworkStatus.COMPLETED_WITH_WARNINGS: set(),  # Terminal state
    ArtworkStatus.FAILED: {ArtworkStatus.UPLOADED, ArtworkStatus.ANALYZING},  # Allow re-processing or direct retry
}




class Artwork(UUIDMixin, TimestampMixin, Base):
    """Represents an uploaded artwork image and its generated content."""

    __tablename__ = "artworks"

    # ── Original Upload ──────────────────────────────────────────────────
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Processing Status ────────────────────────────────────────────────
    _db_status: Mapped[ArtworkStatus] = mapped_column(
        "status",
        Enum(
            "UPLOADED",
            "ANALYZING",
            "PROCESSING",
            "PUBLISHING",
            "COMPLETED",
            "FAILED",
            name="artwork_status",
            native_enum=True,
            values_callable=lambda x: ["UPLOADED", "ANALYZING", "PROCESSING", "PUBLISHING", "COMPLETED", "FAILED"]
        ),
        default=ArtworkStatus.UPLOADED,
        nullable=False,
    )

    @hybrid_property
    def status(self) -> ArtworkStatus:
        db_status = self._db_status
        if isinstance(db_status, str):
            db_status = ArtworkStatus(db_status)
        if db_status == ArtworkStatus.COMPLETED:
            for run in self.workflow_runs:
                # Normalise string comparison if workflow_run status is string
                run_status = getattr(run, "status", None)
                if isinstance(run_status, str):
                    run_status_str = run_status.upper()
                elif run_status:
                    run_status_str = getattr(run_status, "value", str(run_status)).upper()
                else:
                    run_status_str = ""
                if run_status_str in ("COMPLETED_WITH_WARNINGS", "COMPLETED-WITH-WARNINGS"):
                    return ArtworkStatus.COMPLETED_WITH_WARNINGS
        return db_status

    @status.setter
    def status(self, value: ArtworkStatus) -> None:
        if isinstance(value, str):
            value = ArtworkStatus(value.upper())
        if value == ArtworkStatus.COMPLETED_WITH_WARNINGS:
            self._db_status = ArtworkStatus.COMPLETED
        else:
            self._db_status = value

    # ── AI-Generated Content ─────────────────────────────────────────────
    analysis_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    seo_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    youtube_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    youtube_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Media ────────────────────────────────────────────────────────────
    reel_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reel_script: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Instagram Publishing ─────────────────────────────────────────────
    instagram_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    instagram_post_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    instagram_permalink: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    instagram_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── YouTube Publishing ───────────────────────────────────────────────
    youtube_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    youtube_video_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    youtube_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    youtube_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Error Tracking ───────────────────────────────────────────────────
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Idempotency (Phase 3) ────────────────────────────────────────────
    image_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True,
        comment="SHA-256 hash of file bytes for duplicate detection",
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True,
        comment="Original URL if ingested via webhook",
    )

    # ── Relationships ────────────────────────────────────────────────────
    workflow_runs: Mapped[list["WorkflowRun"]] = relationship(
        "WorkflowRun",
        back_populates="artwork",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    analytics: Mapped[list["ArtworkAnalytics"]] = relationship(
        "ArtworkAnalytics",
        back_populates="artwork",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ── Phase 8: State Machine ────────────────────────────────────────────

    def transition_to(self, new_status: ArtworkStatus) -> None:
        """Enforce strict status lifecycle transitions.

        Args:
            new_status: The status to transition to.

        Raises:
            WorkflowException: If the transition is invalid.
        """
        from backend.core.exceptions import WorkflowException

        current = self.status
        if current == new_status:
            return

        allowed = VALID_STATUS_TRANSITIONS.get(current, set())

        if new_status not in allowed:
            raise WorkflowException(
                detail=(
                    f"Invalid status transition: {current.value} → {new_status.value}. "
                    f"Allowed transitions from {current.value}: "
                    f"{', '.join(s.value for s in allowed) or 'none (terminal state)'}."
                ),
                context={
                    "artwork_id": str(self.id),
                    "current_status": current.value,
                    "requested_status": new_status.value,
                },
            )

        self.status = new_status

    def __repr__(self) -> str:
        return f"<Artwork id={self.id} status={self.status.value}>"


# Avoid circular import — WorkflowRun is imported for type checking only.
from backend.models.workflow_run import WorkflowRun  # noqa: E402, F401
from backend.models.analytics import ArtworkAnalytics  # noqa: E402, F401
