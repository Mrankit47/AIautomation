"""Structured JSON logging via structlog.

Supports correlation_id, workflow_id, request_id, artwork_id, and task_id
bound via contextvars so they propagate across async boundaries automatically.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

# ── Context Variables ────────────────────────────────────────────────────────
# These are bound in middleware / task hooks and automatically merged into logs.

correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
workflow_id_ctx: ContextVar[str | None] = ContextVar("workflow_id", default=None)
artwork_id_ctx: ContextVar[str | None] = ContextVar("artwork_id", default=None)
task_id_ctx: ContextVar[str | None] = ContextVar("task_id", default=None)


def _inject_context_vars(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Processor that injects all context variables into every log entry."""
    ctx_mapping: dict[str, ContextVar[str | None]] = {
        "correlation_id": correlation_id_ctx,
        "request_id": request_id_ctx,
        "workflow_id": workflow_id_ctx,
        "artwork_id": artwork_id_ctx,
        "task_id": task_id_ctx,
    }
    for key, ctx_var in ctx_mapping.items():
        value = ctx_var.get()
        if value is not None:
            event_dict[key] = value
    return event_dict


def setup_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    """Configure structlog and stdlib logging for the application.

    Args:
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: If True, output JSON lines (production). Otherwise,
                     use coloured console output (development).
    """
    log_level_upper = log_level.upper()
    numeric_level = getattr(logging, log_level_upper, logging.INFO)

    # Shared processors (run before the final renderer)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _inject_context_vars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_format:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.ExceptionPrettyPrinter(),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
        force=True,
    )

    # Silence noisy third-party loggers
    for noisy_logger in ("uvicorn.access", "sqlalchemy.engine", "celery"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger, optionally bound to a module name."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger()
    if name:
        logger = logger.bind(module=name)
    return logger
