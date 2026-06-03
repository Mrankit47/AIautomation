"""YouTube-specific Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class YouTubeVideoUpload(BaseModel):
    """YouTube video upload metadata."""

    title: str
    description: str
    tags: list[str] = []
    category_id: str = "22"  # People & Blogs
    privacy_status: str = "public"
    is_short: bool = True


class YouTubeUploadResponse(BaseModel):
    """Response from YouTube video upload."""

    video_id: str
    url: str
    title: str


class YouTubeAnalytics(BaseModel):
    """YouTube video analytics."""

    video_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_minutes: float = 0.0
    collected_at: datetime | None = None
