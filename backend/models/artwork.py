"""Artwork ORM model."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin


class ArtworkStatus(str, enum.Enum):
    """Lifecycle status of an artwork through the processing pipeline."""

    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    PROCESSING = "processing"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"


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
    status: Mapped[ArtworkStatus] = mapped_column(
        Enum(ArtworkStatus, name="artwork_status", create_constraint=True),
        default=ArtworkStatus.UPLOADED,
        nullable=False,
    )

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

    # ── Error Tracking ───────────────────────────────────────────────────
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    workflow_runs: Mapped[list["WorkflowRun"]] = relationship(
        "WorkflowRun",
        back_populates="artwork",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Artwork id={self.id} status={self.status.value}>"


# Avoid circular import — WorkflowRun is imported for type checking only.
from backend.models.workflow_run import WorkflowRun  # noqa: E402, F401
