"""Tests for Instagram analytics collection."""

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from backend.models.artwork import Artwork, ArtworkStatus
from backend.services.instagram_analytics import InstagramAnalyticsService
from backend.graph.nodes import collect_analytics
from backend.integrations.instagram.exceptions import InstagramAuthError


@pytest.fixture
def mock_artwork_id() -> uuid.UUID:
    return uuid.uuid4()


# ── Service Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_instagram_analytics_service_success() -> None:
    """Test InstagramAnalyticsService collect_metrics under successful conditions."""
    with patch.dict(os.environ, {
        "INSTAGRAM_ACCESS_TOKEN": "test-token",
        "INSTAGRAM_ACCOUNT_ID": "test-account-id",
    }):
        service = InstagramAnalyticsService()

        # Mock organic media response (likes, comments)
        mock_resp_media = MagicMock(spec=httpx.Response)
        mock_resp_media.json = MagicMock(return_value={
            "like_count": 120,
            "comments_count": 15,
            "id": "ig-media-987",
        })
        mock_resp_media.raise_for_status = MagicMock()
        mock_resp_media.status_code = 200

        # Mock insights response
        mock_resp_insights = MagicMock(spec=httpx.Response)
        mock_resp_insights.json = MagicMock(return_value={
            "data": [
                {"name": "reach", "values": [{"value": 500}]},
                {"name": "impressions", "values": [{"value": 650}]},
                {"name": "saved", "values": [{"value": 30}]},
                {"name": "shares", "values": [{"value": 12}]},
                {"name": "plays", "values": [{"value": 600}]},
            ]
        })
        mock_resp_insights.raise_for_status = MagicMock()
        mock_resp_insights.status_code = 200

        # Mock Client
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(side_effect=[mock_resp_media, mock_resp_insights])

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await service.collect_metrics(media_id="ig-media-987")

        assert result["views"] == 600
        assert result["reach"] == 500
        assert result["impressions"] == 650
        assert result["likes"] == 120
        assert result["comments"] == 15
        assert result["shares"] == 12
        assert result["saves"] == 30
        # Engagement: (120 + 15 + 12 + 30) / 500 = 177 / 500 = 0.3540
        assert result["engagement_rate"] == 0.354
        assert isinstance(result["collected_at"], datetime)


@pytest.mark.asyncio
async def test_instagram_analytics_service_missing_auth() -> None:
    """Test service raises error when auth credentials are not set."""
    with patch.dict(os.environ, {
        "INSTAGRAM_ACCESS_TOKEN": "",
        "INSTAGRAM_ACCOUNT_ID": "",
    }, clear=True):
        # Temporarily bypass setting fallback values to guarantee failure
        with patch("backend.services.instagram_analytics.get_settings") as mock_settings:
            mock_inst = MagicMock()
            mock_inst.instagram.access_token = None
            mock_inst.instagram.account_id = ""
            mock_settings.return_value = mock_inst

            service = InstagramAnalyticsService()
            with pytest.raises(InstagramAuthError):
                await service.collect_metrics(media_id="ig-media-987")


# ── Graph Node Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_collect_analytics_graph_node_instagram(
    mock_artwork_id: uuid.UUID,
) -> None:
    """Test collect_analytics graph node retrieves and persists Instagram metrics."""
    workflow_id = str(uuid.uuid4())
    state = {
        "artwork_id": str(mock_artwork_id),
        "workflow_id": workflow_id,
        "workflow_version": "v1",
        "image_path": "artworks/test.png",
        "storage_url": "http://mock/test.png",
        "original_filename": "test.png",
        "analysis": {},
        "metadata": {},
        "seo": {},
        "caption": "Workflow caption",
        "hashtags": ["#art"],
        "youtube_title": "YouTube Title",
        "youtube_description": "YouTube Desc",
        "reel_script": {},
        "reel_path": "outputs/reels/test.mp4",
        "instagram_status": "published",
        "youtube_status": None,
        "workflow_status": "running",
        "current_node": "publish_youtube",
        "error_history": [],
        "messages": [],
    }

    mock_metrics_result = {
        "views": 450,
        "reach": 400,
        "impressions": 420,
        "likes": 88,
        "comments": 12,
        "shares": 8,
        "saves": 5,
        "watch_time": 0.0,
        "engagement_rate": 0.2825,
        "collected_at": datetime.now(timezone.utc),
    }

    with patch("backend.database.session.get_sync_session") as mock_get_sync_session:
        mock_session_inst = MagicMock()
        mock_get_sync_session.return_value = mock_session_inst

        # Mock query return for Artwork model
        mock_artwork = Artwork(
            id=mock_artwork_id,
            instagram_status="published",
            instagram_post_id="ig-post-xyz",
            youtube_status=None,
        )
        mock_session_inst.execute.return_value.scalar_one_or_none.return_value = mock_artwork

        with patch("backend.services.instagram_analytics.InstagramAnalyticsService.collect_metrics", AsyncMock(return_value=mock_metrics_result)):
            res = await collect_analytics(state)

            assert res["current_node"] == "collect_analytics"
            assert res["workflow_status"] == "completed"

            # Check database commit was called and session added analytics row
            assert mock_session_inst.add.called
            assert mock_session_inst.commit.called
