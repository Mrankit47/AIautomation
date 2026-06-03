"""Celery worker entry point."""

from backend.core.logging import setup_logging
from backend.tasks.celery_app import celery_app

# Configure structured logging for the worker process
setup_logging(log_level="INFO", json_format=True)

# Export for celery CLI: celery -A backend.workers.celery_worker:app worker
app = celery_app
