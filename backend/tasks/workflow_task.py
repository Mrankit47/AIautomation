"""Workflow orchestration Celery task.

Updates WorkflowRun status in PostgreSQL as the task progresses:
  PENDING → RUNNING → COMPLETED | FAILED

Uses a synchronous SQLAlchemy engine (psycopg2) because Celery workers
run in synchronous prefork processes — async engines (asyncpg) cannot be
safely shared across multiple asyncio.run() calls.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import get_settings
from backend.core.logging import artwork_id_ctx, get_logger, workflow_id_ctx
from backend.models.workflow_run import WorkflowRun, WorkflowStatus
from backend.tasks.base_task import BaseTask
from backend.tasks.celery_app import celery_app

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Synchronous DB session for the Celery worker process.
#
# We use psycopg2 (sync) instead of asyncpg because Celery workers are
# synchronous prefork processes.  The sync_url property on DatabaseSettings
# returns a postgresql+psycopg2:// URL which is exactly what we need.
# ---------------------------------------------------------------------------

from backend.database.session import get_sync_session

# Use the centralized get_sync_session helper
_get_sync_session = get_sync_session


# ---------------------------------------------------------------------------
# Database update helpers
# ---------------------------------------------------------------------------


def _mark_running(workflow_run_id: uuid.UUID) -> None:
    """Set WorkflowRun status to RUNNING and record started_at."""
    session = _get_sync_session()
    try:
        run = session.execute(
            select(WorkflowRun).where(WorkflowRun.id == workflow_run_id)
        ).scalar_one_or_none()

        if run is None:
            logger.error(
                "workflow_run_not_found",
                workflow_run_id=str(workflow_run_id),
            )
            return

        run.status = WorkflowStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _mark_completed(
    workflow_run_id: uuid.UUID,
    result_data: dict,
    status: str = "COMPLETED",
) -> None:
    """Set WorkflowRun status with result payload."""
    session = _get_sync_session()
    try:
        run = session.execute(
            select(WorkflowRun).where(WorkflowRun.id == workflow_run_id)
        ).scalar_one_or_none()

        if run is None:
            logger.error(
                "workflow_run_not_found",
                workflow_run_id=str(workflow_run_id),
            )
            return

        from backend.models.workflow_run import WorkflowStatus
        from backend.models.artwork import ArtworkStatus
        
        if status.upper() == "COMPLETED_WITH_WARNINGS":
            run.status = WorkflowStatus.COMPLETED_WITH_WARNINGS
            art_status = ArtworkStatus.COMPLETED_WITH_WARNINGS
        else:
            run.status = WorkflowStatus.COMPLETED
            art_status = ArtworkStatus.COMPLETED
            
        run.completed_at = datetime.now(timezone.utc)
        run.result = result_data
        
        if run.artwork and run.artwork.status not in (ArtworkStatus.COMPLETED, ArtworkStatus.COMPLETED_WITH_WARNINGS, ArtworkStatus.FAILED):
            try:
                run.artwork.transition_to(art_status)
                run.artwork.error_message = None  # Clear previous error message
            except Exception as e:
                logger.error(
                    "failed_to_transition_artwork_status",
                    workflow_run_id=str(workflow_run_id),
                    artwork_id=str(run.artwork.id),
                    current_status=run.artwork.status.value,
                    target_status=art_status.value,
                    error=str(e),
                )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _mark_failed(
    workflow_run_id: uuid.UUID,
    error: str,
) -> None:
    """Set WorkflowRun status to FAILED with error details."""
    session = _get_sync_session()
    try:
        run = session.execute(
            select(WorkflowRun).where(WorkflowRun.id == workflow_run_id)
        ).scalar_one_or_none()

        if run is None:
            logger.error(
                "workflow_run_not_found",
                workflow_run_id=str(workflow_run_id),
            )
            return

        from backend.models.artwork import ArtworkStatus
        run.status = WorkflowStatus.FAILED
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = error
        
        if run.artwork and run.artwork.status not in (ArtworkStatus.COMPLETED, ArtworkStatus.COMPLETED_WITH_WARNINGS, ArtworkStatus.FAILED):
            try:
                run.artwork.transition_to(ArtworkStatus.FAILED)
                if not run.artwork.error_message:
                    run.artwork.error_message = error
            except Exception as e:
                logger.error(
                    "failed_to_transition_artwork_status",
                    workflow_run_id=str(workflow_run_id),
                    artwork_id=str(run.artwork.id),
                    current_status=run.artwork.status.value,
                    target_status="FAILED",
                    error=str(e),
                )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="backend.tasks.workflow_task.execute_workflow",
    queue="workflow",
    autoretry_for=(),       # Disable auto-retry from BaseTask for this task;
    max_retries=0,          # we handle errors ourselves to update DB status.
)
def execute_workflow(
    self: BaseTask,
    workflow_run_id: str,
    artwork_id: str,
    workflow_version: str = "v1",
) -> dict[str, str]:
    """Execute the full artwork processing workflow.

    This task:
    1. Marks the WorkflowRun as RUNNING.
    2. Executes the workflow logic (stub for now).
    3. Marks the WorkflowRun as COMPLETED on success, FAILED on error.

    Args:
        workflow_run_id: UUID string of the WorkflowRun record.
        artwork_id: UUID string of the artwork.
        workflow_version: Version of the workflow to execute (e.g., 'v1').

    Returns:
        Status dict with the workflow result.
    """
    run_uuid = uuid.UUID(workflow_run_id)

    # Bind structured-logging context
    artwork_id_ctx.set(artwork_id)
    workflow_id_ctx.set(f"wf-{artwork_id[:8]}")

    logger.info(
        "execute_workflow_started",
        workflow_run_id=workflow_run_id,
        artwork_id=artwork_id,
        workflow_version=workflow_version,
    )

    # ── 1. Mark RUNNING ──────────────────────────────────────────────────
    _mark_running(run_uuid)

    try:
        # ── 2. Load artwork details ──────────────────────────────────────
        from backend.models.artwork import Artwork
        session = _get_sync_session()
        try:
            artwork = session.execute(
                select(Artwork).where(Artwork.id == uuid.UUID(artwork_id))
            ).scalar_one_or_none()

            if artwork is None:
                raise ValueError(f"Artwork not found: {artwork_id}")

            initial_state = {
                "artwork_id": artwork_id,
                "workflow_id": workflow_run_id,
                "workflow_version": workflow_version,
                "image_path": artwork.file_path,
                "storage_url": artwork.storage_url or "",
                "original_filename": artwork.original_filename,
                "analysis": None,
                "metadata": None,
                "seo": None,
                "caption": None,
                "hashtags": None,
                "youtube_title": None,
                "youtube_description": None,
                "reel_script": None,
                "reel_path": artwork.reel_path,
                "instagram_status": None,
                "youtube_status": None,
                "pinterest_status": None,
                "tiktok_status": None,
                "workflow_status": "RUNNING",
                "current_node": "start",
                "error_history": [],
                "messages": [],
            }
        finally:
            session.close()

        # ── 3. Invoke LangGraph Workflow ─────────────────────────────────
        import asyncio
        from backend.graph.workflow import compile_artwork_workflow

        logger.info(
            "execute_workflow_processing",
            workflow_run_id=workflow_run_id,
            artwork_id=artwork_id,
            workflow_version=workflow_version,
        )

        compiled_graph = compile_artwork_workflow()
        final_state = asyncio.run(compiled_graph.ainvoke(initial_state))

        # Check if the workflow ended in a failed state
        state_status = final_state.get("workflow_status")
        if state_status and state_status.upper() == "FAILED":
            error_msg = f"Workflow failed in node: {final_state.get('current_node', 'unknown')}"
            if final_state.get("error_history"):
                error_msg = final_state["error_history"][-1].get("message", error_msg)
            raise RuntimeError(error_msg)

        # ── 4. Mark COMPLETED ────────────────────────────────────────────
        workflow_status = final_state.get("workflow_status", "COMPLETED")
        result_data = {
            "status": workflow_status,
            "artwork_id": artwork_id,
            "workflow_version": workflow_version,
            "analysis": final_state.get("analysis"),
            "metadata": final_state.get("metadata"),
            "seo": final_state.get("seo"),
            "caption": final_state.get("caption"),
            "hashtags": final_state.get("hashtags"),
            "reel_script": final_state.get("reel_script"),
            "reel_path": final_state.get("reel_path"),
        }

        _mark_completed(run_uuid, result_data, status=workflow_status)

        logger.info(
            "execute_workflow_completed",
            workflow_run_id=workflow_run_id,
            artwork_id=artwork_id,
            workflow_version=workflow_version,
        )
        return result_data

    except Exception as exc:
        # ── 5. Mark FAILED ───────────────────────────────────────────────
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.error(
            "execute_workflow_failed",
            workflow_run_id=workflow_run_id,
            artwork_id=artwork_id,
            error=error_msg,
        )
        _mark_failed(run_uuid, error_msg)
        raise
