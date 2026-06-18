"""Ingestion API — webhook endpoint for external artwork submission.

POST /api/v1/ingestion/artwork

Accepts a JSON body with {title, image_url} and an X-API-KEY header.
Downloads the image, validates it, and feeds it into the autonomous
pipeline (artwork upload → auto-trigger workflow).

After this implementation, integrating an external Artwork Website
is a 5-minute task: just call this endpoint.
"""

from __future__ import annotations

import mimetypes

import httpx
from fastapi import APIRouter, Depends, Request

from backend.api.deps import get_artwork_service
from backend.auth.webhook_auth import verify_webhook_api_key
from backend.config.settings import get_settings
from backend.core.exceptions import ValidationException
from backend.core.logging import get_logger
from backend.schemas.ingestion import IngestionRequest, IngestionResponse
from backend.services.artwork_service import ArtworkService

logger = get_logger(__name__)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

# Max download size: 50 MB (same as upload limit)
MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024
DOWNLOAD_TIMEOUT = 60.0


@router.post("/artwork", response_model=IngestionResponse, status_code=202)
async def ingest_artwork(
    body: IngestionRequest,
    _api_key: str = Depends(verify_webhook_api_key),
    service: ArtworkService = Depends(get_artwork_service),
) -> IngestionResponse:
    """Ingest an artwork from a URL for autonomous processing.

    This endpoint:
    1. Downloads the image from the provided URL
    2. Validates MIME type and file size
    3. Calls ArtworkService.upload_artwork() which:
       - Computes SHA-256 hash for duplicate detection
       - Saves to storage
       - Creates DB record
       - Auto-triggers the full LangGraph workflow
    4. Returns artwork_id + workflow tracking info

    Requires X-API-KEY header for authentication.
    """
    image_url = str(body.image_url)

    logger.info(
        "ingestion_started",
        title=body.title,
        image_url=image_url,
        source=body.source,
    )

    # ── Download Image ───────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(DOWNLOAD_TIMEOUT),
            follow_redirects=True,
        ) as client:
            response = await client.get(image_url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ValidationException(
            detail=f"Failed to download image: HTTP {exc.response.status_code}",
            context={"url": image_url},
        )
    except httpx.RequestError as exc:
        raise ValidationException(
            detail=f"Failed to download image: {type(exc).__name__}: {exc}",
            context={"url": image_url},
        )

    file_data = response.content

    if len(file_data) > MAX_DOWNLOAD_SIZE:
        raise ValidationException(
            detail=f"Downloaded image exceeds {MAX_DOWNLOAD_SIZE // (1024 * 1024)} MB limit.",
        )

    # ── Determine Content Type ───────────────────────────────────────────
    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    if not content_type or not content_type.startswith("image/"):
        # Fallback: guess from URL
        guessed, _ = mimetypes.guess_type(image_url)
        content_type = guessed or "image/png"

    # ── Determine Filename ───────────────────────────────────────────────
    url_path = image_url.rsplit("/", 1)[-1].rsplit("?", 1)[0]
    filename = url_path if "." in url_path else f"ingested.{content_type.split('/')[-1]}"

    # ── Feed into ArtworkService pipeline ────────────────────────────────
    artwork_response = await service.upload_artwork(
        file_data=file_data,
        filename=filename,
        content_type=content_type,
        title=body.title,
        source_url=image_url,
        category=body.category,
    )

    # Check if this was a duplicate
    is_duplicate = artwork_response.image_hash is not None and artwork_response.source_url != image_url

    logger.info(
        "ingestion_completed",
        artwork_id=str(artwork_response.id),
        workflow_run_id=str(artwork_response.workflow_run_id) if artwork_response.workflow_run_id else None,
        duplicate=is_duplicate,
    )

    return IngestionResponse(
        artwork_id=artwork_response.id,
        workflow_run_id=artwork_response.workflow_run_id,
        celery_task_id=artwork_response.celery_task_id,
        status="accepted",
        message="Duplicate artwork found; returning existing record." if is_duplicate else "Artwork accepted for processing.",
        duplicate=is_duplicate,
    )


@router.post("/cloudinary", response_model=IngestionResponse, status_code=202)
async def cloudinary_webhook(
    request: Request,
    service: ArtworkService = Depends(get_artwork_service),
) -> IngestionResponse:
    """Handle Cloudinary upload webhook notifications.

    Validates signature and pulls the secure_url to ingest.
    """
    settings = get_settings()
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    # Get signature and timestamp headers
    signature = request.headers.get("X-Cld-Signature")
    timestamp = request.headers.get("X-Cld-Timestamp")

    api_secret = settings.cloudinary.api_secret.get_secret_value() if settings.cloudinary.api_secret else None

    if signature and timestamp and api_secret:
        import cloudinary.utils
        is_valid = cloudinary.utils.verify_notification_signature(
            body=body_str,
            signature=signature,
            timestamp=int(timestamp),
            secret=api_secret,
        )
        if not is_valid:
            raise ValidationException(detail="Invalid Cloudinary signature", status_code=400)

    try:
        import json
        payload = json.loads(body_str)
    except Exception as e:
        raise ValidationException(detail=f"Invalid JSON payload: {str(e)}")

    notification_type = payload.get("notification_type")
    if notification_type and notification_type != "upload":
        logger.info("cloudinary_webhook_ignored", notification_type=notification_type)
        # Return a dummy response for ignored notification types to avoid erroring Cloudinary
        import uuid
        return IngestionResponse(
            artwork_id=uuid.UUID(int=0),
            workflow_run_id=None,
            celery_task_id=None,
            status="ignored",
            message=f"Ignored notification type: {notification_type}",
            duplicate=False,
        )

    secure_url = payload.get("secure_url")
    if not secure_url:
        raise ValidationException(detail="Missing secure_url in webhook payload")

    # Determine public ID / title
    public_id = payload.get("public_id", "")
    title = public_id.split("/")[-1] if "/" in public_id else public_id
    if not title:
        title = "Cloudinary Ingested Artwork"

    # Download file data
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(DOWNLOAD_TIMEOUT),
            follow_redirects=True,
        ) as client:
            response = await client.get(secure_url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ValidationException(
            detail=f"Failed to download image from Cloudinary: HTTP {exc.response.status_code}",
            context={"url": secure_url},
        )
    except httpx.RequestError as exc:
        raise ValidationException(
            detail=f"Failed to download image from Cloudinary: {type(exc).__name__}: {exc}",
            context={"url": secure_url},
        )

    file_data = response.content
    if len(file_data) > MAX_DOWNLOAD_SIZE:
        raise ValidationException(
            detail=f"Downloaded Cloudinary image exceeds {MAX_DOWNLOAD_SIZE // (1024 * 1024)} MB limit.",
        )

    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    if not content_type or not content_type.startswith("image/"):
        guessed, _ = mimetypes.guess_type(secure_url)
        content_type = guessed or "image/png"

    filename = secure_url.rsplit("/", 1)[-1].rsplit("?", 1)[0]
    if not filename or "." not in filename:
        filename = f"{public_id.replace('/', '_')}.{content_type.split('/')[-1]}"

    # Determine category from folder structure if present
    category = "gallery"
    if "/" in public_id:
        folder = public_id.split("/")[0]
        if folder.lower() == "photography":
            category = "photography"

    # Feed into the pipeline
    artwork_response = await service.upload_artwork(
        file_data=file_data,
        filename=filename,
        content_type=content_type,
        title=title,
        source_url=secure_url,
        category=category,
    )

    is_duplicate = artwork_response.image_hash is not None and artwork_response.source_url != secure_url

    logger.info(
        "cloudinary_ingestion_completed",
        artwork_id=str(artwork_response.id),
        workflow_run_id=str(artwork_response.workflow_run_id) if artwork_response.workflow_run_id else None,
        duplicate=is_duplicate,
    )

    return IngestionResponse(
        artwork_id=artwork_response.id,
        workflow_run_id=artwork_response.workflow_run_id,
        celery_task_id=artwork_response.celery_task_id,
        status="accepted",
        message="Duplicate artwork found; returning existing record." if is_duplicate else "Artwork accepted for processing.",
        duplicate=is_duplicate,
    )
