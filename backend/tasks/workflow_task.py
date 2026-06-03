"""Workflow orchestration Celery task."""

from __future__ import annotations

from backend.core.logging import artwork_id_ctx, get_logger, workflow_id_ctx
from backend.tasks.base_task import BaseTask
from backend.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="backend.tasks.workflow_task.execute_workflow",
    queue="workflow",
)
def execute_workflow(
    self: BaseTask,
    artwork_id: str,
    workflow_version: str = "v1",
) -> dict[str, str]:
    """Execute the full artwork processing workflow via LangGraph.

    This task runs the LangGraph workflow which orchestrates:
    analysis → metadata → SEO → caption → hashtags → reel → publish → analytics.

    Args:
        artwork_id: UUID string of the artwork.
        workflow_version: Version of the workflow to execute (e.g., 'v1', 'v2').

    Returns:
        Status dict with the workflow result.

    Note: Full implementation deferred to AI prompts phase.
    """
    artwork_id_ctx.set(artwork_id)
    workflow_id_ctx.set(f"wf-{artwork_id[:8]}")

    logger.info(
        "execute_workflow_started",
        artwork_id=artwork_id,
        workflow_version=workflow_version,
    )

    # Stub — will:
    # 1. Create WorkflowRun record
    # 2. Load the appropriate workflow version
    # 3. Build initial state
    # 4. Invoke compiled LangGraph workflow
    # 5. Update WorkflowRun with results

    logger.info(
        "execute_workflow_completed",
        artwork_id=artwork_id,
        workflow_version=workflow_version,
    )
    return {
        "status": "completed",
        "artwork_id": artwork_id,
        "workflow_version": workflow_version,
    }
