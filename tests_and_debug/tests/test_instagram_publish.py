"""Tests for Instagram Reel Publishing feature."""

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import Settings
from backend.models.artwork import Artwork, ArtworkStatus
from backend.models.user import User
from backend.services.instagram_publisher import InstagramPublisher
from backend.graph.nodes import publish_instagram


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_artwork_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def mock_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def auth_headers() -> dict[str, str]:
    from backend.auth.jwt import JWTHandler
    handler = JWTHandler()
    user_id = str(uuid.uuid4())
    token = handler.create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


# ── Service Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_instagram_publisher_service_success() -> None:
    """Test InstagramPublisher publish_reel workflow under successful conditions."""
    # Settings/Environment mocking
    with patch.dict(os.environ, {
        "INSTAGRAM_ACCESS_TOKEN": "test-token",
        "INSTAGRAM_ACCOUNT_ID": "test-account-id"
    }):
        publisher = InstagramPublisher()
        publisher._upload_to_temp_host = AsyncMock(return_value="https://public-host/temp.mp4")

        # Mock responses using spec=httpx.Response to avoid coroutine issues
        mock_resp_create = MagicMock(spec=httpx.Response)
        mock_resp_create.json = MagicMock(return_value={"id": "container-123"})
        mock_resp_create.raise_for_status = MagicMock()
        mock_resp_create.status_code = 200

        mock_resp_poll1 = MagicMock(spec=httpx.Response)
        mock_resp_poll1.json = MagicMock(return_value={"status_code": "IN_PROGRESS"})
        mock_resp_poll1.raise_for_status = MagicMock()
        mock_resp_poll1.status_code = 200

        mock_resp_poll2 = MagicMock(spec=httpx.Response)
        mock_resp_poll2.json = MagicMock(return_value={"status_code": "FINISHED"})
        mock_resp_poll2.raise_for_status = MagicMock()
        mock_resp_poll2.status_code = 200

        mock_resp_publish = MagicMock(spec=httpx.Response)
        mock_resp_publish.json = MagicMock(return_value={"id": "post-987"})
        mock_resp_publish.raise_for_status = MagicMock()
        mock_resp_publish.status_code = 200

        mock_resp_permalink = MagicMock(spec=httpx.Response)
        mock_resp_permalink.json = MagicMock(return_value={"permalink": "https://instagram.com/reel/xyz"})
        mock_resp_permalink.raise_for_status = MagicMock()
        mock_resp_permalink.status_code = 200

        # Mock the client context manager
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(side_effect=[mock_resp_create, mock_resp_publish])
        mock_client.get = AsyncMock(side_effect=[mock_resp_poll1, mock_resp_poll2, mock_resp_permalink])

        # Create a temp reel file to pass validation
        reel_file = "temp_reel.mp4"
        with open(reel_file, "w") as f:
            f.write("mock-mp4-data")

        try:
            with patch("httpx.AsyncClient", return_value=mock_client):
                # We patch asyncio.sleep to speed up polling
                with patch("asyncio.sleep", AsyncMock()):
                    result = await publisher.publish_reel(
                        reel_path=reel_file,
                        caption="Check out this awesome AI Art! #aiart",
                    )

            assert result["instagram_post_id"] == "post-987"
            assert result["instagram_permalink"] == "https://instagram.com/reel/xyz"
            assert isinstance(result["instagram_published_at"], datetime)

            assert mock_client.post.call_count == 2
            assert mock_client.get.call_count == 3
        finally:
            if os.path.exists(reel_file):
                os.remove(reel_file)


