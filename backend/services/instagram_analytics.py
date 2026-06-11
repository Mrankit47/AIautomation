"""Instagram analytics collection service using Meta Graph API."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.integrations.instagram.exceptions import (
    InstagramAPIError,
    InstagramAuthError,
)

logger = get_logger(__name__)


class InstagramAnalyticsService:
    """Service to collect organic performance metrics and insights from Instagram."""

    def __init__(self) -> None:
        settings = get_settings()
        self._access_token = (
            os.getenv("INSTAGRAM_ACCESS_TOKEN")
            or (settings.instagram.access_token.get_secret_value() if settings.instagram.access_token else "")
        )
        self._account_id = (
            os.getenv("INSTAGRAM_ACCOUNT_ID")
            or settings.instagram.account_id
            or settings.instagram.business_account_id
        )
        self.base_url = "https://graph.facebook.com/v19.0"

    async def collect_metrics(self, media_id: str) -> dict[str, Any]:
        """Fetch organic insights and basic statistics for a published Instagram Reel/post.

        Args:
            media_id: The Instagram Media (post/reel) ID.

        Returns:
            Dict containing views (plays), reach, impressions, likes, comments, shares, saves,
            engagement_rate, and collected_at.
        """
        if not self._access_token:
            raise InstagramAuthError("Instagram access token is not configured.")
        if not self._account_id:
            raise InstagramAuthError("Instagram business account ID is not configured.")
        if not media_id:
            raise ValueError("Media ID must be provided.")

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            # 1. Fetch organic basic statistics (likes, comments)
            logger.info("instagram_analytics_fetch_media_started", media_id=media_id)
            media_url = f"/{media_id}"
            media_params = {
                "fields": "like_count,comments_count",
                "access_token": self._access_token,
            }
            try:
                media_resp = await client.get(media_url, params=media_params)
                media_resp.raise_for_status()
                media_data = media_resp.json()
            except Exception as e:
                logger.error("instagram_analytics_fetch_media_failed", media_id=media_id, error=str(e))
                raise InstagramAPIError(f"Failed to fetch media stats: {str(e)}") from e

            likes = media_data.get("like_count", 0)
            comments = media_data.get("comments_count", 0)

            # 2. Fetch insights metrics (reach, impressions, saved, shares, plays/views)
            logger.info("instagram_analytics_fetch_insights_started", media_id=media_id)
            insights_url = f"/{media_id}/insights"
            insights_params = {
                "metric": "reach,impressions,saved,shares,plays",
                "access_token": self._access_token,
            }
            
            reach = 0
            impressions = 0
            saved = 0
            shares = 0
            plays = 0

            try:
                insights_resp = await client.get(insights_url, params=insights_params)
                insights_resp.raise_for_status()
                insights_data = insights_resp.json()

                for metric in insights_data.get("data", []):
                    name = metric.get("name")
                    values = metric.get("values", [])
                    if values:
                        val = values[0].get("value", 0)
                        if name == "reach":
                            reach = val
                        elif name == "impressions":
                            impressions = val
                        elif name == "saved":
                            saved = val
                        elif name == "shares":
                            shares = val
                        elif name == "plays":
                            plays = val

            except Exception as e:
                # Insights might be empty/delayed for very new media, log a warning and proceed
                logger.warning(
                    "instagram_analytics_fetch_insights_warning",
                    media_id=media_id,
                    error=str(e),
                )

            # Compute engagement rate: (likes + comments + shares + saves) / reach
            # Fallback to impressions if reach is 0, or default to 0.0
            engagement_rate = 0.0
            total_engagements = likes + comments + shares + saved
            if reach > 0:
                engagement_rate = float(total_engagements) / reach
            elif impressions > 0:
                engagement_rate = float(total_engagements) / impressions

            logger.info(
                "instagram_analytics_fetch_success",
                media_id=media_id,
                views=plays,
                reach=reach,
                likes=likes,
            )

            return {
                "views": plays,
                "reach": reach,
                "impressions": impressions,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "saves": saved,
                "watch_time": 0.0,  # Watch time not natively provided for Reels in simple Graph API insights
                "engagement_rate": round(engagement_rate, 4),
                "collected_at": datetime.now(timezone.utc),
            }
