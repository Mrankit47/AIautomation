"""Artwork service — business logic for artwork CRUD and processing."""

from __future__ import annotations

import hashlib
import math
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import NotFoundException, ValidationException
from backend.core.logging import get_logger
from backend.database.repository import BaseRepository
from backend.feature_flags.config import get_workflow_version
from backend.models.artwork import Artwork, ArtworkStatus
from backend.models.workflow_run import WorkflowRun, WorkflowStatus
from backend.schemas.artwork import (
    ArtworkAnalysisResponse,
    ArtworkCaptionResponse,
    ArtworkHashtagsResponse,
    ArtworkListResponse,
    ArtworkReelScriptResponse,
    ArtworkResponse,
    ArtworkSEOResponse,
)
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
        self._workflow_repo = BaseRepository(WorkflowRun, session)
        self._storage = storage
        self._session = session

    # ── Auto-Trigger Workflow (Phase 1) ──────────────────────────────────

    async def _auto_trigger_workflow(
        self,
        artwork: Artwork,
    ) -> tuple[uuid.UUID | None, str | None]:
        """Auto-create WorkflowRun and dispatch Celery task after upload.

        Returns:
            (workflow_run_id, celery_task_id) tuple, or (None, None) on failure.
        """
        try:
            from backend.tasks.workflow_task import execute_workflow

            version = get_workflow_version()

            # Create workflow run record
            workflow_run = await self._workflow_repo.create(
                artwork_id=artwork.id,
                workflow_version=version,
                status=WorkflowStatus.PENDING,
                error_history=[],
            )

            # Dispatch Celery task
            task = execute_workflow.delay(
                str(workflow_run.id),
                str(artwork.id),
                version,
            )

            # Store celery task ID on the workflow run
            await self._workflow_repo.update(
                workflow_run.id,
                celery_task_id=task.id,
            )

            logger.info(
                "workflow_auto_triggered",
                artwork_id=str(artwork.id),
                workflow_run_id=str(workflow_run.id),
                celery_task_id=task.id,
                workflow_version=version,
            )
            return workflow_run.id, task.id

        except Exception as exc:
            logger.error(
                "workflow_auto_trigger_failed",
                artwork_id=str(artwork.id),
                error=str(exc),
            )
            return None, None

    # ── Upload ───────────────────────────────────────────────────────────

    async def upload_artwork(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        title: str | None = None,
        source_url: str | None = None,
    ) -> ArtworkResponse:
        """Upload and persist a new artwork with auto-trigger.

        Phase 3 — Idempotency: computes SHA-256 hash and returns existing
        artwork if a duplicate is detected.

        Phase 1 — Auto-Start: after creating the artwork record, auto-creates
        a WorkflowRun and dispatches the Celery workflow.

        Args:
            file_data: Raw file bytes.
            filename: Original filename.
            content_type: MIME type of the file.
            title: Optional user-provided title.
            source_url: Original URL if ingested via webhook.

        Returns:
            ArtworkResponse with the created (or existing) record.

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

        # ── Phase 3: Duplicate Detection ─────────────────────────────────
        image_hash = hashlib.sha256(file_data).hexdigest()

        existing = await self._repo.filter_by(image_hash=image_hash)
        if existing:
            logger.info(
                "duplicate_artwork_detected",
                image_hash=image_hash,
                existing_artwork_id=str(existing[0].id),
            )
            resp = ArtworkResponse.model_validate(existing[0])
            # Populate workflow info from latest run if available
            if existing[0].workflow_runs:
                latest_run = existing[0].workflow_runs[-1]
                resp.workflow_run_id = latest_run.id
                resp.celery_task_id = latest_run.celery_task_id
            return resp

        # ── Save to storage ──────────────────────────────────────────────
        artwork_id = uuid.uuid4()
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "png"
        storage_path = f"artworks/{artwork_id}.{ext}"

        storage_result = await self._storage.save(
            file_data, storage_path, content_type
        )

        # ── Create database record ───────────────────────────────────────
        artwork = await self._repo.create(
            id=artwork_id,
            title=title,
            original_filename=filename,
            file_path=storage_result.path,
            storage_url=storage_result.url,
            file_size=len(file_data),
            mime_type=content_type,
            status=ArtworkStatus.UPLOADED,
            image_hash=image_hash,
            source_url=source_url,
        )

        logger.info(
            "artwork_uploaded",
            artwork_id=str(artwork.id),
            filename=filename,
            file_size=len(file_data),
            image_hash=image_hash,
        )

        # ── Phase 1: Auto-Trigger Workflow ───────────────────────────────
        workflow_run_id, celery_task_id = await self._auto_trigger_workflow(artwork)

        resp = ArtworkResponse.model_validate(artwork)
        resp.workflow_run_id = workflow_run_id
        resp.celery_task_id = celery_task_id
        return resp

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

    async def get_analysis(self, artwork_id: uuid.UUID) -> ArtworkAnalysisResponse:
        """Retrieve artwork analysis results."""
        artwork = await self._repo.get_by_id(artwork_id)
        if artwork is None:
            raise NotFoundException(detail=f"Artwork {artwork_id} not found.")
        return ArtworkAnalysisResponse(
            artwork_id=artwork.id,
            analysis_data=artwork.analysis_data,
        )

    async def get_seo(self, artwork_id: uuid.UUID) -> ArtworkSEOResponse:
        """Retrieve artwork SEO-optimized metadata."""
        artwork = await self._repo.get_by_id(artwork_id)
        if artwork is None:
            raise NotFoundException(detail=f"Artwork {artwork_id} not found.")
        return ArtworkSEOResponse(
            artwork_id=artwork.id,
            seo_data=artwork.seo_data,
        )

    async def get_caption(self, artwork_id: uuid.UUID) -> ArtworkCaptionResponse:
        """Retrieve artwork platform captions and titles."""
        artwork = await self._repo.get_by_id(artwork_id)
        if artwork is None:
            raise NotFoundException(detail=f"Artwork {artwork_id} not found.")
        return ArtworkCaptionResponse(
            artwork_id=artwork.id,
            caption=artwork.caption,
            youtube_title=artwork.youtube_title,
            youtube_description=artwork.youtube_description,
        )

    async def get_hashtags(self, artwork_id: uuid.UUID) -> ArtworkHashtagsResponse:
        """Retrieve artwork hashtags."""
        artwork = await self._repo.get_by_id(artwork_id)
        if artwork is None:
            raise NotFoundException(detail=f"Artwork {artwork_id} not found.")
        return ArtworkHashtagsResponse(
            artwork_id=artwork.id,
            hashtags=artwork.hashtags,
        )

    async def get_reel_script(self, artwork_id: uuid.UUID) -> ArtworkReelScriptResponse:
        """Retrieve artwork reel video script."""
        artwork = await self._repo.get_by_id(artwork_id)
        if artwork is None:
            raise NotFoundException(detail=f"Artwork {artwork_id} not found.")
        return ArtworkReelScriptResponse(
            artwork_id=artwork.id,
            reel_script=artwork.reel_script,
        )

