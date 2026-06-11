"""FastAPI dependency injection providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.session import get_db_session
from backend.services.artwork_service import ArtworkService
from backend.services.workflow_service import WorkflowService
from backend.storage.base import StorageBackend
from backend.storage.local import LocalStorageBackend

if TYPE_CHECKING:
    import redis.asyncio as aioredis


def get_redis(request: Request) -> "aioredis.Redis":
    """Retrieve the Redis client from app state."""
    return request.app.state.redis


def get_storage() -> StorageBackend:
    """Return the configured storage backend."""
    return LocalStorageBackend()


def get_artwork_service(
    session: AsyncSession = Depends(get_db_session),
    storage: StorageBackend = Depends(get_storage),
) -> ArtworkService:
    """Provide an ArtworkService instance with injected dependencies."""
    return ArtworkService(session=session, storage=storage)


def get_workflow_service(
    session: AsyncSession = Depends(get_db_session),
) -> WorkflowService:
    """Provide a WorkflowService instance with injected dependencies."""
    return WorkflowService(session=session)


def get_instagram_publisher() -> InstagramPublisher:
    """Provide an InstagramPublisher service instance."""
    from backend.services.instagram_publisher import InstagramPublisher
    return InstagramPublisher()


def get_youtube_publisher() -> YouTubePublisher:
    """Provide a YouTubePublisher service instance."""
    from backend.services.youtube_publisher import YouTubePublisher
    return YouTubePublisher()


def get_instagram_analytics_service() -> InstagramAnalyticsService:
    """Provide an InstagramAnalyticsService instance."""
    from backend.services.instagram_analytics import InstagramAnalyticsService
    return InstagramAnalyticsService()


def get_youtube_analytics_service() -> YouTubeAnalyticsService:
    """Provide a YouTubeAnalyticsService instance."""
    from backend.services.youtube_analytics import YouTubeAnalyticsService
    return YouTubeAnalyticsService()


def get_ai_recommendation_service() -> AIRecommendationService:
    """Provide an AIRecommendationService instance."""
    from backend.services.ai_recommendations import AIRecommendationService
    return AIRecommendationService()
