"""Artwork API endpoints — upload, retrieve, list, and trigger processing."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile

from backend.api.deps import get_artwork_service, get_workflow_service
from backend.auth.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.artwork import ArtworkListResponse, ArtworkResponse
from backend.schemas.workflow import (
    WorkflowStatusResponse,
    WorkflowTriggerRequest,
    WorkflowTriggerResponse,
)
from backend.services.artwork_service import ArtworkService
from backend.services.workflow_service import WorkflowService

router = APIRouter(prefix="/artworks", tags=["artworks"])


@router.post("/upload", response_model=ArtworkResponse, status_code=201)
async def upload_artwork(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> ArtworkResponse:
    """Upload a new artwork image."""
    file_data = await file.read()
    return await service.upload_artwork(
        file_data=file_data,
        filename=file.filename or "untitled.png",
        content_type=file.content_type or "application/octet-stream",
        title=title,
    )


@router.get("", response_model=ArtworkListResponse)
async def list_artworks(
    page: int = 1,
    per_page: int = 20,
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> ArtworkListResponse:
    """List all artworks with pagination."""
    return await service.list_artworks(page=page, per_page=per_page)


@router.get("/{artwork_id}", response_model=ArtworkResponse)
async def get_artwork(
    artwork_id: uuid.UUID,
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> ArtworkResponse:
    """Retrieve a single artwork by ID."""
    return await service.get_artwork(artwork_id)


@router.post(
    "/{artwork_id}/process",
    response_model=WorkflowTriggerResponse,
    status_code=202,
)
async def trigger_processing(
    artwork_id: uuid.UUID,
    body: WorkflowTriggerRequest | None = None,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    current_user: User = Depends(get_current_active_user),
) -> WorkflowTriggerResponse:
    """Trigger the AI processing workflow for an artwork.

    Dispatches a Celery task and returns immediately with the task ID.
    """
    version = body.workflow_version if body else "v1"
    return await workflow_service.trigger_workflow(
        artwork_id=artwork_id,
        workflow_version=version,
    )


@router.get(
    "/{artwork_id}/workflow/{workflow_run_id}",
    response_model=WorkflowStatusResponse,
)
async def get_workflow_status(
    artwork_id: uuid.UUID,
    workflow_run_id: uuid.UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    current_user: User = Depends(get_current_active_user),
) -> WorkflowStatusResponse:
    """Get the status of a specific workflow run."""
    return await workflow_service.get_workflow_status(workflow_run_id)
