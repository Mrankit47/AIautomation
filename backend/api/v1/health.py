"""Health-check API endpoints."""

from __future__ import annotations

import time

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_redis
from backend.config.settings import get_settings
from backend.database.session import get_db_session
from backend.schemas.health import HealthReadyResponse, HealthResponse, ServiceStatus

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Liveness probe — returns healthy if the app is running."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
    )


@router.get("/ready", response_model=HealthReadyResponse)
async def readiness(
    session: AsyncSession = Depends(get_db_session),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> HealthReadyResponse:
    """Readiness probe — checks database, Redis, and Celery connectivity."""
    services: list[ServiceStatus] = []

    # ── PostgreSQL ───────────────────────────────────────────────────────
    try:
        start = time.perf_counter()
        await session.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - start) * 1000, 2)
        services.append(
            ServiceStatus(name="postgres", status="healthy", latency_ms=latency)
        )
    except Exception as exc:
        services.append(
            ServiceStatus(name="postgres", status="unhealthy", detail=str(exc))
        )

    # ── Redis ────────────────────────────────────────────────────────────
    try:
        start = time.perf_counter()
        await redis_client.ping()
        latency = round((time.perf_counter() - start) * 1000, 2)
        services.append(
            ServiceStatus(name="redis", status="healthy", latency_ms=latency)
        )
    except Exception as exc:
        services.append(
            ServiceStatus(name="redis", status="unhealthy", detail=str(exc))
        )

    # ── Celery ───────────────────────────────────────────────────────────
    try:
        from backend.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect()
        # Use a short timeout for the ping
        ping_result = inspector.ping()
        if ping_result:
            services.append(
                ServiceStatus(name="celery", status="healthy")
            )
        else:
            services.append(
                ServiceStatus(name="celery", status="unhealthy", detail="No workers responding")
            )
    except Exception as exc:
        services.append(
            ServiceStatus(name="celery", status="unhealthy", detail=str(exc))
        )

    # ── Aggregate Status ─────────────────────────────────────────────────
    all_healthy = all(s.status == "healthy" for s in services)
    any_healthy = any(s.status == "healthy" for s in services)

    if all_healthy:
        overall = "ready"
    elif any_healthy:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return HealthReadyResponse(status=overall, services=services)


@router.get("/workflow")
async def workflow_health(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Workflow health — aggregate stats for the last 24 hours.

    Returns counts of workflows by status, average duration,
    and the last workflow completion time.
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import func, case
    from backend.models.workflow_run import WorkflowRun

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    # Count by status
    result = await session.execute(
        text("""
            SELECT
                status,
                COUNT(*) as count
            FROM workflow_runs
            WHERE created_at >= :cutoff
            GROUP BY status
        """),
        {"cutoff": cutoff},
    )
    status_counts = {row[0]: row[1] for row in result.fetchall()}

    # Average duration of completed workflows
    avg_result = await session.execute(
        text("""
            SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
            FROM workflow_runs
            WHERE status = 'COMPLETED'
            AND started_at IS NOT NULL
            AND completed_at IS NOT NULL
            AND created_at >= :cutoff
        """),
        {"cutoff": cutoff},
    )
    avg_duration = avg_result.scalar()
 
    # Last completion time
    last_result = await session.execute(
        text("""
            SELECT MAX(completed_at)
            FROM workflow_runs
            WHERE status = 'COMPLETED'
        """),
    )
    last_completed = last_result.scalar()

    return {
        "period": "last_24h",
        "total": sum(status_counts.values()),
        "pending": status_counts.get("PENDING", 0),
        "running": status_counts.get("RUNNING", 0),
        "completed": status_counts.get("COMPLETED", 0),
        "failed": status_counts.get("FAILED", 0),
        "average_duration_seconds": round(avg_duration, 2) if avg_duration else None,
        "last_completed_at": last_completed.isoformat() if last_completed else None,
    }
