"""Pinterest-specific Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PinterestPin(BaseModel):
    """Pinterest pin creation payload."""

    title: str
    description: str
    link: str | None = None
    board_id: str
    media_source_url: str


class PinterestPinResponse(BaseModel):
    """Response from Pinterest pin creation."""

    pin_id: str
    url: str
    title: str


class PinterestAnalytics(BaseModel):
    """Pinterest pin analytics."""

    pin_id: str
    impressions: int = 0
    saves: int = 0
    clicks: int = 0
    closeups: int = 0
    collected_at: datetime | None = None
