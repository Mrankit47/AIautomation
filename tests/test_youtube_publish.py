"""Tests for YouTube Shorts Publishing feature."""

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
from backend.services.youtube_publisher import YouTubePublisher
from backend.graph.nodes import publish_youtube
from backend.integrations.youtube.exceptions import YouTubeAuthError


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
async def test_youtube_publisher_service_success() -> None:
    """Test YouTubePublisher publish_short workflow under successful conditions."""
    # Settings/Environment mocking
    with patch.dict(os.environ, {
        "YOUTUBE_CLIENT_ID": "test-client-id",
        "YOUTUBE_CLIENT_SECRET": "test-client-secret",
        "YOUTUBE_REFRESH_TOKEN": "test-refresh-token",
    }):
        publisher = YouTubePublisher()

        # Mock responses using spec=httpx.Response to avoid coroutine issues
        mock_resp_oauth = MagicMock(spec=httpx.Response)
        mock_resp_oauth.json = MagicMock(return_value={"access_token": "mock-access-token"})
        mock_resp_oauth.raise_for_status = MagicMock()
        mock_resp_oauth.status_code = 200

        mock_resp_init = MagicMock(spec=httpx.Response)
        mock_resp_init.headers = {"Location": "https://upload.youtube.com/upload/session-xyz"}
        mock_resp_init.raise_for_status = MagicMock()
        mock_resp_init.status_code = 200

        mock_resp_upload = MagicMock(spec=httpx.Response)
        mock_resp_upload.json = MagicMock(return_value={"id": "yt-video-123"})
        mock_resp_upload.raise_for_status = MagicMock()
        mock_resp_upload.status_code = 200

        # Mock the client context manager
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(side_effect=[mock_resp_oauth, mock_resp_init])
        mock_client.put = AsyncMock(return_value=mock_resp_upload)

        # Create a temp reel file to pass validation
        reel_file = "temp_youtube_reel.mp4"
        with open(reel_file, "w") as f:
            f.write("mock-mp4-data")

        try:
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await publisher.publish_short(
                    reel_path=reel_file,
                    title="Amazing AI Art!",
                    description="Check out this awesome AI Art!",
                )

            assert result["youtube_video_id"] == "yt-video-123"
            assert result["youtube_url"] == "https://youtube.com/shorts/yt-video-123"
            assert isinstance(result["youtube_published_at"], datetime)

            assert mock_client.post.call_count == 2
            assert mock_client.put.call_count == 1
        finally:
            if os.path.exists(reel_file):
                os.remove(reel_file)


@pytest.mark.asyncio
async def test_youtube_publisher_service_missing_credentials() -> None:
    """Test service error when Google OAuth credentials are not fully configured."""
    with patch.dict(os.environ, {
        "YOUTUBE_CLIENT_ID": "",
        "YOUTUBE_CLIENT_SECRET": "",
        "YOUTUBE_REFRESH_TOKEN": "",
    }, clear=True):
        # Temporarily bypass setting fallback values to guarantee failure
        with patch("backend.services.youtube_publisher.get_settings") as mock_settings:
            mock_inst = MagicMock()
            mock_inst.youtube.client_id = ""
            mock_inst.youtube.client_secret = None
            mock_inst.youtube.refresh_token = None
            mock_settings.return_value = mock_inst

            publisher = YouTubePublisher()

            reel_file = "temp_youtube_reel.mp4"
            with open(reel_file, "w") as f:
                f.write("mock-mp4-data")

            try:
                with pytest.raises(YouTubeAuthError) as exc_info:
                    await publisher.publish_short(
                        reel_path=reel_file,
                        title="Art",
                        description="Desc",
                    )
                assert "credentials" in str(exc_info.value)
            finally:
                if os.path.exists(reel_file):
                    os.remove(reel_file)