# ── API Endpoint Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_instagram_api_endpoints(
    client: AsyncClient,
    mock_db_session: AsyncSession,
    mock_user: User,
    mock_artwork_id: uuid.UUID,
    auth_headers: dict[str, str],
) -> None:
    """Test POST /publish/instagram and GET /instagram-status endpoints."""
    # Mock current user lookup
    mock_db_session.get = AsyncMock(return_value=mock_user)

    # 1. Setup mock artwork
    mock_artwork = Artwork(
        id=mock_artwork_id,
        title="Sunset",
        original_filename="sunset.png",
        file_path="artworks/sunset.png",
        file_size=1024,
        mime_type="image/png",
        status=ArtworkStatus.PROCESSING,
        reel_path="outputs/reels/sunset.mp4",
        caption="Beautiful sunset caption",
        instagram_status="pending",
    )

    # Stub repository / DB execute returning this artwork
    mock_db_session.execute = AsyncMock()
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=mock_artwork)

    # Mock database update responses
    from backend.database.repository import BaseRepository
    BaseRepository.get_by_id = AsyncMock(return_value=mock_artwork)
    
    # We will mock the DB updates to modify mock_artwork dynamically
    async def mock_update_side_effect(id_, **kwargs):
        for k, v in kwargs.items():
            setattr(mock_artwork, k, v)
        return mock_artwork

    mock_update = AsyncMock(side_effect=mock_update_side_effect)
    BaseRepository.update = mock_update

    # Mock the publisher service
    mock_publish_result = {
        "instagram_post_id": "ig-post-12345",
        "instagram_permalink": "https://instagram.com/reel/sunset123",
        "instagram_published_at": datetime.now(timezone.utc),
    }
    
    with patch("backend.services.instagram_publisher.InstagramPublisher.publish_reel", AsyncMock(return_value=mock_publish_result)):
        # Trigger publish
        resp = await client.post(
            f"/api/v1/artworks/{mock_artwork_id}/publish/instagram",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["instagram_status"] == "published"
        assert data["instagram_post_id"] == "ig-post-12345"
        assert data["instagram_permalink"] == "https://instagram.com/reel/sunset123"

        # Now get status
        status_resp = await client.get(
            f"/api/v1/artworks/{mock_artwork_id}/instagram-status",
            headers=auth_headers,
        )

        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["instagram_status"] == "published"
        assert status_data["instagram_post_id"] == "ig-post-12345"
        assert status_data["instagram_permalink"] == "https://instagram.com/reel/sunset123"


# ── LangGraph Workflow Node Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_instagram_graph_node(
    mock_artwork_id: uuid.UUID,
) -> None:
    """Test the publish_instagram workflow node execution."""
    workflow_id = str(uuid.uuid4())
    state = {
        "artwork_id": str(mock_artwork_id),
        "workflow_id": workflow_id,
        "workflow_version": "v1",
        "image_path": "artworks/sunset.png",
        "storage_url": "http://mock/artworks/sunset.png",
        "original_filename": "sunset.png",
        "analysis": {},
        "metadata": {},
        "seo": {},
        "caption": "Workflow generated caption",
        "hashtags": ["#art"],
        "youtube_title": "Sunset",
        "youtube_description": "Sunset description",
        "reel_script": {},
        "reel_path": "outputs/reels/sunset.mp4",
        "instagram_status": "pending",
        "workflow_status": "running",
        "current_node": "generate_reel",
        "error_history": [],
        "messages": [],
    }

    mock_publish_result = {
        "instagram_post_id": "ig-workflow-post-id",
        "instagram_permalink": "https://instagram.com/reel/workflow",
        "instagram_published_at": datetime.now(timezone.utc),
    }

    # Mock the internal DB session updates for workflow nodes
    with patch("backend.database.session.get_sync_session") as mock_get_sync_session:
        mock_session_inst = MagicMock()
        mock_get_sync_session.return_value = mock_session_inst

        # Mock query return for Artwork model inside the node
        mock_artwork = Artwork(
            id=mock_artwork_id,
            reel_path="outputs/reels/sunset.mp4",
            caption="Workflow generated caption",
        )
        mock_session_inst.execute.return_value.scalar_one_or_none.return_value = mock_artwork

        # Mock the publisher service
        with patch("backend.services.instagram_publisher.InstagramPublisher.publish_reel", AsyncMock(return_value=mock_publish_result)):
            res = await publish_instagram(state)

            assert res["instagram_status"] == "published"
            assert res["current_node"] == "publish_instagram"

            # Check database commit was called
            assert mock_session_inst.commit.called
