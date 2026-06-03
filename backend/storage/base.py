"""Abstract storage interface.

Concrete implementations (local, S3, GCS, Cloudinary) must implement
all methods.  The active backend is selected via configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class StorageResult:
    """Result of a file storage operation."""

    path: str
    url: str
    size: int
    content_type: str


class StorageBackend(ABC):
    """Abstract base class for file storage backends."""

    @abstractmethod
    async def save(
        self,
        file_data: bytes,
        destination: str,
        content_type: str = "application/octet-stream",
    ) -> StorageResult:
        """Save file data to the storage backend."""
        ...

    @abstractmethod
    async def load(self, path: str) -> bytes:
        """Load file data from the storage backend."""
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete a file from the storage backend."""
        ...

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check whether a file exists in the storage backend."""
        ...

    @abstractmethod
    async def get_url(self, path: str) -> str:
        """Return a public/signed URL for the file."""
        ...

    @abstractmethod
    async def get_public_url(self, path: str) -> str:
        """Return a publicly accessible URL (for CDN-backed storage)."""
        ...