@pytest.mark.asyncio
async def test_youtube_publisher_service_token_failure() -> None:
    """Test service failure when OAuth endpoint returns an error."""
    with patch.dict(os.environ, {
        "YOUTUBE_CLIENT_ID": "test-client-id",
        "YOUTUBE_CLIENT_SECRET": "test-client-secret",
        "YOUTUBE_REFRESH_TOKEN": "test-refresh-token",
    }):
        publisher = YouTubePublisher()

        # Mock token request failure
        mock_resp_oauth = MagicMock(spec=httpx.Response)
        mock_resp_oauth.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Auth failed", request=MagicMock(), response=mock_resp_oauth))
        mock_resp_oauth.status_code = 400

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_resp_oauth)

        reel_file = "temp_youtube_reel.mp4"
        with open(reel_file, "w") as f:
            f.write("mock-mp4-data")

        try:
            with patch("httpx.AsyncClient", return_value=mock_client):
                with pytest.raises(YouTubeAuthError):
                    await publisher.publish_short(
                        reel_path=reel_file,
                        title="Art",
                        description="Desc",
                    )
        finally:
            if os.path.exists(reel_file):
                os.remove(reel_file)


# ── API Endpoint Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_youtube_api_endpoints(
    client: AsyncClient,
    mock_db_session: AsyncSession,
    mock_user: User,
    mock_artwork_id: uuid.UUID,
    auth_headers: dict[str, str],
) -> None:
    """Test POST /publish/youtube and GET /youtube-status endpoints."""
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
        youtube_title="Sunset Short",
        youtube_description="Sunset description",
        youtube_status="pending",
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
        "youtube_video_id": "yt-endpoint-123",
        "youtube_url": "https://youtube.com/shorts/yt-endpoint-123",
        "youtube_published_at": datetime.now(timezone.utc),
    }
    
    with patch("backend.services.youtube_publisher.YouTubePublisher.publish_short", AsyncMock(return_value=mock_publish_result)):
        # Trigger publish
        resp = await client.post(
            f"/api/v1/artworks/{mock_artwork_id}/publish/youtube",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["youtube_status"] == "published"
        assert data["youtube_video_id"] == "yt-endpoint-123"
        assert data["youtube_url"] == "https://youtube.com/shorts/yt-endpoint-123"

        # Now get status
        status_resp = await client.get(
            f"/api/v1/artworks/{mock_artwork_id}/youtube-status",
            headers=auth_headers,
        )

        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["youtube_status"] == "published"
        assert status_data["youtube_video_id"] == "yt-endpoint-123"
        assert status_data["youtube_url"] == "https://youtube.com/shorts/yt-endpoint-123"


# ── LangGraph Workflow Node Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_youtube_graph_node(
    mock_artwork_id: uuid.UUID,
) -> None:
    """Test the publish_youtube workflow node execution."""
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
        "youtube_status": "pending",
        "workflow_status": "running",
        "current_node": "generate_reel",
        "error_history": [],
        "messages": [],
    }

    mock_publish_result = {
        "youtube_video_id": "yt-workflow-video-id",
        "youtube_url": "https://youtube.com/shorts/yt-workflow-video-id",
        "youtube_published_at": datetime.now(timezone.utc),
    }

    # Mock the internal DB session updates for workflow nodes
    with patch("backend.database.session.get_sync_session") as mock_get_sync_session:
        mock_session_inst = MagicMock()
        mock_get_sync_session.return_value = mock_session_inst

        # Mock query return for Artwork model inside the node
        mock_artwork = Artwork(
            id=mock_artwork_id,
            reel_path="outputs/reels/sunset.mp4",
            youtube_title="Sunset",
            youtube_description="Sunset description",
        )
        mock_session_inst.execute.return_value.scalar_one_or_none.return_value = mock_artwork

        # Mock the publisher service
        with patch("backend.services.youtube_publisher.YouTubePublisher.publish_short", AsyncMock(return_value=mock_publish_result)):
            res = await publish_youtube(state)

            assert res["youtube_status"] == "published"
            assert res["current_node"] == "publish_youtube"

            # Check database commit was called
            assert mock_session_inst.commit.called
