"""YouTube analytics collection service using YouTube Data API and Analytics API."""

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.integrations.youtube.exceptions import YouTubeAuthError

logger = get_logger(__name__)


class YouTubeAnalyticsService:
    """Service to collect performance metrics and engagement insights for YouTube Shorts."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client_id = (
            os.getenv("YOUTUBE_CLIENT_ID")
            or settings.youtube.client_id
        )
        self._client_secret = (
            os.getenv("YOUTUBE_CLIENT_SECRET")
            or (settings.youtube.client_secret.get_secret_value() if settings.youtube.client_secret else "")
        )
        self._refresh_token = (
            os.getenv("YOUTUBE_REFRESH_TOKEN")
            or (settings.youtube.refresh_token.get_secret_value() if settings.youtube.refresh_token else "")
        )

    async def _get_access_token(self, client: httpx.AsyncClient) -> str:
        """Exchange the refresh token for a temporary access token."""
        if not self._client_id or not self._client_secret or not self._refresh_token:
            raise YouTubeAuthError("YouTube OAuth credentials (client_id, client_secret, refresh_token) are not fully configured.")

        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        }

        try:
            resp = await client.post(token_url, data=token_data)
            resp.raise_for_status()
            res_data = resp.json()
            access_token = res_data.get("access_token")
            if not access_token:
                raise YouTubeAuthError("OAuth token endpoint did not return an access token.")
            return access_token
        except Exception as e:
            logger.error("youtube_oauth_failed", error=str(e))
            raise YouTubeAuthError(f"YouTube authentication failed: {str(e)}") from e

    async def collect_metrics(
        self,
        video_id: str,
        published_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Fetch views, likes, comments, watch time, and average duration for a YouTube Short.

        Args:
            video_id: The YouTube Video ID.
            published_at: Optional datetime representing the video publication timestamp.

        Returns:
            Dict containing views, reach, impressions, likes, comments, shares, saves,
            watch_time (minutes), engagement_rate, and collected_at.
        """
        if not video_id:
            raise ValueError("Video ID must be provided.")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Fetch access token
            access_token = await self._get_access_token(client)

            # 2. Query YouTube Data API v3 (Videos endpoint) for views, likes, and comments
            logger.info("youtube_analytics_fetch_data_api_started", video_id=video_id)
            data_url = "https://www.googleapis.com/youtube/v3/videos"
            data_params = {
                "part": "statistics",
                "id": video_id,
            }
            data_headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }

            views = 0
            likes = 0
            comments = 0

            try:
                data_resp = await client.get(data_url, params=data_params, headers=data_headers)
                data_resp.raise_for_status()
                data_json = data_resp.json()
                items = data_json.get("items", [])
                if items:
                    stats = items[0].get("statistics", {})
                    views = int(stats.get("viewCount", 0))
                    likes = int(stats.get("likeCount", 0))
                    comments = int(stats.get("commentCount", 0))
            except Exception as e:
                logger.error("youtube_analytics_fetch_data_api_failed", video_id=video_id, error=str(e))
                raise RuntimeError(f"YouTube Data API request failed: {str(e)}") from e

            # 3. Query YouTube Analytics API v2 for watch time and average view duration
            logger.info("youtube_analytics_fetch_reports_started", video_id=video_id)
            reports_url = "https://youtubeanalytics.googleapis.com/v2/reports"

            # Safely build date range. Start date must be formatting as YYYY-MM-DD.
            # YouTube Analytics requires a start date and end date.
            start_dt = published_at or (datetime.now(timezone.utc) - timedelta(days=30))
            start_date_str = start_dt.strftime("%Y-%m-%d")
            # End date must be today or yesterday
            end_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            reports_params = {
                "ids": "channel==MINE",
                "startDate": start_date_str,
                "endDate": end_date_str,
                "metrics": "estimatedMinutesWatched,averageViewDuration",
                "filters": f"video=={video_id}",
            }

            watch_time = 0.0
            avg_duration = 0.0

            try:
                reports_resp = await client.get(reports_url, params=reports_params, headers=data_headers)
                reports_resp.raise_for_status()
                reports_json = reports_resp.json()
                
                cols = [c.get("name") for c in reports_json.get("columnHeaders", [])]
                rows = reports_json.get("rows", [])
                if rows and len(rows) > 0:
                    row = rows[0]
                    if "estimatedMinutesWatched" in cols:
                        watch_time = float(row[cols.index("estimatedMinutesWatched")])
                    if "averageViewDuration" in cols:
                        avg_duration = float(row[cols.index("averageViewDuration")])

            except Exception as e:
                # Analytics reports are delayed by 24-48h or requires different scopes.
                # Catch errors gracefully so standard Data API statistics are preserved.
                logger.warning(
                    "youtube_analytics_fetch_reports_warning",
                    video_id=video_id,
                    error=str(e),
                )

            # Compute engagement rate: (likes + comments) / views
            engagement_rate = 0.0
            total_engagements = likes + comments
            if views > 0:
                engagement_rate = float(total_engagements) / views

            logger.info(
                "youtube_analytics_fetch_success",
                video_id=video_id,
                views=views,
                likes=likes,
                watch_time=watch_time,
            )

            return {
                "views": views,
                "reach": views,  # YouTube Shorts views ~ reach
                "impressions": views,  # YouTube Shorts views ~ impressions
                "likes": likes,
                "comments": comments,
                "shares": 0,  # Shares are not natively returned per video in public statistics
                "saves": 0,
                "watch_time": watch_time,  # minutes
                "engagement_rate": round(engagement_rate, 4),
                "collected_at": datetime.now(timezone.utc),
            }
