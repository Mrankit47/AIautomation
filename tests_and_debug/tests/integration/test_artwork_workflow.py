from datetime import datetime, timezone
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt import JWTHandler
from backend.models.artwork import Artwork, ArtworkStatus
from backend.models.user import User
from backend.models.workflow_run import WorkflowRun, WorkflowStatus


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Provide authorization headers with a mock JWT access token."""
    handler = JWTHandler()
    user_id = str(uuid.uuid4())
    token = handler.create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_upload_artwork_api(
    client: AsyncClient,
    mock_db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Test uploading artwork via the API with valid JWT authorization."""
    # Mock current user lookup
    mock_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_db_session.get = AsyncMock(return_value=mock_user)

    # Mock database insert for repository
    artwork_id = uuid.uuid4()
    mock_artwork = Artwork(
        id=artwork_id,
        title="Sunset Title",
        original_filename="sunset.png",
        file_path="artworks/sunset.png",
        storage_url="http://mock-storage/artworks/sunset.png",
        file_size=100,
        mime_type="image/png",
        status=ArtworkStatus.UPLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=mock_artwork)

    # We mock service and repository calls
    from backend.services.artwork_service import ArtworkService
    mock_upload = AsyncMock(return_value=mock_artwork)
    mock_db_session.add = MagicMock()

    files = {"file": ("sunset.png", b"fake-file-content", "image/png")}
    data = {"title": "Sunset Title"}

    # We mock the service's upload_artwork directly in dependency overrides if needed,
    # or let the real service call mock_repo and mock_storage.
    # Since we mocked mock_db_session.get and repository functions, we let the service run.
    from backend.database.repository import BaseRepository
    BaseRepository.create = AsyncMock(return_value=mock_artwork)
    BaseRepository.filter_by = AsyncMock(return_value=[])

    with patch("backend.services.artwork_service.ArtworkService._auto_trigger_workflow") as mock_trigger:
        mock_trigger.return_value = (uuid.uuid4(), "mock-task-id")

        response = await client.post(
            "/api/v1/artworks/upload",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["original_filename"] == "sunset.png"


@pytest.mark.asyncio
async def test_trigger_workflow_api(
    client: AsyncClient,
    mock_db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Test triggering processing workflow via the API."""
    mock_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_db_session.get = AsyncMock(return_value=mock_user)

    # Mock get artwork by id
    artwork_id = uuid.uuid4()
    mock_artwork = Artwork(
        id=artwork_id,
        title="Sunset Title",
        original_filename="sunset.png",
        file_path="artworks/sunset.png",
        storage_url="http://mock-storage/artworks/sunset.png",
        file_size=100,
        mime_type="image/png",
        status=ArtworkStatus.UPLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Mock repo filter/get calls
    from backend.database.repository import BaseRepository
    BaseRepository.get_by_id = AsyncMock(return_value=mock_artwork)
    BaseRepository.filter_by = AsyncMock(return_value=[])  # no active runs

    # Mock workflow run creation
    workflow_run_id = uuid.uuid4()
    mock_workflow_run = WorkflowRun(
        id=workflow_run_id,
        artwork_id=artwork_id,
        workflow_version="v1",
        status=WorkflowStatus.PENDING,
        error_history=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    BaseRepository.create = AsyncMock(return_value=mock_workflow_run)
    BaseRepository.update = AsyncMock(return_value=mock_workflow_run)

    response = await client.post(
        f"/api/v1/artworks/{artwork_id}/process",
        json={"workflow_version": "v1"},
        headers=auth_headers,
    )

    assert response.status_code == 202
    assert response.json()["status"] == "PENDING"
    assert "celery_task_id" in response.json()


@pytest.mark.asyncio
async def test_get_analysis_api(
    client: AsyncClient,
    mock_db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Test retrieving artwork analysis data via API."""
    mock_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
    )
    mock_db_session.get = AsyncMock(return_value=mock_user)

    artwork_id = uuid.uuid4()
    mock_artwork = Artwork(
        id=artwork_id,
        title="Sunset Title",
        original_filename="sunset.png",
        file_path="artworks/sunset.png",
        file_size=100,
        mime_type="image/png",
        status=ArtworkStatus.PROCESSING,
        analysis_data={"style": "Impressionism", "mood": "calm"},
    )

    from backend.database.repository import BaseRepository
    BaseRepository.get_by_id = AsyncMock(return_value=mock_artwork)

    response = await client.get(
        f"/api/v1/artworks/{artwork_id}/analysis",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["analysis_data"]["style"] == "Impressionism"


@pytest.mark.asyncio
async def test_get_seo_api(
    client: AsyncClient,
    mock_db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Test retrieving artwork SEO data via API."""
    mock_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
    )
    mock_db_session.get = AsyncMock(return_value=mock_user)

    artwork_id = uuid.uuid4()
    mock_artwork = Artwork(
        id=artwork_id,
        title="Sunset Title",
        original_filename="sunset.png",
        file_path="artworks/sunset.png",
        file_size=100,
        mime_type="image/png",
        status=ArtworkStatus.PROCESSING,
        seo_data={"seo_title": "Optimized Title", "keywords": ["sunset"]},
    )

    from backend.database.repository import BaseRepository
    BaseRepository.get_by_id = AsyncMock(return_value=mock_artwork)

    response = await client.get(
        f"/api/v1/artworks/{artwork_id}/seo",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["seo_data"]["seo_title"] == "Optimized Title"


@pytest.mark.asyncio
async def test_get_caption_api(
    client: AsyncClient,
    mock_db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Test retrieving artwork caption via API."""
    mock_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
    )
    mock_db_session.get = AsyncMock(return_value=mock_user)

    artwork_id = uuid.uuid4()
    mock_artwork = Artwork(
        id=artwork_id,
        title="Sunset Title",
        original_filename="sunset.png",
        file_path="artworks/sunset.png",
        file_size=100,
        mime_type="image/png",
        status=ArtworkStatus.PROCESSING,
        caption="A beautiful sunset",
        youtube_title="Sunset Youtube Title",
        youtube_description="Sunset Youtube Description",
    )

    from backend.database.repository import BaseRepository
    BaseRepository.get_by_id = AsyncMock(return_value=mock_artwork)

    response = await client.get(
        f"/api/v1/artworks/{artwork_id}/caption",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["caption"] == "A beautiful sunset"
    assert response.json()["youtube_title"] == "Sunset Youtube Title"


@pytest.mark.asyncio
async def test_get_hashtags_api(
    client: AsyncClient,
    mock_db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Test retrieving artwork hashtags via API."""
    mock_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
    )
    mock_db_session.get = AsyncMock(return_value=mock_user)

    artwork_id = uuid.uuid4()
    mock_artwork = Artwork(
        id=artwork_id,
        title="Sunset Title",
        original_filename="sunset.png",
        file_path="artworks/sunset.png",
        file_size=100,
        mime_type="image/png",
        status=ArtworkStatus.PROCESSING,
        hashtags=["sunset", "art"],
    )

    from backend.database.repository import BaseRepository
    BaseRepository.get_by_id = AsyncMock(return_value=mock_artwork)

    response = await client.get(
        f"/api/v1/artworks/{artwork_id}/hashtags",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["hashtags"] == ["sunset", "art"]


@pytest.mark.asyncio
async def test_get_reel_api(
    client: AsyncClient,
    mock_db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Test retrieving artwork reel script via API."""
    mock_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
    )
    mock_db_session.get = AsyncMock(return_value=mock_user)

    artwork_id = uuid.uuid4()
    mock_artwork = Artwork(
        id=artwork_id,
        title="Sunset Title",
        original_filename="sunset.png",
        file_path="artworks/sunset.png",
        file_size=100,
        mime_type="image/png",
        status=ArtworkStatus.PROCESSING,
        reel_script={"hook": "Watch this!", "script": "narration"},
    )

    from backend.database.repository import BaseRepository
    BaseRepository.get_by_id = AsyncMock(return_value=mock_artwork)

    response = await client.get(
        f"/api/v1/artworks/{artwork_id}/reel",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["reel_script"]["hook"] == "Watch this!"
