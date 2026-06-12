"""Pydantic schemas for workflow API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from backend.models.workflow_run import WorkflowStatus


class WorkflowTriggerRequest(BaseModel):
    """Request to trigger a workflow for an artwork."""

    workflow_version: str = "v1"


class WorkflowTriggerResponse(BaseModel):
    """Response after triggering a workflow."""

    workflow_run_id: uuid.UUID
    artwork_id: uuid.UUID
    celery_task_id: str
    workflow_version: str
    status: str = "PENDING"


class WorkflowStatusResponse(BaseModel):
    """Current status of a workflow run."""

    id: uuid.UUID
    artwork_id: uuid.UUID
    workflow_version: str
    status: WorkflowStatus
    current_node: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error_history: list[dict[str, Any]] | None = None
    instagram_status: str | None
    youtube_status: str | None
    pinterest_status: str | None
    tiktok_status: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
