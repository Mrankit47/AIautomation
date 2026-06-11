"""Artwork API endpoints — upload, retrieve, list, and trigger processing."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile

from backend.api.deps import get_artwork_service, get_workflow_service, get_instagram_publisher, get_youtube_publisher
from backend.auth.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.artwork import (
    ArtworkAnalysisResponse,
    ArtworkCaptionResponse,
    ArtworkHashtagsResponse,
    ArtworkListResponse,
    ArtworkReelScriptResponse,
    ArtworkResponse,
    ArtworkSEOResponse,
    InstagramPublishResponse,
    InstagramStatusResponse,
    YouTubePublishResponse,
    YouTubeStatusResponse,
)
from backend.schemas.workflow import (
    WorkflowStatusResponse,
    WorkflowTriggerRequest,
    WorkflowTriggerResponse,
)
from backend.schemas.analytics import ArtworkAnalyticsResponse
from backend.services.artwork_service import ArtworkService
from backend.services.workflow_service import WorkflowService

router = APIRouter(prefix="/artworks", tags=["artworks"])


@router.post("/upload", response_model=ArtworkResponse, status_code=201)
async def upload_artwork(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> ArtworkResponse:
    """Upload a new artwork image."""
    file_data = await file.read()
    return await service.upload_artwork(
        file_data=file_data,
        filename=file.filename or "untitled.png",
        content_type=file.content_type or "application/octet-stream",
        title=title,
    )


@router.get("", response_model=ArtworkListResponse)
async def list_artworks(
    page: int = 1,
    per_page: int = 20,
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> ArtworkListResponse:
    """List all artworks with pagination."""
    return await service.list_artworks(page=page, per_page=per_page)


@router.get("/{artwork_id}", response_model=ArtworkResponse)
async def get_artwork(
    artwork_id: uuid.UUID,
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> ArtworkResponse:
    """Retrieve a single artwork by ID."""
    return await service.get_artwork(artwork_id)


@router.post(
    "/{artwork_id}/process",
    response_model=WorkflowTriggerResponse,
    status_code=202,
)
async def trigger_processing(
    artwork_id: uuid.UUID,
    body: WorkflowTriggerRequest | None = None,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    current_user: User = Depends(get_current_active_user),
) -> WorkflowTriggerResponse:
    """Trigger the AI processing workflow for an artwork.

    Dispatches a Celery task and returns immediately with the task ID.
    """
    version = body.workflow_version if body else "v1"
    return await workflow_service.trigger_workflow(
        artwork_id=artwork_id,
        workflow_version=version,
    )


@router.get(
    "/{artwork_id}/workflow/{workflow_run_id}",
    response_model=WorkflowStatusResponse,
)
async def get_workflow_status(
    artwork_id: uuid.UUID,
    workflow_run_id: uuid.UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    current_user: User = Depends(get_current_active_user),
) -> WorkflowStatusResponse:
    """Get the status of a specific workflow run."""
    return await workflow_service.get_workflow_status(workflow_run_id)


@router.get("/{artwork_id}/analysis", response_model=ArtworkAnalysisResponse)
async def get_artwork_analysis(
    artwork_id: uuid.UUID,
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> ArtworkAnalysisResponse:
    """Retrieve artwork analysis results."""
    return await service.get_analysis(artwork_id)


@router.get("/{artwork_id}/seo", response_model=ArtworkSEOResponse)
async def get_artwork_seo(
    artwork_id: uuid.UUID,
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> ArtworkSEOResponse:
    """Retrieve artwork SEO-optimized metadata."""
    return await service.get_seo(artwork_id)


@router.get("/{artwork_id}/caption", response_model=ArtworkCaptionResponse)
async def get_artwork_caption(
    artwork_id: uuid.UUID,
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> ArtworkCaptionResponse:
    """Retrieve artwork platform captions and titles."""
    return await service.get_caption(artwork_id)


@router.get("/{artwork_id}/hashtags", response_model=ArtworkHashtagsResponse)
async def get_artwork_hashtags(
    artwork_id: uuid.UUID,
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> ArtworkHashtagsResponse:
    """Retrieve artwork hashtags."""
    return await service.get_hashtags(artwork_id)


@router.get("/{artwork_id}/reel", response_model=ArtworkReelScriptResponse)
async def get_artwork_reel(
    artwork_id: uuid.UUID,
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> ArtworkReelScriptResponse:
    """Retrieve artwork reel video script."""
    return await service.get_reel_script(artwork_id)


@router.post("/{artwork_id}/publish/instagram", response_model=InstagramPublishResponse, status_code=200)
async def publish_to_instagram(
    artwork_id: uuid.UUID,
    service: ArtworkService = Depends(get_artwork_service),
    publisher = Depends(get_instagram_publisher),
    current_user: User = Depends(get_current_active_user),
) -> InstagramPublishResponse:
    """Trigger manual publishing of the artwork's reel to Instagram."""
    from backend.core.exceptions import NotFoundException, ValidationException

    artwork = await service._repo.get_by_id(artwork_id)
    if not artwork:
        raise NotFoundException(detail=f"Artwork {artwork_id} not found.")

    if not artwork.reel_path:
        raise ValidationException(detail="Reel has not been generated for this artwork.")

    if not artwork.caption:
        raise ValidationException(detail="Caption has not been generated for this artwork.")

    # Update status to processing
    await service._repo.update(artwork_id, instagram_status="processing")

    try:
        # Publish
        result = await publisher.publish_reel(
            reel_path=artwork.reel_path,
            caption=artwork.caption,
        )
        # Save results
        updated = await service._repo.update(
            artwork_id,
            instagram_status="published",
            instagram_post_id=result["instagram_post_id"],
            instagram_permalink=result["instagram_permalink"],
            instagram_published_at=result["instagram_published_at"],
        )
        return InstagramPublishResponse(
            artwork_id=artwork_id,
            instagram_status="published",
            instagram_post_id=updated.instagram_post_id,
            instagram_permalink=updated.instagram_permalink,
            instagram_published_at=updated.instagram_published_at,
        )
    except Exception as e:
        # On error, update status to failed and store the error message
        await service._repo.update(
            artwork_id,
            instagram_status="failed",
            error_message=str(e),
        )
        return InstagramPublishResponse(
            artwork_id=artwork_id,
            instagram_status="failed",
            error_message=str(e),
        )


