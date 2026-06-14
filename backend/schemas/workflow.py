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


# ── Phase 4: Observability Schemas ───────────────────────────────────────


class WorkflowEventResponse(BaseModel):
    """A single node execution event within a workflow."""

    id: uuid.UUID
    node_name: str
    event_type: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    error_message: str | None = None
    attempt_number: int = 1
    metadata: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowDetailResponse(BaseModel):
    """Comprehensive workflow status with event timeline."""

    id: uuid.UUID
    artwork_id: uuid.UUID
    workflow_version: str
    status: WorkflowStatus
    current_node: str | None
    celery_task_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None = None
    error_history: list[dict[str, Any]] | None = None
    error_message: str | None = None
    instagram_status: str | None
    youtube_status: str | None
    pinterest_status: str | None
    tiktok_status: str | None
    events: list[WorkflowEventResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Phase 6: Retry Schemas ───────────────────────────────────────────────


class WorkflowRetryResponse(BaseModel):
    """Response after triggering a workflow retry."""

    original_workflow_id: uuid.UUID
    new_workflow_run_id: uuid.UUID
    artwork_id: uuid.UUID
    celery_task_id: str
    status: str = "retrying"
