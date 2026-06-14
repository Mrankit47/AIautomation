"""Tests for Pinterest Publishing integration and LangGraph node."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from backend.config.settings import Settings
from backend.models.artwork import Artwork, ArtworkStatus
from backend.graph.nodes import publish_pinterest
from backend.integrations.pinterest.client import PinterestClient
from backend.integrations.pinterest.exceptions import PinterestAPIError, PinterestAuthError


@pytest.fixture
def mock_artwork_id() -> uuid.UUID:
    return uuid.uuid4()


# ── Client Tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pinterest_client_auth_success() -> None:
    """Test PinterestClient authentication when credentials are configured."""
    with patch("backend.integrations.pinterest.client.get_settings") as mock_settings:
        mock_settings.return_value.pinterest.access_token.get_secret_value.return_value = "mock-token"
        mock_settings.return_value.pinterest.board_id = "mock-board"
        
        client = PinterestClient()
        # authenticate should not raise any errors
        await client.authenticate()
        assert client._access_token == "mock-token"
        assert client._board_id == "mock-board"
        await client.close()


@pytest.mark.asyncio
async def test_pinterest_client_auth_missing() -> None:
    """Test PinterestClient authentication raises when access token is missing."""
    with patch("backend.integrations.pinterest.client.get_settings") as mock_settings:
        mock_settings.return_value.pinterest.access_token = None
        
        client = PinterestClient()
        with pytest.raises(PinterestAuthError) as exc_info:
            await client.authenticate()
        assert "access token not configured" in str(exc_info.value)
        await client.close()


@pytest.mark.asyncio
async def test_pinterest_client_publish_image_success() -> None:
    """Test PinterestClient.publish_image successfully creates a pin."""
    with patch("backend.integrations.pinterest.client.get_settings") as mock_settings:
        mock_settings.return_value.pinterest.access_token.get_secret_value.return_value = "mock-token"
        mock_settings.return_value.pinterest.board_id = "mock-board-id"

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 201
        mock_resp.json = MagicMock(return_value={"id": "pin-123", "board_id": "mock-board-id"})
        mock_resp.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.post = AsyncMock(return_value=mock_resp)

        client = PinterestClient()
        client._http = mock_http_client

        result = await client.publish_image(
            image_url="http://mock/art.jpg",
            caption="Beautiful artwork",
            hashtags=["#art"],
            title="Artwork Title",
        )

        assert result.post_id == "pin-123"
        assert result.url == "https://www.pinterest.com/pin/pin-123/"
        assert result.platform == "pinterest"
        assert isinstance(result.published_at, datetime)
        mock_http_client.post.assert_called_once_with(
            "/pins",
            json={
                "board_id": "mock-board-id",
                "media_source": {
                    "source_type": "image_url",
                    "url": "http://mock/art.jpg",
                },
                "title": "Artwork Title",
                "description": "Beautiful artwork\n\n#art",
            }
        )
        await client.close()


@pytest.mark.asyncio
async def test_pinterest_client_publish_image_failure() -> None:
    """Test PinterestClient.publish_image raises PinterestAPIError on failure."""
    with patch("backend.integrations.pinterest.client.get_settings") as mock_settings:
        mock_settings.return_value.pinterest.access_token.get_secret_value.return_value = "mock-token"
        mock_settings.return_value.pinterest.board_id = "mock-board-id"

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        mock_resp.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Bad Request", request=MagicMock(), response=mock_resp))

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.post = AsyncMock(return_value=mock_resp)

        client = PinterestClient()
        client._http = mock_http_client

        with pytest.raises(PinterestAPIError) as exc_info:
            await client.publish_image(
                image_url="http://mock/art.jpg",
                caption="Beautiful artwork",
            )
        assert "Pinterest pin creation failed: Bad Request" in str(exc_info.value)
        await client.close()


@pytest.mark.asyncio
async def test_pinterest_client_get_analytics_success() -> None:
    """Test PinterestClient.get_post_analytics fetches analytics correctly."""
    with patch("backend.integrations.pinterest.client.get_settings") as mock_settings:
        mock_settings.return_value.pinterest.access_token.get_secret_value.return_value = "mock-token"

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={
            "all": {
                "IMPRESSION": 150,
                "PIN_CLICK": 25,
                "SAVE": 5,
                "OUTBOUND_CLICK": 10,
                "VIDEO_V50_WATCH_10S": 0,
            }
        })
        mock_resp.raise_for_status = MagicMock()

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get = AsyncMock(return_value=mock_resp)

        client = PinterestClient()
        client._http = mock_http_client

        analytics = await client.get_post_analytics("pin-123")
        assert analytics.post_id == "pin-123"
        assert analytics.impressions == 150
        assert analytics.reach == 25
        assert analytics.likes == 5
        assert analytics.shares == 10
        assert analytics.saves == 5
        await client.close()


@pytest.mark.asyncio
async def test_pinterest_client_health_check() -> None:
    """Test PinterestClient.health_check behavior."""
    with patch("backend.integrations.pinterest.client.get_settings") as mock_settings:
        mock_settings.return_value.pinterest.access_token.get_secret_value.return_value = "mock-token"

        mock_resp_ok = MagicMock(spec=httpx.Response)
        mock_resp_ok.status_code = 200

        mock_resp_err = MagicMock(spec=httpx.Response)
        mock_resp_err.status_code = 401

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.get = AsyncMock(side_effect=[mock_resp_ok, mock_resp_err])

        client = PinterestClient()
        client._http = mock_http_client

        # First call: OK (200)
        assert await client.health_check() is True
        
        # Second call: Error (401)
        assert await client.health_check() is False
        await client.close()


# ── LangGraph Workflow Node Tests ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_publish_pinterest_node_success(mock_artwork_id: uuid.UUID) -> None:
    """Test publish_pinterest node successfully publishes a pin and updates the DB."""
    workflow_id = str(uuid.uuid4())
    state = {
        "artwork_id": str(mock_artwork_id),
        "workflow_id": workflow_id,
        "workflow_version": "v1",
        "image_path": "artworks/sunflower.png",
        "storage_url": "http://mock/artworks/sunflower.png",
        "original_filename": "sunflower.png",
        "analysis": {},
        "metadata": {},
        "seo": {},
        "caption": "Sunflower artwork caption",
        "hashtags": ["#flower", "#nature"],
        "pinterest_status": "pending",
        "workflow_status": "running",
        "current_node": "generate_hashtags",
        "error_history": [],
        "messages": [],
    }

    from backend.integrations.base import PublishResult
    mock_publish_result = PublishResult(
        post_id="pin-sunflower-123",
        url="https://pinterest.com/pin/pin-sunflower-123",
        platform="pinterest",
        published_at=datetime.now(timezone.utc),
        raw_response={"id": "pin-sunflower-123"}
    )

    with patch("backend.database.session.get_sync_session") as mock_get_sync_session:
        mock_session_inst = MagicMock()
        mock_get_sync_session.return_value = mock_session_inst

        # Mock query return for Artwork model inside the node
        mock_artwork = Artwork(
            id=mock_artwork_id,
            storage_url="http://mock/artworks/sunflower.png",
            title="Sunflower Art",
            caption="Sunflower artwork caption",
            hashtags=["#flower", "#nature"],
        )
        mock_session_inst.execute.return_value.scalar_one_or_none.return_value = mock_artwork

        with patch("backend.integrations.pinterest.client.PinterestClient.publish_image", AsyncMock(return_value=mock_publish_result)):
            res = await publish_pinterest(state)

            assert res["pinterest_status"] == "published"
            assert res["current_node"] == "publish_pinterest"
            assert mock_session_inst.commit.called


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_publish_pinterest_node_retry_exhausted(mock_sleep: AsyncMock, mock_artwork_id: uuid.UUID) -> None:
    """Test publish_pinterest node retries on transient error and marks workflow as failed when exhausted."""
    workflow_id = str(uuid.uuid4())
    state = {
        "artwork_id": str(mock_artwork_id),
        "workflow_id": workflow_id,
        "workflow_version": "v1",
        "image_path": "artworks/sunflower.png",
        "storage_url": "http://mock/artworks/sunflower.png",
        "original_filename": "sunflower.png",
        "analysis": {},
        "metadata": {},
        "seo": {},
        "caption": "Sunflower artwork caption",
        "hashtags": ["#flower", "#nature"],
        "pinterest_status": "pending",
        "workflow_status": "running",
        "current_node": "generate_hashtags",
        "error_history": [],
        "messages": [],
    }

    with patch("backend.database.session.get_sync_session") as mock_get_sync_session:
        mock_session_inst = MagicMock()
        mock_get_sync_session.return_value = mock_session_inst

        mock_artwork = Artwork(
            id=mock_artwork_id,
            storage_url="http://mock/artworks/sunflower.png",
            title="Sunflower Art",
            caption="Sunflower artwork caption",
            hashtags=["#flower", "#nature"],
        )
        mock_session_inst.execute.return_value.scalar_one_or_none.return_value = mock_artwork

        # Mock publish_image to raise a transient error
        with patch("backend.integrations.pinterest.client.PinterestClient.publish_image", AsyncMock(side_effect=PinterestAPIError("Transient network failure"))):
            res = await publish_pinterest(state)

            assert res["pinterest_status"] == "failed"
            assert res["workflow_status"] == "failed"
            assert len(res["error_history"]) == 1
            assert "Transient network failure" in res["error_history"][0]["message"]
            assert mock_sleep.call_count == 3  # Retried 3 times
