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
