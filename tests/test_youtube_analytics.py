"""Tests for YouTube Shorts analytics collection."""

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from backend.models.artwork import Artwork
from backend.services.youtube_analytics import YouTubeAnalyticsService
from backend.graph.nodes import collect_analytics
from backend.integrations.youtube.exceptions import YouTubeAuthError


@pytest.fixture
def mock_artwork_id() -> uuid.UUID:
    return uuid.uuid4()


# ── Service Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_youtube_analytics_service_success() -> None:
    """Test YouTubeAnalyticsService collect_metrics under successful conditions."""
    with patch.dict(os.environ, {
        "YOUTUBE_CLIENT_ID": "test-client",
        "YOUTUBE_CLIENT_SECRET": "test-secret",
        "YOUTUBE_REFRESH_TOKEN": "test-refresh",
    }):
        service = YouTubeAnalyticsService()

        # Mock OAuth response
        mock_resp_oauth = MagicMock(spec=httpx.Response)
        mock_resp_oauth.json = MagicMock(return_value={"access_token": "mock-yt-token"})
        mock_resp_oauth.raise_for_status = MagicMock()
        mock_resp_oauth.status_code = 200

        # Mock Data API response (views, likes, comments)
        mock_resp_data = MagicMock(spec=httpx.Response)
        mock_resp_data.json = MagicMock(return_value={
            "items": [{
                "statistics": {
                    "viewCount": "1200",
                    "likeCount": "95",
                    "commentCount": "8",
                }
            }]
        })
        mock_resp_data.raise_for_status = MagicMock()
        mock_resp_data.status_code = 200

        # Mock Analytics API response (watch time, duration)
        mock_resp_reports = MagicMock(spec=httpx.Response)
        mock_resp_reports.json = MagicMock(return_value={
            "columnHeaders": [
                {"name": "estimatedMinutesWatched"},
                {"name": "averageViewDuration"},
            ],
            "rows": [
                [75.5, 45.0]
            ]
        })
        mock_resp_reports.raise_for_status = MagicMock()
        mock_resp_reports.status_code = 200

        # Mock Client
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_resp_oauth)
        mock_client.get = AsyncMock(side_effect=[mock_resp_data, mock_resp_reports])

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await service.collect_metrics(video_id="yt-video-123")

        assert result["views"] == 1200
        assert result["likes"] == 95
        assert result["comments"] == 8
        assert result["watch_time"] == 75.5
        # Engagement: (95 + 8) / 1200 = 103 / 1200 = 0.0858
        assert result["engagement_rate"] == 0.0858


@pytest.mark.asyncio
async def test_youtube_analytics_service_reports_failure_fallback() -> None:
    """Test service tolerates Analytics reports API failure, fallback to 0 for watch time."""
    with patch.dict(os.environ, {
        "YOUTUBE_CLIENT_ID": "test-client",
        "YOUTUBE_CLIENT_SECRET": "test-secret",
        "YOUTUBE_REFRESH_TOKEN": "test-refresh",
    }):
        service = YouTubeAnalyticsService()

        # Mock OAuth
        mock_resp_oauth = MagicMock(spec=httpx.Response)
        mock_resp_oauth.json = MagicMock(return_value={"access_token": "mock-yt-token"})
        mock_resp_oauth.raise_for_status = MagicMock()
        mock_resp_oauth.status_code = 200

        # Mock Data API stats
        mock_resp_data = MagicMock(spec=httpx.Response)
        mock_resp_data.json = MagicMock(return_value={
            "items": [{
                "statistics": {
                    "viewCount": "100",
                    "likeCount": "5",
                    "commentCount": "1",
                }
            }]
        })
        mock_resp_data.raise_for_status = MagicMock()
        mock_resp_data.status_code = 200

        # Mock Analytics API failing with 403 Forbidden
        mock_resp_reports = MagicMock(spec=httpx.Response)
        mock_resp_reports.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=mock_resp_reports))
        mock_resp_reports.status_code = 403

        # Mock Client
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_resp_oauth)
        mock_client.get = AsyncMock(side_effect=[mock_resp_data, mock_resp_reports])

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await service.collect_metrics(video_id="yt-video-123")

        # Basic stats should still be populated successfully
        assert result["views"] == 100
        assert result["likes"] == 5
        assert result["comments"] == 1
        assert result["watch_time"] == 0.0  # fell back gracefully
        assert result["engagement_rate"] == 0.06


# ── Graph Node Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_collect_analytics_graph_node_youtube(
    mock_artwork_id: uuid.UUID,
) -> None:
    """Test collect_analytics graph node retrieves and persists YouTube metrics."""
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
        "instagram_status": None,
        "youtube_status": "published",
        "workflow_status": "running",
        "current_node": "publish_youtube",
        "error_history": [],
        "messages": [],
    }

    mock_metrics_result = {
        "views": 800,
        "reach": 800,
        "impressions": 800,
        "likes": 50,
        "comments": 6,
        "shares": 0,
        "saves": 0,
        "watch_time": 40.5,
        "engagement_rate": 0.07,
        "collected_at": datetime.now(timezone.utc),
    }

    with patch("backend.database.session.get_sync_session") as mock_get_sync_session:
        mock_session_inst = MagicMock()
        mock_get_sync_session.return_value = mock_session_inst

        # Mock query return for Artwork model
        mock_artwork = Artwork(
            id=mock_artwork_id,
            instagram_status=None,
            youtube_status="published",
            youtube_video_id="yt-video-999",
            youtube_published_at=datetime.now(timezone.utc),
        )
        mock_session_inst.execute.return_value.scalar_one_or_none.return_value = mock_artwork

        with patch("backend.services.youtube_analytics.YouTubeAnalyticsService.collect_metrics", AsyncMock(return_value=mock_metrics_result)):
            res = await collect_analytics(state)

            assert res["current_node"] == "collect_analytics"
            assert res["workflow_status"] == "completed"

            # Check database commit was called and session added analytics row
            assert mock_session_inst.add.called
            assert mock_session_inst.commit.called
