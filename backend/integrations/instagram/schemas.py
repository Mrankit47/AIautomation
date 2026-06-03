"""Instagram-specific Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class InstagramMediaContainer(BaseModel):
    """Instagram media container for creation."""

    image_url: str
    caption: str
    media_type: str = "IMAGE"


class InstagramMediaResponse(BaseModel):
    """Response from Instagram media creation."""

    id: str
    uri: str | None = None


class InstagramInsights(BaseModel):
    """Instagram post insights."""

    post_id: str
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    saved: int = 0
    shares: int = 0
    collected_at: datetime | None = None
