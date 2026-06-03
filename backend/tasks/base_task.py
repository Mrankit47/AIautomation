"""Abstract base Celery task with structured logging and retry policy."""

from __future__ import annotations

from typing import Any

import celery
import structlog

from backend.core.logging import task_id_ctx

logger = structlog.get_logger(__name__)


class BaseTask(celery.Task):
    """Abstract base task providing structured logging, retry policies,
    and lifecycle hooks for all Celery tasks.
    """

    abstract = True

    # Retry policy
    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes max backoff
    retry_jitter = True

    def before_start(
        self,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        """Bind task_id to structlog context before execution starts."""
        task_id_ctx.set(task_id)
        logger.info(
            "task_starting",
            task_name=self.name,
            task_id=task_id,
            args=str(args),
        )

    def on_success(
        self,
        retval: Any,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        """Log successful task completion."""
        logger.info(
            "task_succeeded",
            task_name=self.name,
            task_id=task_id,
        )

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        """Log task failure with exception details."""
        logger.error(
            "task_failed",
            task_name=self.name,
            task_id=task_id,
            error_type=type(exc).__name__,
            error_message=str(exc),
            retry_count=self.request.retries if self.request else 0,
        )

    def on_retry(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        """Log task retry."""
        logger.warning(
            "task_retrying",
            task_name=self.name,
            task_id=task_id,
            error_type=type(exc).__name__,
            retry_count=self.request.retries if self.request else 0,
        )