@router.get("/{artwork_id}/instagram-status", response_model=InstagramStatusResponse)
async def get_instagram_status(
    artwork_id: uuid.UUID,
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> InstagramStatusResponse:
    """Get the current Instagram publishing status and details."""
    from backend.core.exceptions import NotFoundException

    artwork = await service._repo.get_by_id(artwork_id)
    if not artwork:
        raise NotFoundException(detail=f"Artwork {artwork_id} not found.")

    return InstagramStatusResponse(
        artwork_id=artwork_id,
        instagram_status=artwork.instagram_status,
        instagram_post_id=artwork.instagram_post_id,
        instagram_permalink=artwork.instagram_permalink,
        instagram_published_at=artwork.instagram_published_at,
        error_message=artwork.error_message if artwork.instagram_status == "failed" else None,
    )


@router.post("/{artwork_id}/publish/youtube", response_model=YouTubePublishResponse, status_code=200)
async def publish_to_youtube(
    artwork_id: uuid.UUID,
    service: ArtworkService = Depends(get_artwork_service),
    publisher = Depends(get_youtube_publisher),
    current_user: User = Depends(get_current_active_user),
) -> YouTubePublishResponse:
    """Trigger manual publishing of the artwork's reel to YouTube Shorts."""
    from backend.core.exceptions import NotFoundException, ValidationException

    artwork = await service._repo.get_by_id(artwork_id)
    if not artwork:
        raise NotFoundException(detail=f"Artwork {artwork_id} not found.")

    if not artwork.reel_path:
        raise ValidationException(detail="Reel has not been generated for this artwork.")

    # YouTube titles are limited to 100 characters. Build a clean title.
    raw_title = artwork.youtube_title or artwork.title or artwork.original_filename.rsplit(".", 1)[0]
    raw_description = artwork.youtube_description or artwork.caption or ""

    # Update status to processing
    await service._repo.update(artwork_id, youtube_status="processing")

    try:
        # Publish
        result = await publisher.publish_short(
            reel_path=artwork.reel_path,
            title=raw_title,
            description=raw_description,
        )
        # Save results
        updated = await service._repo.update(
            artwork_id,
            youtube_status="published",
            youtube_video_id=result["youtube_video_id"],
            youtube_url=result["youtube_url"],
            youtube_published_at=result["youtube_published_at"],
        )
        return YouTubePublishResponse(
            artwork_id=artwork_id,
            youtube_status="published",
            youtube_video_id=updated.youtube_video_id,
            youtube_url=updated.youtube_url,
            youtube_published_at=updated.youtube_published_at,
        )
    except Exception as e:
        # On error, update status to failed and store the error message
        await service._repo.update(
            artwork_id,
            youtube_status="failed",
            error_message=str(e),
        )
        return YouTubePublishResponse(
            artwork_id=artwork_id,
            youtube_status="failed",
            error_message=str(e),
        )


@router.get("/{artwork_id}/youtube-status", response_model=YouTubeStatusResponse)
async def get_youtube_status(
    artwork_id: uuid.UUID,
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> YouTubeStatusResponse:
    """Get the current YouTube publishing status and details."""
    from backend.core.exceptions import NotFoundException

    artwork = await service._repo.get_by_id(artwork_id)
    if not artwork:
        raise NotFoundException(detail=f"Artwork {artwork_id} not found.")

    return YouTubeStatusResponse(
        artwork_id=artwork_id,
        youtube_status=artwork.youtube_status,
        youtube_video_id=artwork.youtube_video_id,
        youtube_url=artwork.youtube_url,
        youtube_published_at=artwork.youtube_published_at,
        error_message=artwork.error_message if artwork.youtube_status == "failed" else None,
    )


@router.get("/{artwork_id}/analytics", response_model=list[ArtworkAnalyticsResponse])
async def get_artwork_analytics(
    artwork_id: uuid.UUID,
    service: ArtworkService = Depends(get_artwork_service),
    current_user: User = Depends(get_current_active_user),
) -> list[ArtworkAnalyticsResponse]:
    """Retrieve historical analytics data for a specific artwork."""
    from backend.core.exceptions import NotFoundException
    from backend.schemas.analytics import ArtworkAnalyticsResponse

    artwork = await service._repo.get_by_id(artwork_id)
    if not artwork:
        raise NotFoundException(detail=f"Artwork {artwork_id} not found.")

    return [ArtworkAnalyticsResponse.model_validate(a) for a in artwork.analytics]
