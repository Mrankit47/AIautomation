"""Pinterest API v5 client stub."""

from __future__ import annotations

from typing import Any

import httpx

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.integrations.base import PostAnalytics, PublishResult, SocialMediaClient
from backend.integrations.pinterest.exceptions import PinterestAuthError

logger = get_logger(__name__)

PINTEREST_API_BASE = "https://api.pinterest.com/v5"


class PinterestClient(SocialMediaClient):
    """Pinterest API v5 client.

    Note: Publishing logic deferred to social media publishing phase.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._access_token = settings.pinterest.access_token.get_secret_value()
        self._board_id = settings.pinterest.board_id
        self._http = httpx.AsyncClient(
            base_url=PINTEREST_API_BASE,
            headers={"Authorization": f"Bearer {self._access_token}"},
            timeout=30.0,
        )

    @property
    def platform_name(self) -> str:
        return "Pinterest"

    async def authenticate(self) -> None:
        if not self._access_token:
            raise PinterestAuthError("Pinterest access token not configured.")
        logger.info("pinterest_authenticated")

    async def publish_image(
        self, image_url: str, caption: str, *, hashtags: list[str] | None = None, **kwargs: Any
    ) -> PublishResult:
        raise NotImplementedError("Pinterest pin creation — future phase.")

    async def publish_video(
        self, video_url: str, title: str, description: str, *, hashtags: list[str] | None = None, **kwargs: Any
    ) -> PublishResult:
        raise NotImplementedError("Pinterest video pin creation — future phase.")

    async def get_post_analytics(self, post_id: str) -> PostAnalytics:
        raise NotImplementedError("Pinterest analytics — future phase.")

    async def health_check(self) -> bool:
        try:
            resp = await self._http.get("/user_account")
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("pinterest_health_check_failed", error=str(exc))
            return False

    async def close(self) -> None:
        await self._http.aclose()
