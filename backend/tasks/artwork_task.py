"""Artwork processing Celery task."""

from __future__ import annotations

from backend.core.logging import artwork_id_ctx, get_logger
from backend.tasks.base_task import BaseTask
from backend.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="backend.tasks.artwork_task.process_artwork",
    queue="artwork",
)
def process_artwork(self: BaseTask, artwork_id: str) -> dict[str, str]:
    """Process an uploaded artwork through the initial analysis pipeline.

    This task is dispatched when a new artwork is uploaded.  It binds the
    artwork_id to the structlog context for correlation.

    Args:
        artwork_id: UUID string of the artwork to process.

    Returns:
        Status dict with the result.

    Note: Full implementation deferred to AI prompts phase.
    """
    artwork_id_ctx.set(artwork_id)
    logger.info("process_artwork_started", artwork_id=artwork_id)

    # Stub — will:
    # 1. Load artwork from database
    # 2. Read image from storage
    # 3. Run analysis via AIProvider
    # 4. Update artwork record with results
    # 5. Dispatch workflow_task if successful

    logger.info("process_artwork_completed", artwork_id=artwork_id)
    return {"status": "completed", "artwork_id": artwork_id}
