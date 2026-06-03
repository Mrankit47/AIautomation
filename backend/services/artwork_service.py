"""Artwork service — business logic for artwork CRUD and processing."""

from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import NotFoundException, ValidationException
from backend.core.logging import get_logger
from backend.database.repository import BaseRepository
from backend.models.artwork import Artwork, ArtworkStatus
from backend.schemas.artwork import ArtworkListResponse, ArtworkResponse
from backend.storage.base import StorageBackend

logger = get_logger(__name__)

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/tiff"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


class ArtworkService:
    """Artwork business logic — upload, retrieve, list, status management."""

    def __init__(
        self,
        session: AsyncSession,
        storage: StorageBackend,
    ) -> None:
        self._repo = BaseRepository(Artwork, session)
        self._storage = storage
        self._session = session

    async def upload_artwork(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        title: str | None = None,
    ) -> ArtworkResponse:
        """Upload and persist a new artwork.

        Args:
            file_data: Raw file bytes.
            filename: Original filename.
            content_type: MIME type of the file.
            title: Optional user-provided title.

        Returns:
            ArtworkResponse with the created record.

        Raises:
            ValidationException: If file type or size is invalid.
        """
        if content_type not in ALLOWED_MIME_TYPES:
            raise ValidationException(
                detail=f"Unsupported file type: {content_type}. Allowed: {ALLOWED_MIME_TYPES}",
            )
        if len(file_data) > MAX_FILE_SIZE:
            raise ValidationException(
                detail=f"File too large. Maximum: {MAX_FILE_SIZE // (1024 * 1024)} MB",
            )

        # Generate storage path
        artwork_id = uuid.uuid4()
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "png"
        storage_path = f"artworks/{artwork_id}.{ext}"

        # Save to storage
        storage_result = await self._storage.save(
            file_data, storage_path, content_type
        )

        # Create database record
        artwork = await self._repo.create(
            id=artwork_id,
            title=title,
            original_filename=filename,
            file_path=storage_result.path,
            storage_url=storage_result.url,
            file_size=len(file_data),
            mime_type=content_type,
            status=ArtworkStatus.UPLOADED,
        )

        logger.info(
            "artwork_uploaded",
            artwork_id=str(artwork.id),
            filename=filename,
            file_size=len(file_data),
        )

        return ArtworkResponse.model_validate(artwork)

    async def get_artwork(self, artwork_id: uuid.UUID) -> ArtworkResponse:
        """Retrieve a single artwork by ID.

        Raises:
            NotFoundException: If the artwork does not exist.
        """
        artwork = await self._repo.get_by_id(artwork_id)
        if artwork is None:
            raise NotFoundException(
                detail=f"Artwork {artwork_id} not found.",
                context={"artwork_id": str(artwork_id)},
            )
        return ArtworkResponse.model_validate(artwork)

    async def list_artworks(
        self, page: int = 1, per_page: int = 20
    ) -> ArtworkListResponse:
        """Return a paginated list of artworks."""
        items, total = await self._repo.get_paginated(page=page, per_page=per_page)
        return ArtworkListResponse(
            items=[ArtworkResponse.model_validate(a) for a in items],
            total=total,
            page=page,
            per_page=per_page,
            pages=math.ceil(total / per_page) if per_page > 0 else 0,
        )

    async def update_status(
        self,
        artwork_id: uuid.UUID,
        status: ArtworkStatus,
        **kwargs: Any,
    ) -> ArtworkResponse:
        """Update the processing status of an artwork."""
        artwork = await self._repo.update(artwork_id, status=status, **kwargs)
        if artwork is None:
            raise NotFoundException(detail=f"Artwork {artwork_id} not found.")
        logger.info(
            "artwork_status_updated",
            artwork_id=str(artwork_id),
            new_status=status.value,
        )
        return ArtworkResponse.model_validate(artwork)
