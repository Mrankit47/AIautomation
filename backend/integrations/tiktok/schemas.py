"""TikTok-specific Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TikTokVideoUpload(BaseModel):
    """TikTok video upload metadata."""

    title: str
    description: str
    privacy_level: str = "PUBLIC_TO_EVERYONE"
    disable_comment: bool = False
    disable_duet: bool = False
    disable_stitch: bool = False


class TikTokUploadResponse(BaseModel):
    """Response from TikTok video upload."""

    publish_id: str
    upload_url: str | None = None


class TikTokAnalytics(BaseModel):
    """TikTok video analytics."""

    video_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    collected_at: datetime | None = None
