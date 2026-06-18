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
from backend.schemas.health import (
    HealthReadyResponse,
    HealthResponse,
    ServiceStatus,
    IntegrationsHealthResponse,
    IntegrationStatus,
)

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


@router.get("/integrations", response_model=IntegrationsHealthResponse)
async def check_integrations() -> IntegrationsHealthResponse:
    """Check the health check status of registered integrations (Gemini, Groq, Instagram 1 & 2, YouTube)."""
    import httpx
    from backend.providers.gemini import GeminiProvider
    from backend.providers.groq import GroqProvider
    from backend.services.youtube_publisher import YouTubePublisher
    from backend.integrations.pinterest.client import PinterestClient
    from backend.integrations.tiktok.client import TikTokClient

    settings = get_settings()
    integrations: list[IntegrationStatus] = []

    # 1. Gemini API
    gemini_status = "unhealthy"
    gemini_detail = None
    try:
        gemini_prov = GeminiProvider()
        healthy = await gemini_prov.health_check()
        if healthy:
            gemini_status = "healthy"
        else:
            gemini_detail = "List models query failed."
    except Exception as exc:
        gemini_detail = str(exc)
    integrations.append(IntegrationStatus(name="gemini", status=gemini_status, detail=gemini_detail))

    # 2. Groq API
    groq_status = "unhealthy"
    groq_detail = None
    try:
        groq_prov = GroqProvider()
        healthy = await groq_prov.health_check()
        if healthy:
            groq_status = "healthy"
        else:
            groq_detail = "Ping completion failed."
    except Exception as exc:
        groq_detail = str(exc)
    integrations.append(IntegrationStatus(name="groq", status=groq_status, detail=groq_detail))

    # 3. Instagram Account 1 (Gallery)
    ig_gallery_status = "disabled"
    ig_gallery_detail = None
    access_token = settings.instagram.access_token.get_secret_value() if settings.instagram.access_token else None
    account_id = settings.instagram.account_id or settings.instagram.business_account_id
    if access_token and account_id:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://graph.facebook.com/v19.0/{account_id}",
                    params={"access_token": access_token, "fields": "id,name"},
                )
                if resp.status_code == 200:
                    ig_gallery_status = "healthy"
                else:
                    ig_gallery_status = "unhealthy"
                    ig_gallery_detail = f"API returned {resp.status_code}: {resp.text}"
        except Exception as exc:
            ig_gallery_status = "unhealthy"
            ig_gallery_detail = str(exc)
    else:
        ig_gallery_detail = "Credentials not fully configured."
    integrations.append(IntegrationStatus(name="instagram_gallery", status=ig_gallery_status, detail=ig_gallery_detail))

    # 4. Instagram Account 2 (Photography)
    ig_photo_status = "disabled"
    ig_photo_detail = None
    access_token_acc2 = settings.instagram_acc2.access_token.get_secret_value() if settings.instagram_acc2.access_token else None
    account_id_acc2 = settings.instagram_acc2.account_id or settings.instagram_acc2.business_account_id
    if access_token_acc2 and account_id_acc2:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://graph.facebook.com/v19.0/{account_id_acc2}",
                    params={"access_token": access_token_acc2, "fields": "id,name"},
                )
                if resp.status_code == 200:
                    ig_photo_status = "healthy"
                else:
                    ig_photo_status = "unhealthy"
                    ig_photo_detail = f"API returned {resp.status_code}: {resp.text}"
        except Exception as exc:
            ig_photo_status = "unhealthy"
            ig_photo_detail = str(exc)
    else:
        ig_photo_detail = "Credentials not fully configured."
    integrations.append(IntegrationStatus(name="instagram_photography", status=ig_photo_status, detail=ig_photo_detail))

    # 5. YouTube API
    yt_status = "disabled"
    yt_detail = None
    yt_client_id = settings.youtube.client_id
    yt_client_secret = settings.youtube.client_secret.get_secret_value() if settings.youtube.client_secret else None
    yt_refresh_token = settings.youtube.refresh_token.get_secret_value() if settings.youtube.refresh_token else None
    if yt_client_id and yt_client_secret and yt_refresh_token:
        try:
            publisher = YouTubePublisher()
            async with httpx.AsyncClient(timeout=10.0) as client:
                await publisher._get_access_token(client)
                yt_status = "healthy"
        except Exception as exc:
            yt_status = "unhealthy"
            yt_detail = str(exc)
    else:
        yt_detail = "Credentials not fully configured."
    integrations.append(IntegrationStatus(name="youtube", status=yt_status, detail=yt_detail))

    # 6. Pinterest API
    pinterest_status = "disabled"
    pinterest_detail = None
    pinterest_access_token = settings.pinterest.access_token.get_secret_value() if settings.pinterest.access_token else None
    if pinterest_access_token and settings.pinterest.board_id and settings.pinterest.board_id != "mock-pinterest-board-id":
        try:
            client = PinterestClient()
            healthy = await client.health_check()
            await client.close()
            if healthy:
                pinterest_status = "healthy"
            else:
                pinterest_status = "unhealthy"
                pinterest_detail = "Pinterest health check failed."
        except Exception as exc:
            pinterest_status = "unhealthy"
            pinterest_detail = str(exc)
    else:
        pinterest_detail = "Credentials not fully configured."
    integrations.append(IntegrationStatus(name="pinterest", status=pinterest_status, detail=pinterest_detail))

    # 7. TikTok API
    tiktok_status = "disabled"
    tiktok_detail = None
    tiktok_client_key = settings.tiktok.client_key
    tiktok_client_secret = settings.tiktok.client_secret.get_secret_value() if settings.tiktok.client_secret else None
    tiktok_access_token = settings.tiktok.access_token.get_secret_value() if settings.tiktok.access_token else None
    if tiktok_client_key and tiktok_client_secret and tiktok_access_token and tiktok_client_key != "mock-tiktok-client-key":
        try:
            client = TikTokClient()
            healthy = await client.health_check()
            await client.close()
            if healthy:
                tiktok_status = "healthy"
            else:
                tiktok_status = "unhealthy"
                tiktok_detail = "TikTok health check failed."
        except Exception as exc:
            tiktok_status = "unhealthy"
            tiktok_detail = str(exc)
    else:
        tiktok_detail = "Credentials not fully configured."
    integrations.append(IntegrationStatus(name="tiktok", status=tiktok_status, detail=tiktok_detail))

    # Determine aggregated status
    all_statuses = [i.status for i in integrations]
    if "unhealthy" in all_statuses:
        status = "unhealthy" if all(s == "unhealthy" or s == "disabled" for s in all_statuses if s != "disabled") else "degraded"
    else:
        status = "healthy"

    return IntegrationsHealthResponse(status=status, integrations=integrations)
