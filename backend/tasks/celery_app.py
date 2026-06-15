"""Celery application factory and configuration."""

from __future__ import annotations

from celery import Celery

from backend.config.settings import get_settings


def create_celery_app() -> Celery:
    """Create and configure the Celery application.

    Uses Redis as both broker and result backend.
    Tasks are routed to dedicated queues for workload isolation.
    """
    settings = get_settings()

    app = Celery(
        "artwork_automation",
        include=[
            "backend.tasks.artwork_task",
            "backend.tasks.workflow_task",
            "backend.tasks.analytics_task",
        ],
    )

    app.conf.update(
        # Broker & Backend
        broker_url=settings.celery.broker_url,
        result_backend=settings.celery.result_backend,
        # Serialization
        task_serializer=settings.celery.task_serializer,
        result_serializer=settings.celery.result_serializer,
        accept_content=settings.celery.accept_content,
        # Reliability & Process Recycling
        task_track_started=settings.celery.task_track_started,
        task_acks_late=settings.celery.task_acks_late,
        worker_prefetch_multiplier=settings.celery.worker_prefetch_multiplier,
        worker_max_tasks_per_child=1,
        worker_max_memory_per_child=250000, # 250MB limit to release memory leaks
        # Timeouts
        task_soft_time_limit=600,   # 10 minutes soft limit
        task_time_limit=900,        # 15 minutes hard limit
        result_expires=86400,       # Results expire after 24 hours
        # Queue Routing
        task_routes={
            "backend.tasks.artwork_task.*": {"queue": "artwork"},
            "backend.tasks.workflow_task.*": {"queue": "workflow"},
            "backend.tasks.analytics_task.*": {"queue": "workflow"},
        },
        # Default queue
        task_default_queue="default",
        # Celery Beat Periodic Schedule
        beat_schedule={
            "collect-analytics-daily": {
                "task": "backend.tasks.analytics_task.collect_analytics_daily",
                "schedule": 86400.0,  # Run every 24 hours (daily)
            }
        },
    )

    # Auto-discover tasks in the backend.tasks package
    app.autodiscover_tasks(["backend.tasks"])

    return app


# Module-level singleton
celery_app = create_celery_app()
