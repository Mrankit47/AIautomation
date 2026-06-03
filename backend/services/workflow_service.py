"""Workflow service — orchestrates workflow execution via Celery."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import NotFoundException, WorkflowException
from backend.core.logging import get_logger
from backend.database.repository import BaseRepository
from backend.feature_flags.config import get_workflow_version
from backend.models.artwork import Artwork
from backend.models.workflow_run import WorkflowRun, WorkflowStatus
from backend.schemas.workflow import WorkflowStatusResponse, WorkflowTriggerResponse
from backend.tasks.workflow_task import execute_workflow

logger = get_logger(__name__)


class WorkflowService:
    """Orchestrates artwork workflow execution via Celery tasks."""

    def __init__(self, session: AsyncSession) -> None:
        self._artwork_repo = BaseRepository(Artwork, session)
        self._workflow_repo = BaseRepository(WorkflowRun, session)
        self._session = session

    async def trigger_workflow(
        self,
        artwork_id: uuid.UUID,
        workflow_version: str | None = None,
    ) -> WorkflowTriggerResponse:
        """Trigger the processing workflow for an artwork.

        Creates a WorkflowRun record and dispatches a Celery task.

        Args:
            artwork_id: UUID of the artwork to process.
            workflow_version: Override the default workflow version.

        Returns:
            WorkflowTriggerResponse with the task ID and run ID.

        Raises:
            NotFoundException: If the artwork does not exist.
            WorkflowException: If a workflow is already running for this artwork.
        """
        # Verify artwork exists
        artwork = await self._artwork_repo.get_by_id(artwork_id)
        if artwork is None:
            raise NotFoundException(detail=f"Artwork {artwork_id} not found.")

        # Check for active workflows
        active_runs = await self._workflow_repo.filter_by(
            artwork_id=artwork_id, status=WorkflowStatus.RUNNING
        )
        if active_runs:
            raise WorkflowException(
                detail="A workflow is already running for this artwork.",
                context={"artwork_id": str(artwork_id)},
            )

        version = workflow_version or get_workflow_version()

        # Create workflow run record
        workflow_run = await self._workflow_repo.create(
            artwork_id=artwork_id,
            workflow_version=version,
            status=WorkflowStatus.PENDING,
            error_history=[],
        )

        # Dispatch Celery task
        task = execute_workflow.delay(str(artwork_id), version)

        # Update run with task ID
        await self._workflow_repo.update(
            workflow_run.id,
            celery_task_id=task.id,
        )

        logger.info(
            "workflow_triggered",
            artwork_id=str(artwork_id),
            workflow_run_id=str(workflow_run.id),
            celery_task_id=task.id,
            workflow_version=version,
        )

        return WorkflowTriggerResponse(
            workflow_run_id=workflow_run.id,
            artwork_id=artwork_id,
            celery_task_id=task.id,
            workflow_version=version,
            status="pending",
        )

    async def get_workflow_status(
        self,
        workflow_run_id: uuid.UUID,
    ) -> WorkflowStatusResponse:
        """Retrieve the current status of a workflow run.

        Raises:
            NotFoundException: If the workflow run does not exist.
        """
        run = await self._workflow_repo.get_by_id(workflow_run_id)
        if run is None:
            raise NotFoundException(
                detail=f"WorkflowRun {workflow_run_id} not found."
            )
        return WorkflowStatusResponse.model_validate(run)
