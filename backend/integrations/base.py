"""Abstract integration interfaces for social media and cloud storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PublishResult:
    """Result of publishing content to a social platform."""

    post_id: str
    url: str
    platform: str
    published_at: datetime
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class PostAnalytics:
    """Analytics data for a single published post."""

    post_id: str
    platform: str
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    views: int = 0
    collected_at: datetime | None = None


@dataclass
class UploadResult:
    """Result of uploading a file to cloud storage."""

    public_id: str
    url: str
    secure_url: str
    format: str
    bytes: int
    width: int | None = None
    height: int | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


class SocialMediaClient(ABC):
    """Abstract interface for social media platform clients."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Human-readable platform name."""
        ...

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the platform API."""
        ...

    @abstractmethod
    async def publish_image(
        self,
        image_url: str,
        caption: str,
        *,
        hashtags: list[str] | None = None,
        **kwargs: Any,
    ) -> PublishResult:
        """Publish an image post."""
        ...

    @abstractmethod
    async def publish_video(
        self,
        video_url: str,
        title: str,
        description: str,
        *,
        hashtags: list[str] | None = None,
        **kwargs: Any,
    ) -> PublishResult:
        """Publish a video post (reel/short)."""
        ...

    @abstractmethod
    async def get_post_analytics(self, post_id: str) -> PostAnalytics:
        """Retrieve analytics for a published post."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the platform API is reachable."""
        ...


class MediaStorageClient(ABC):
    """Abstract interface for cloud media storage / CDN clients."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        ...

    @abstractmethod
    async def upload(
        self,
        file_path: str,
        *,
        folder: str | None = None,
        resource_type: str = "image",
        **kwargs: Any,
    ) -> UploadResult:
        """Upload a file to cloud storage."""
        ...

    @abstractmethod
    async def transform(
        self,
        public_id: str,
        transformations: dict[str, Any],
    ) -> str:
        """Apply transformations and return the transformed URL."""
        ...

    @abstractmethod
    async def delete(self, public_id: str) -> None:
        """Delete a resource from cloud storage."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the storage provider is reachable."""
        ...
