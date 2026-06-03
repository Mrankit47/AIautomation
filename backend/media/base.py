"""Abstract media processor interface for future video/reel generation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MediaResult:
    """Result of a media processing operation."""

    output_path: str
    format: str
    duration: float | None = None
    file_size: int = 0
    width: int | None = None
    height: int | None = None


@dataclass
class ImageMetadata:
    """Metadata extracted from an image file."""

    width: int
    height: int
    format: str
    color_space: str
    file_size: int
    dominant_colors: list[str] = field(default_factory=list)


class MediaProcessor(ABC):
    """Abstract interface for media processing (images, reels, shorts)."""

    @abstractmethod
    async def create_reel(
        self,
        image_path: str,
        template_name: str,
        *,
        music_path: str | None = None,
        duration: int = 15,
        caption_text: str | None = None,
        **kwargs: Any,
    ) -> MediaResult:
        """Create a reel/short video from an artwork image."""
        ...

    @abstractmethod
    async def resize_image(
        self,
        image_path: str,
        width: int,
        height: int,
        *,
        output_format: str = "webp",
    ) -> str:
        """Resize an image and return the output path."""
        ...

    @abstractmethod
    async def get_image_metadata(self, image_path: str) -> ImageMetadata:
        """Extract metadata from an image file."""
        ...

    @abstractmethod
    async def create_thumbnail(
        self,
        image_path: str,
        size: tuple[int, int] = (300, 300),
    ) -> str:
        """Create a thumbnail and return the output path."""
        ...
