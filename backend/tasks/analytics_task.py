"""Celery tasks for analytics collection."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select

from backend.core.logging import get_logger
from backend.database.session import get_sync_session
from backend.models.artwork import Artwork
from backend.models.analytics import ArtworkAnalytics
from backend.tasks.base_task import BaseTask
from backend.tasks.celery_app import celery_app

logger = get_logger(__name__)


async def _collect_metrics_async(
    artwork_id: uuid.UUID,
    instagram_post_id: str | None,
    youtube_video_id: str | None,
    youtube_published_at: datetime | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Asynchronously trigger metrics collection for Instagram and YouTube."""
    ig_metrics = None
    yt_metrics = None

    # Instagram
    if instagram_post_id:
        try:
            from backend.services.instagram_analytics import InstagramAnalyticsService
            ig_service = InstagramAnalyticsService()
            ig_metrics = await ig_service.collect_metrics(instagram_post_id)
        except Exception as e:
            logger.warning("instagram_analytics_periodic_collection_failed", artwork_id=str(artwork_id), error=str(e))

    # YouTube
    if youtube_video_id:
        try:
            from backend.services.youtube_analytics import YouTubeAnalyticsService
            yt_service = YouTubeAnalyticsService()
            yt_metrics = await yt_service.collect_metrics(youtube_video_id, youtube_published_at)
        except Exception as e:
            logger.warning("youtube_analytics_periodic_collection_failed", artwork_id=str(artwork_id), error=str(e))

    return ig_metrics, yt_metrics


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="backend.tasks.analytics_task.collect_analytics_daily",
    queue="workflow",  # Route to workflow queue so the active worker executes it
)
def collect_analytics_daily(self: BaseTask) -> dict[str, Any]:
    """Daily Celery task to collect performance metrics for all published artworks."""
    logger.info("periodic_analytics_collection_started")

    # 1. Open sync DB session
    session = get_sync_session()
    try:
        # Query all artworks with at least one platform published
        stmt = select(Artwork).where(
            (Artwork.instagram_status == "published") | (Artwork.youtube_status == "published")
        )
        artworks = session.execute(stmt).scalars().all()
        logger.info("periodic_analytics_collection_found_artworks", count=len(artworks))

        for art in artworks:
            # 2. Asynchronously run collection APIs using asyncio.run
            # Celery workers run in sync prefork pools, so we use asyncio.run
            ig_metrics, yt_metrics = asyncio.run(
                _collect_metrics_async(
                    art.id,
                    art.instagram_post_id if art.instagram_status == "published" else None,
                    art.youtube_video_id if art.youtube_status == "published" else None,
                    art.youtube_published_at,
                )
            )

            # 3. Create database records in our sync session
            if ig_metrics:
                ig_analytics = ArtworkAnalytics(
                    artwork_id=art.id,
                    platform="instagram",
                    views=ig_metrics["views"],
                    reach=ig_metrics["reach"],
                    impressions=ig_metrics["impressions"],
                    likes=ig_metrics["likes"],
                    comments=ig_metrics["comments"],
                    shares=ig_metrics["shares"],
                    saves=ig_metrics["saves"],
                    watch_time=ig_metrics["watch_time"],
                    engagement_rate=ig_metrics["engagement_rate"],
                    collected_at=ig_metrics["collected_at"],
                )
                session.add(ig_analytics)

            if yt_metrics:
                yt_analytics = ArtworkAnalytics(
                    artwork_id=art.id,
                    platform="youtube",
                    views=yt_metrics["views"],
                    reach=yt_metrics["reach"],
                    impressions=yt_metrics["impressions"],
                    likes=yt_metrics["likes"],
                    comments=yt_metrics["comments"],
                    shares=yt_metrics["shares"],
                    saves=yt_metrics["saves"],
                    watch_time=yt_metrics["watch_time"],
                    engagement_rate=yt_metrics["engagement_rate"],
                    collected_at=yt_metrics["collected_at"],
                )
                session.add(yt_analytics)

        session.commit()
        logger.info("periodic_analytics_collection_completed_successfully")
        return {"status": "success", "processed_artworks_count": len(artworks)}
    except Exception as exc:
        logger.error("periodic_analytics_collection_failed", error=str(exc))
        session.rollback()
        raise
    finally:
        session.close()
