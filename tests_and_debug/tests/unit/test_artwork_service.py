"""Unit tests for the ArtworkService business logic."""

from datetime import datetime, timezone
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import NotFoundException, ValidationException
from backend.models.artwork import Artwork, ArtworkStatus
from backend.schemas.artwork import ArtworkResponse
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
    storage.load = AsyncMock(return_value=b"filebytes")
    storage.delete = AsyncMock()
    storage.exists = AsyncMock(return_value=True)
    return storage


@pytest.mark.asyncio
async def test_upload_artwork_success(mock_db_session: AsyncSession, mock_storage: MagicMock) -> None:
    """Test successful upload of a valid artwork file."""
    service = ArtworkService(session=mock_db_session, storage=mock_storage)

    # Mock DB insert / repo.create
    mock_artwork = Artwork(
        id=uuid.uuid4(),
        title="My Art",
        original_filename="art.png",
        file_path="artworks/mock-id.png",
        storage_url="http://mock-storage/artworks/mock-id.png",
        file_size=1024,
        mime_type="image/png",
        status=ArtworkStatus.UPLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    # We monkeypatch repository.create or database session calls
    service._repo.create = AsyncMock(return_value=mock_artwork)

    response = await service.upload_artwork(
        file_data=b"filebytes",
        filename="art.png",
        content_type="image/png",
        title="My Art",
    )

    assert isinstance(response, ArtworkResponse)
    assert response.title == "My Art"
    assert response.status == ArtworkStatus.UPLOADED
    mock_storage.save.assert_called_once()


@pytest.mark.asyncio
async def test_upload_artwork_invalid_mime_type(mock_db_session: AsyncSession, mock_storage: MagicMock) -> None:
    """Test that uploading a file with an unsupported mime type raises ValidationException."""
    service = ArtworkService(session=mock_db_session, storage=mock_storage)

    with pytest.raises(ValidationException):
        await service.upload_artwork(
            file_data=b"bytes",
            filename="doc.txt",
            content_type="text/plain",
        )


@pytest.mark.asyncio
async def test_get_artwork_not_found(mock_db_session: AsyncSession, mock_storage: MagicMock) -> None:
    """Test retrieving a non-existent artwork raises NotFoundException."""
    service = ArtworkService(session=mock_db_session, storage=mock_storage)
    service._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundException):
        await service.get_artwork(uuid.uuid4())


@pytest.mark.asyncio
async def test_upload_artwork_heic_conversion(mock_db_session: AsyncSession, mock_storage: MagicMock) -> None:
    """Test that uploading an HEIC file automatically converts it to JPEG."""
    service = ArtworkService(session=mock_db_session, storage=mock_storage)

    # Mock DB insert / repo.create
    mock_artwork = Artwork(
        id=uuid.uuid4(),
        title="HEIC Art",
        original_filename="art.jpg",
        file_path="artworks/mock-id.jpg",
        storage_url="http://mock-storage/artworks/mock-id.jpg",
        file_size=512,
        mime_type="image/jpeg",
        status=ArtworkStatus.UPLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    service._repo.create = AsyncMock(return_value=mock_artwork)

    # Mock pillow_heif and PIL Image
    with patch("pillow_heif.register_heif_opener") as mock_register, \
         patch("PIL.Image.open") as mock_open:
        
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        
        response = await service.upload_artwork(
            file_data=b"fake-heic-bytes",
            filename="art.heic",
            content_type="image/heic",
            title="HEIC Art",
        )
        
        assert mock_register.called
        assert mock_open.called
        mock_img.convert.assert_called_with("RGB")
        mock_img.convert().save.assert_called_once()
        assert response.status == ArtworkStatus.UPLOADED
