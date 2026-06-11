"""YouTube publisher service using YouTube Data API v3."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.integrations.youtube.exceptions import YouTubeAuthError

logger = get_logger(__name__)


class YouTubePublisher:
    """YouTube Shorts Auto Publishing service via YouTube Data API v3."""

    def __init__(self) -> None:
        settings = get_settings()
        # Fallback support for both flat environment variables and nested settings
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

    async def publish_short(
        self,
        reel_path: str,
        title: str,
        description: str,
    ) -> dict[str, Any]:
        """Publish a local video reel as a YouTube Short.

        Args:
            reel_path: Local path to the MP4 video.
            title: Video title (should include #shorts).
            description: Video description.

        Returns:
            Dict containing youtube_video_id, youtube_url, and youtube_published_at.
        """
        if not os.path.exists(reel_path):
            raise FileNotFoundError(f"Video file not found at: {reel_path}")

        file_size = os.path.getsize(reel_path)

        # Ensure title has #shorts to index properly as a Short
        if "#shorts" not in title.lower():
            # Keep title within YouTube's 100 character limit
            if len(title) > 91:
                title = title[:91] + " #shorts"
            else:
                title = f"{title} #shorts"

        async with httpx.AsyncClient(timeout=120.0) as client:
            # 1. Fetch access token
            access_token = await self._get_access_token(client)

            # 2. Initiate Resumable Upload Session
            logger.info("youtube_publish_upload_initiation_started", title=title)
            init_url = "https://www.googleapis.com/upload/youtube/v3/videos"
            init_params = {
                "uploadType": "resumable",
                "part": "snippet,status",
            }
            init_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Length": str(file_size),
                "X-Upload-Content-Type": "video/mp4",
            }
            init_body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["shorts", "aiart", "artwork"],
                    "categoryId": "22",  # People & Blogs
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            }

            try:
                init_resp = await client.post(
                    init_url,
                    params=init_params,
                    headers=init_headers,
                    json=init_body,
                )
                init_resp.raise_for_status()
            except Exception as e:
                logger.error("youtube_publish_initiation_failed", error=str(e))
                raise RuntimeError(f"YouTube upload initiation failed: {str(e)}") from e

            upload_url = init_resp.headers.get("Location")
            if not upload_url:
                raise RuntimeError("No upload Location header returned from YouTube.")

            # 3. Upload raw video bytes
            logger.info("youtube_publish_upload_bytes_started", upload_url=upload_url, file_size=file_size)
            upload_headers = {
                "Content-Length": str(file_size),
                "Content-Type": "video/mp4",
            }

            try:
                # Open file in binary mode and upload
                with open(reel_path, "rb") as f:
                    file_data = f.read()

                upload_resp = await client.put(
                    upload_url,
                    headers=upload_headers,
                    content=file_data,
                )
                upload_resp.raise_for_status()
                res_data = upload_resp.json()
            except Exception as e:
                logger.error("youtube_publish_bytes_upload_failed", error=str(e))
                raise RuntimeError(f"YouTube video bytes upload failed: {str(e)}") from e

            video_id = res_data.get("id")
            if not video_id:
                raise RuntimeError("No video ID returned from YouTube upload.")

            video_url = f"https://youtube.com/shorts/{video_id}"
            logger.info("youtube_publish_success", video_id=video_id, url=video_url)

            return {
                "youtube_video_id": video_id,
                "youtube_url": video_url,
                "youtube_published_at": datetime.now(timezone.utc),
            }
