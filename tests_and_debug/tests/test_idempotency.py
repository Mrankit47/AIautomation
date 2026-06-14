"""Unit/Integration tests for artwork idempotency (duplicate detection)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.artwork import Artwork, ArtworkStatus
from backend.services.artwork_service import ArtworkService
from backend.storage.base import StorageBackend, StorageResult


@pytest.fixture
def mock_storage() -> MagicMock:
    """Mock storage backend provider."""
    storage = MagicMock(spec=StorageBackend)
    storage.save = AsyncMock(
        return_value=StorageResult(
            path="artworks/mock-id.png",
            url="http://mock-storage/artworks/mock-id.png",
            size=1024,
            content_type="image/png",
        )
    )
    return storage


@pytest.mark.asyncio
async def test_duplicate_upload_returns_existing(
    mock_db_session: AsyncSession,
    mock_storage: MagicMock,
) -> None:
    """Test that uploading the same image twice returns the existing artwork."""
    service = ArtworkService(session=mock_db_session, storage=mock_storage)

    file_data = b"image-content-unique"
    expected_hash = hashlib.sha256(file_data).hexdigest()

    existing_art = Artwork(
        id=uuid.uuid4(),
        title="Existing Art",
        original_filename="art1.png",
        file_path="artworks/existing.png",
        storage_url="http://mock-storage/artworks/existing.png",
        file_size=len(file_data),
        mime_type="image/png",
        status=ArtworkStatus.UPLOADED,
        image_hash=expected_hash,
        source_url="http://original/url",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        workflow_runs=[],
    )

    # Mock DB filter_by to find the duplicate artwork
    service._repo.filter_by = AsyncMock(return_value=[existing_art])
    service._repo.create = AsyncMock()

    response = await service.upload_artwork(
        file_data=file_data,
        filename="art2.png",
        content_type="image/png",
        title="Another Name",
    )

    # Should not save or create new DB record
    mock_storage.save.assert_not_called()
    service._repo.create.assert_not_called()

    # Should return existing artwork
    assert response.id == existing_art.id
    assert response.image_hash == expected_hash
    assert response.title == "Existing Art"


@pytest.mark.asyncio
async def test_new_upload_creates_new_record(
    mock_db_session: AsyncSession,
    mock_storage: MagicMock,
) -> None:
    """Test that uploading a new image creates a new database record."""
    service = ArtworkService(session=mock_db_session, storage=mock_storage)

    file_data = b"new-image-content"
    expected_hash = hashlib.sha256(file_data).hexdigest()

    new_art = Artwork(
        id=uuid.uuid4(),
        title="New Art",
        original_filename="new.png",
        file_path="artworks/new.png",
        storage_url="http://mock-storage/artworks/new.png",
        file_size=len(file_data),
        mime_type="image/png",
        status=ArtworkStatus.UPLOADED,
        image_hash=expected_hash,
        source_url=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        workflow_runs=[],
    )

    # Mock DB filter_by to return empty list (no duplicate)
    service._repo.filter_by = AsyncMock(return_value=[])
    service._repo.create = AsyncMock(return_value=new_art)

    # Mock Celery/workflow auto trigger helper to avoid actual Celery dispatch crash
    service._auto_trigger_workflow = AsyncMock(return_value=(uuid.uuid4(), "mock-task-id"))

    response = await service.upload_artwork(
        file_data=file_data,
        filename="new.png",
        content_type="image/png",
        title="New Art",
    )

    mock_storage.save.assert_called_once()
    service._repo.create.assert_called_once()
    assert response.image_hash == expected_hash
    assert response.title == "New Art"
