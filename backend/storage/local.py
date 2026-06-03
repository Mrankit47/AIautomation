"""Local filesystem storage backend."""

from __future__ import annotations

from pathlib import Path

import aiofiles

from backend.config.settings import get_settings
from backend.core.exceptions import StorageException
from backend.storage.base import StorageBackend, StorageResult


class LocalStorageBackend(StorageBackend):
    """Store files on the local filesystem."""

    def __init__(self, base_path: str | None = None) -> None:
        settings = get_settings()
        self._base = Path(base_path or settings.storage.local_path).resolve()
        self._base.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        """Resolve a relative path against the base directory safely."""
        resolved = (self._base / path).resolve()
        if not str(resolved).startswith(str(self._base)):
            raise StorageException(
                detail="Path traversal detected.",
                context={"path": path},
            )
        return resolved

    async def save(
        self,
        file_data: bytes,
        destination: str,
        content_type: str = "application/octet-stream",
    ) -> StorageResult:
        """Write file data to the local filesystem."""
        full_path = self._resolve(destination)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(file_data)
        except OSError as exc:
            raise StorageException(
                detail=f"Failed to save file: {exc}",
                context={"destination": destination},
            ) from exc

        return StorageResult(
            path=str(full_path),
            url=f"file://{full_path}",
            size=len(file_data),
            content_type=content_type,
        )

    async def load(self, path: str) -> bytes:
        """Read file data from the local filesystem."""
        full_path = self._resolve(path)
        if not full_path.exists():
            raise StorageException(
                detail="File not found.",
                context={"path": path},
            )
        try:
            async with aiofiles.open(full_path, "rb") as f:
                return await f.read()
        except OSError as exc:
            raise StorageException(
                detail=f"Failed to read file: {exc}",
                context={"path": path},
            ) from exc

    async def delete(self, path: str) -> None:
        """Delete a file from the local filesystem."""
        full_path = self._resolve(path)
        if full_path.exists():
            full_path.unlink()

    async def exists(self, path: str) -> bool:
        """Check if a file exists on the local filesystem."""
        return self._resolve(path).exists()

    async def get_url(self, path: str) -> str:
        """Return a file:// URL for the local file."""
        full_path = self._resolve(path)
        return f"file://{full_path}"

    async def get_public_url(self, path: str) -> str:
        """Local storage has no public URL — returns file:// URL."""
        return await self.get_url(path)
