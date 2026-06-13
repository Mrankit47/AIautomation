"""Instagram publisher service using Meta Graph API."""

from __future__ import annotations

import asyncio
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


class InstagramPublisher:
    """Instagram Reels Auto Publishing service via Meta Graph API."""

    def __init__(self) -> None:
        settings = get_settings()
        # Fallback support for both flat environment variables and nested settings
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

    async def publish_reel(
        self,
        reel_path: str,
        caption: str,
    ) -> dict[str, Any]:
        """Publish a local video reel to Instagram Reels.

        Args:
            reel_path: Local path or public URL of the MP4 video.
            caption: Post caption text.

        Returns:
            Dict containing instagram_post_id, instagram_permalink, and instagram_published_at.
        """
        # Validate settings
        if not self._access_token:
            raise InstagramAuthError("Instagram access token is not configured.")
        if not self._account_id:
            raise InstagramAuthError("Instagram business account ID is not configured.")

        # Resolve reel_path to a public URL. Meta API requires a public HTTP(S) URL.
        if not (reel_path.startswith("http://") or reel_path.startswith("https://")):
            if not os.path.exists(reel_path):
                raise FileNotFoundError(f"Reel video file not found at: {reel_path}")
            # Upload local file to a public temporary host so Meta's servers can download it
            video_url = await self._upload_to_temp_host(reel_path)
        else:
            video_url = reel_path

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            # 1. Create Media Container
            logger.info(
                "instagram_publish_container_creation_started",
                account_id=self._account_id,
                video_url=video_url,
            )
            container_url = f"/{self._account_id}/media"
            container_data = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": self._access_token,
            }
            try:
                resp = await client.post(container_url, data=container_data)
                resp.raise_for_status()
                res_data = resp.json()
            except httpx.HTTPStatusError as e:
                err_detail = e.response.text
                logger.error("instagram_publish_container_creation_failed", error=err_detail)
                raise InstagramAPIError(f"Failed to create media container: {err_detail}") from e
            except Exception as e:
                logger.error("instagram_publish_container_creation_failed", error=str(e))
                raise InstagramAPIError(f"Failed to create media container: {str(e)}") from e

            container_id = res_data.get("id")
            if not container_id:
                raise InstagramAPIError("No container ID returned from media creation.")

            # 2. Poll Processing Status
            logger.info("instagram_publish_polling_started", container_id=container_id)
            poll_url = f"/{container_id}"
            poll_params = {
                "fields": "status_code,status",
                "access_token": self._access_token,
            }
            status_code = "IN_PROGRESS"
            max_attempts = 30
            attempt = 0
            while status_code == "IN_PROGRESS" and attempt < max_attempts:
                await asyncio.sleep(5)
                attempt += 1
                try:
                    poll_resp = await client.get(poll_url, params=poll_params)
                    poll_resp.raise_for_status()
                    poll_data = poll_resp.json()
                    status_code = poll_data.get("status_code", "IN_PROGRESS")
                    logger.info(
                        "instagram_publish_polling_status",
                        container_id=container_id,
                        status_code=status_code,
                        attempt=attempt,
                    )
                except Exception as e:
                    logger.warning(
                        "instagram_publish_polling_error",
                        container_id=container_id,
                        error=str(e),
                    )
                    continue

            if status_code != "FINISHED":
                raise InstagramAPIError(
                    f"Container processing failed or timed out with status: {status_code}"
                )

            # 3. Publish Media
            logger.info("instagram_publish_media_publish_started", container_id=container_id)
            publish_url = f"/{self._account_id}/media_publish"
            publish_data = {
                "creation_id": container_id,
                "access_token": self._access_token,
            }
            try:
                pub_resp = await client.post(publish_url, data=publish_data)
                pub_resp.raise_for_status()
                pub_res_data = pub_resp.json()
            except Exception as e:
                logger.error("instagram_publish_media_publish_failed", error=str(e))
                raise InstagramAPIError(f"Failed to publish media: {str(e)}") from e

            post_id = pub_res_data.get("id")
            if not post_id:
                raise InstagramAPIError("No post ID returned from media publish.")

            # 4. Fetch Permalink
            permalink = None
            try:
                get_post_url = f"/{post_id}"
                post_params = {
                    "fields": "permalink",
                    "access_token": self._access_token,
                }
                post_resp = await client.get(get_post_url, params=post_params)
                post_resp.raise_for_status()
                post_data = post_resp.json()
                permalink = post_data.get("permalink")
            except Exception as e:
                logger.warning(
                    "instagram_fetch_permalink_failed",
                    post_id=post_id,
                    error=str(e),
                )

            logger.info(
                "instagram_publish_success",
                post_id=post_id,
                permalink=permalink,
            )
            return {
                "instagram_post_id": post_id,
                "instagram_permalink": permalink,
                "instagram_published_at": datetime.now(timezone.utc),
            }

    async def _upload_to_temp_host(self, file_path: str) -> str:
        """Upload local file to a temporary public hosting service to get a public URL for Meta API."""
        logger.info("uploading_video_to_temp_host_started", file_path=file_path)
        
        # 1. Try tmpfiles.org
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (os.path.basename(file_path), f, "video/mp4")}
                    resp = await client.post("https://tmpfiles.org/api/v1/upload", files=files)
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success":
                        url = data.get("data", {}).get("url")
                        if url:
                            direct_url = url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                            logger.info("uploading_video_to_temp_host_success_tmpfiles", url=direct_url)
                            return direct_url
        except Exception as e:
            logger.warning("upload_to_tmpfiles_failed", error=str(e))

        # 2. Try catbox.moe as fallback
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(file_path, "rb") as f:
                    data = {
                        "reqtype": "fileupload"
                    }
                    files = {"fileToUpload": (os.path.basename(file_path), f, "video/mp4")}
                    resp = await client.post("https://catbox.moe/user/api.php", data=data, files=files)
                
                if resp.status_code == 200:
                    url = resp.text.strip()
                    if url.startswith("http://") or url.startswith("https://"):
                        logger.info("uploading_video_to_temp_host_success_catbox", url=url)
                        return url
        except Exception as e:
            logger.warning("upload_to_catbox_failed", error=str(e))
            
        raise RuntimeError("Failed to upload video to temporary public hosting for Instagram.")
