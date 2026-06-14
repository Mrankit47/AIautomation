"""Pinterest API v5 client implementation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.integrations.base import PostAnalytics, PublishResult, SocialMediaClient
from backend.integrations.pinterest.exceptions import (
    PinterestAPIError,
    PinterestAuthError,
)

logger = get_logger(__name__)

PINTEREST_API_BASE = "https://api.pinterest.com/v5"


class PinterestClient(SocialMediaClient):
    """Pinterest API v5 client."""

    def __init__(self) -> None:
        settings = get_settings()
        self._access_token = settings.pinterest.access_token.get_secret_value() if settings.pinterest.access_token else ""
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
        """Create a Pin on Pinterest using an image URL."""
        await self.authenticate()

        # Combine description and hashtags
        description = caption
        if hashtags:
            description += "\n\n" + " ".join(hashtags)

        pin_title = kwargs.get("title") or "Artwork"
        if len(pin_title) > 100:
            pin_title = pin_title[:97] + "..."

        if len(description) > 500:
            description = description[:497] + "..."

        data = {
            "board_id": self._board_id,
            "media_source": {
                "source_type": "image_url",
                "url": image_url,
            },
            "title": pin_title,
            "description": description,
        }

        if kwargs.get("link"):
            data["link"] = kwargs.get("link")

        try:
            logger.info("pinterest_publish_pin_started", board_id=self._board_id, url=image_url)
            resp = await self._http.post("/pins", json=data)
            resp.raise_for_status()
            res_data = resp.json()

            pin_id = res_data.get("id")
            if not pin_id:
                raise PinterestAPIError("No pin ID returned from Pinterest.")

            pin_url = f"https://www.pinterest.com/pin/{pin_id}/"

            logger.info("pinterest_publish_pin_success", pin_id=pin_id)
            return PublishResult(
                post_id=pin_id,
                url=pin_url,
                platform="pinterest",
                published_at=datetime.now(timezone.utc),
                raw_response=res_data,
            )
        except httpx.HTTPStatusError as e:
            err_detail = e.response.text
            logger.error("pinterest_publish_pin_failed", error=err_detail)
            raise PinterestAPIError(f"Pinterest pin creation failed: {err_detail}") from e
        except Exception as e:
            logger.error("pinterest_publish_pin_failed", error=str(e))
            raise PinterestAPIError(f"Pinterest pin creation failed: {str(e)}") from e

    async def publish_video(
        self, video_url: str, title: str, description: str, *, hashtags: list[str] | None = None, **kwargs: Any
    ) -> PublishResult:
        raise NotImplementedError("Pinterest video pin creation not implemented.")

    async def get_post_analytics(self, post_id: str) -> PostAnalytics:
        """Fetch Pinterest post analytics."""
        await self.authenticate()
        try:
            resp = await self._http.get(f"/pins/{post_id}/analytics", params={"split_field": "NO_SPLIT"})
            resp.raise_for_status()
            analytics_data = resp.json()
            
            # Extract metrics (lifetime metrics or standard default metrics)
            all_metrics = analytics_data.get("all", {})
            
            return PostAnalytics(
                post_id=post_id,
                platform="pinterest",
                impressions=all_metrics.get("IMPRESSION", 0),
                reach=all_metrics.get("PIN_CLICK", 0),  # map close clicks as reach proxy
                likes=all_metrics.get("SAVE", 0),       # saves map to likes/saves
                comments=0,
                shares=all_metrics.get("OUTBOUND_CLICK", 0),
                saves=all_metrics.get("SAVE", 0),
                views=all_metrics.get("VIDEO_V50_WATCH_10S", 0),
                collected_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning("pinterest_get_post_analytics_failed", post_id=post_id, error=str(e))
            raise PinterestAPIError(f"Pinterest analytics fetch failed: {str(e)}") from e

    async def health_check(self) -> bool:
        try:
            resp = await self._http.get("/user_account")
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("pinterest_health_check_failed", error=str(exc))
            return False

    async def close(self) -> None:
        await self._http.aclose()
