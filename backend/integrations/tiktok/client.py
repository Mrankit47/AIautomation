"""TikTok Content Posting API client stub."""

from __future__ import annotations

from typing import Any

import httpx

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.integrations.base import PostAnalytics, PublishResult, SocialMediaClient
from backend.integrations.tiktok.exceptions import TikTokAuthError

logger = get_logger(__name__)

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"


class TikTokClient(SocialMediaClient):
    """TikTok Content Posting API client.

    Note: Publishing logic deferred to social media publishing phase.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client_key = settings.tiktok.client_key
        self._client_secret = settings.tiktok.client_secret.get_secret_value()
        self._access_token = settings.tiktok.access_token.get_secret_value()
        self._http = httpx.AsyncClient(
            base_url=TIKTOK_API_BASE,
            headers={"Authorization": f"Bearer {self._access_token}"},
            timeout=60.0,
        )

    @property
    def platform_name(self) -> str:
        return "TikTok"

    async def authenticate(self) -> None:
        if not self._client_key:
            raise TikTokAuthError("TikTok client key not configured.")
        logger.info("tiktok_authenticated")

    async def publish_image(
        self, image_url: str, caption: str, *, hashtags: list[str] | None = None, **kwargs: Any
    ) -> PublishResult:
        raise NotImplementedError("TikTok image publishing — future phase.")

    async def publish_video(
        self, video_url: str, title: str, description: str, *, hashtags: list[str] | None = None, **kwargs: Any
    ) -> PublishResult:
        raise NotImplementedError("TikTok video publishing — future phase.")

    async def get_post_analytics(self, post_id: str) -> PostAnalytics:
        raise NotImplementedError("TikTok analytics — future phase.")

    async def health_check(self) -> bool:
        try:
            resp = await self._http.get("/user/info/")
            return resp.status_code in (200, 401)
        except Exception as exc:
            logger.warning("tiktok_health_check_failed", error=str(exc))
            return False

    async def close(self) -> None:
        await self._http.aclose()
