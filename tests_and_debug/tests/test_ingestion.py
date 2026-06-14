"""Integration/Unit tests for the webhook ingestion API endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from backend.models.artwork import ArtworkStatus
from backend.schemas.artwork import ArtworkResponse


@pytest.fixture
def mock_artwork_response() -> ArtworkResponse:
    return ArtworkResponse(
        id=uuid.uuid4(),
        title="Ingested Art",
        original_filename="ingested.png",
        file_path="artworks/ingested.png",
        storage_url="http://mock-storage/artworks/ingested.png",
        file_size=1024,
        mime_type="image/png",
        width=None,
        height=None,
        status=ArtworkStatus.UPLOADED,
        image_hash="fakehash123",
        source_url="http://example.com/image.png",
        workflow_run_id=uuid.uuid4(),
        celery_task_id="task-1234",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_ingest_artwork_auth_failed(client: AsyncClient) -> None:
    """Test that requests without correct API key are rejected with 401."""
    # Mock settings to configure API key
    with patch("backend.auth.webhook_auth.get_settings") as mock_settings:
        mock_settings.return_value.webhook_api_key = "secret-api-key"

        response = await client.post(
            "/api/v1/ingestion/artwork",
            json={"title": "Ingested", "image_url": "http://example.com/image.png"},
            headers={"X-API-KEY": "wrong-key"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key."


@pytest.mark.asyncio
async def test_ingest_artwork_success(client: AsyncClient, mock_artwork_response) -> None:
    """Test successful ingestion of artwork via webhook."""
    # Mock settings to configure API key
    with patch("backend.auth.webhook_auth.get_settings") as mock_settings:
        mock_settings.return_value.webhook_api_key = "secret-api-key"

        # Mock the http download client
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_http_resp = MagicMock()
            mock_http_resp.status_code = 200
            mock_http_resp.content = b"fake-downloaded-bytes"
            mock_http_resp.headers = {"content-type": "image/png"}
            mock_http_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_http_resp

            # Mock upload_artwork service call
            with patch("backend.api.v1.ingestion.ArtworkService.upload_artwork", new_callable=AsyncMock) as mock_upload:
                mock_upload.return_value = mock_artwork_response

                response = await client.post(
                    "/api/v1/ingestion/artwork",
                    json={"title": "Ingested Art", "image_url": "http://example.com/image.png"},
                    headers={"X-API-KEY": "secret-api-key"},
                )

                assert response.status_code == 202
                data = response.json()
                assert data["status"] == "accepted"
                assert data["artwork_id"] == str(mock_artwork_response.id)
                assert data["workflow_run_id"] == str(mock_artwork_response.workflow_run_id)
                assert data["celery_task_id"] == mock_artwork_response.celery_task_id
                assert data["duplicate"] is False
