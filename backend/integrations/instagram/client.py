"""Instagram Graph API client stub."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.integrations.base import PostAnalytics, PublishResult, SocialMediaClient
from backend.integrations.instagram.exceptions import (
    InstagramAPIError,
    InstagramAuthError,
)

logger = get_logger(__name__)

INSTAGRAM_GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class InstagramClient(SocialMediaClient):
    """Instagram Graph API client.

    Note: Publishing logic deferred to social media publishing phase.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._access_token = settings.instagram.access_token.get_secret_value()
        self._account_id = settings.instagram.business_account_id
        self._http = httpx.AsyncClient(
            base_url=INSTAGRAM_GRAPH_API_BASE,
            timeout=30.0,
        )

    @property
    def platform_name(self) -> str:
        return "Instagram"

    async def authenticate(self) -> None:
        if not self._access_token:
            raise InstagramAuthError("Instagram access token not configured.")
        logger.info("instagram_authenticated")

    async def publish_image(
        self,
        image_url: str,
        caption: str,
        *,
        hashtags: list[str] | None = None,
        **kwargs: Any,
    ) -> PublishResult:
        raise NotImplementedError("Instagram image publishing — future phase.")

    async def publish_video(
        self,
        video_url: str,
        title: str,
        description: str,
        *,
        hashtags: list[str] | None = None,
        **kwargs: Any,
    ) -> PublishResult:
        raise NotImplementedError("Instagram video publishing — future phase.")

    async def get_post_analytics(self, post_id: str) -> PostAnalytics:
        raise NotImplementedError("Instagram analytics — future phase.")

    async def health_check(self) -> bool:
        try:
            resp = await self._http.get(
                f"/{self._account_id}",
                params={"access_token": self._access_token, "fields": "id"},
            )
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("instagram_health_check_failed", error=str(exc))
            return False

    async def close(self) -> None:
        await self._http.aclose()
