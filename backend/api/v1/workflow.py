"""Workflow observability API — track and inspect workflow execution.

Provides public endpoints to check workflow progress, event timeline,
and trigger retries — without needing Celery or Flower access.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_active_user
from backend.core.exceptions import NotFoundException
from backend.core.logging import get_logger
from backend.database.repository import BaseRepository
from backend.database.session import get_db_session
from backend.models.user import User
from backend.models.workflow_run import WorkflowRun
from backend.schemas.workflow import (
    WorkflowDetailResponse,
    WorkflowEventResponse,
    WorkflowRetryResponse,
    WorkflowStatusResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow_detail(
    workflow_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> WorkflowDetailResponse:
    """Get comprehensive workflow status with event timeline.

    Returns full workflow details including:
    - Current status and node
    - Start/completion timestamps and duration
    - Publishing statuses per platform
    - Full event timeline (every node execution)
    - Error history
    """
    repo = BaseRepository(WorkflowRun, session)
    run = await repo.get_by_id(workflow_id)
    if run is None:
        raise NotFoundException(
            detail=f"WorkflowRun {workflow_id} not found.",
        )

    # Calculate duration
    duration_seconds = None
    if run.started_at and run.completed_at:
        delta = run.completed_at - run.started_at
        duration_seconds = round(delta.total_seconds(), 2)

    # Build event timeline
    events = [
        WorkflowEventResponse(
            id=event.id,
            node_name=event.node_name,
            event_type=event.event_type,
            started_at=event.started_at,
            completed_at=event.completed_at,
            duration_ms=event.duration_ms,
            error_message=event.error_message,
            attempt_number=event.attempt_number,
            metadata=event.event_metadata,
            created_at=event.created_at,
        )
        for event in (run.events or [])
    ]

    return WorkflowDetailResponse(
        id=run.id,
        artwork_id=run.artwork_id,
        workflow_version=run.workflow_version,
        status=run.status,
        current_node=run.current_node,
        celery_task_id=run.celery_task_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_seconds=duration_seconds,
        error_history=run.error_history,
        error_message=run.error_message,
        instagram_status=run.instagram_status,
        youtube_status=run.youtube_status,
        pinterest_status=run.pinterest_status,
        tiktok_status=run.tiktok_status,
        events=events,
        created_at=run.created_at,
    )


@router.post("/{workflow_id}/retry", response_model=WorkflowRetryResponse, status_code=202)
async def retry_workflow(
    workflow_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> WorkflowRetryResponse:
    """Retry a failed workflow.

    Creates a new workflow run for the same artwork and dispatches
    a fresh Celery task. Only works on FAILED workflows.
    """
    from backend.models.workflow_run import WorkflowStatus
    from backend.tasks.workflow_task import execute_workflow
    from backend.feature_flags.config import get_workflow_version

    repo = BaseRepository(WorkflowRun, session)
    run = await repo.get_by_id(workflow_id)
    if run is None:
        raise NotFoundException(detail=f"WorkflowRun {workflow_id} not found.")

    if run.status != WorkflowStatus.FAILED:
        from backend.core.exceptions import ValidationException
        raise ValidationException(
            detail=f"Cannot retry workflow in '{run.status.value}' status. Only FAILED workflows can be retried.",
        )

    # Create a new workflow run for the same artwork
    version = get_workflow_version()
    new_run = await repo.create(
        artwork_id=run.artwork_id,
        workflow_version=version,
        status=WorkflowStatus.PENDING,
        error_history=[],
    )

    # Dispatch Celery task
    task = execute_workflow.delay(
        str(new_run.id),
        str(run.artwork_id),
        version,
    )

    await repo.update(new_run.id, celery_task_id=task.id)

    logger.info(
        "workflow_retry_triggered",
        original_workflow_id=str(workflow_id),
        new_workflow_run_id=str(new_run.id),
        celery_task_id=task.id,
        artwork_id=str(run.artwork_id),
    )

    return WorkflowRetryResponse(
        original_workflow_id=workflow_id,
        new_workflow_run_id=new_run.id,
        artwork_id=run.artwork_id,
        celery_task_id=task.id,
        status="retrying",
    )
