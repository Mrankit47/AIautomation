"""YouTube Data API v3 client stub."""

from __future__ import annotations

from typing import Any

import httpx

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.integrations.base import PostAnalytics, PublishResult, SocialMediaClient
from backend.integrations.youtube.exceptions import YouTubeAuthError

logger = get_logger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeClient(SocialMediaClient):
    """YouTube Data API v3 client.

    Note: Publishing logic deferred to social media publishing phase.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client_id = settings.youtube.client_id
        self._client_secret = settings.youtube.client_secret.get_secret_value()
        self._refresh_token = settings.youtube.refresh_token.get_secret_value()
        self._channel_id = settings.youtube.channel_id
        self._http = httpx.AsyncClient(base_url=YOUTUBE_API_BASE, timeout=60.0)

    @property
    def platform_name(self) -> str:
        return "YouTube"

    async def authenticate(self) -> None:
        if not self._client_id:
            raise YouTubeAuthError("YouTube client ID not configured.")
        logger.info("youtube_authenticated")

    async def publish_image(
        self, image_url: str, caption: str, *, hashtags: list[str] | None = None, **kwargs: Any
    ) -> PublishResult:
        raise NotImplementedError("YouTube does not support image-only publishing.")

    async def publish_video(
        self, video_url: str, title: str, description: str, *, hashtags: list[str] | None = None, **kwargs: Any
    ) -> PublishResult:
        raise NotImplementedError("YouTube video publishing — future phase.")

    async def get_post_analytics(self, post_id: str) -> PostAnalytics:
        raise NotImplementedError("YouTube analytics — future phase.")

    async def health_check(self) -> bool:
        try:
            resp = await self._http.get("/channels", params={"part": "id", "mine": "true"})
            return resp.status_code in (200, 401)  # 401 means reachable but needs auth
        except Exception as exc:
            logger.warning("youtube_health_check_failed", error=str(exc))
            return False

    async def close(self) -> None:
        await self._http.aclose()
