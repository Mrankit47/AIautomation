"""Cloudinary media storage client stub."""

from __future__ import annotations

from typing import Any

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.integrations.base import MediaStorageClient, UploadResult
from backend.integrations.cloudinary.exceptions import CloudinaryAPIError

logger = get_logger(__name__)


class CloudinaryClient(MediaStorageClient):
    """Cloudinary upload, transformation, and CDN client.

    Note: Full implementation deferred to media integration phase.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._cloud_name = settings.cloudinary.cloud_name
        self._api_key = settings.cloudinary.api_key
        self._api_secret = settings.cloudinary.api_secret.get_secret_value()
        self._upload_preset = settings.cloudinary.upload_preset

    @property
    def provider_name(self) -> str:
        return "Cloudinary"

    async def upload(
        self,
        file_path: str,
        *,
        folder: str | None = None,
        resource_type: str = "image",
        **kwargs: Any,
    ) -> UploadResult:
        raise NotImplementedError("Cloudinary upload — future phase.")

    async def transform(
        self,
        public_id: str,
        transformations: dict[str, Any],
    ) -> str:
        raise NotImplementedError("Cloudinary transform — future phase.")

    async def delete(self, public_id: str) -> None:
        raise NotImplementedError("Cloudinary delete — future phase.")

    async def health_check(self) -> bool:
        return bool(self._cloud_name and self._api_key)
