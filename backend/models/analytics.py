"""ArtworkAnalytics ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin


class ArtworkAnalytics(UUIDMixin, TimestampMixin, Base):
    """Represents historical/daily analytics metrics collected for an artwork on a platform."""

    __tablename__ = "artwork_analytics"

    artwork_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artworks.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # "instagram" or "youtube"

    # Platform metrics
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    watch_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # in minutes (YouTube)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    artwork: Mapped["Artwork"] = relationship("Artwork", back_populates="analytics")

    def __repr__(self) -> str:
        return f"<ArtworkAnalytics id={self.id} platform={self.platform} artwork_id={self.artwork_id}>"


# Avoid circular import
from backend.models.artwork import Artwork  # noqa: E402
