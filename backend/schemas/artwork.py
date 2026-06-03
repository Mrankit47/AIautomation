"""Pydantic schemas for artwork API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.models.artwork import ArtworkStatus


class ArtworkCreate(BaseModel):
    """Schema for artwork upload metadata (file is sent as multipart)."""

    title: str | None = None


class ArtworkResponse(BaseModel):
    """Public artwork representation."""

    id: uuid.UUID
    title: str | None
    original_filename: str
    file_path: str
    storage_url: str | None
    file_size: int
    mime_type: str
    width: int | None
    height: int | None
    status: ArtworkStatus
    analysis_data: dict[str, Any] | None = None
    seo_data: dict[str, Any] | None = None
    caption: str | None = None
    hashtags: list[str] | None = None
    youtube_title: str | None = None
    youtube_description: str | None = None
    reel_path: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArtworkListResponse(BaseModel):
    """Paginated list of artworks."""

    items: list[ArtworkResponse]
    total: int
    page: int
    per_page: int
    pages: int
