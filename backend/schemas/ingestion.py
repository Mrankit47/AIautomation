"""Pydantic schemas for the artwork ingestion webhook endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, HttpUrl


class IngestionRequest(BaseModel):
    """Request body for ingesting an artwork from a URL.

    This is the payload that external systems (e.g., an art website)
    will send to trigger the full autonomous pipeline.
    """

    title: str
    image_url: HttpUrl
    source: str = "webhook"
    category: str = "gallery"


class IngestionResponse(BaseModel):
    """Response after accepting an artwork for ingestion."""

    artwork_id: uuid.UUID
    workflow_run_id: uuid.UUID | None = None
    celery_task_id: str | None = None
    status: str = "accepted"
    message: str = "Artwork accepted for processing."
    duplicate: bool = False
