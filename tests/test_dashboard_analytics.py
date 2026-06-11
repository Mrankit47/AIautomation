"""Tests for dashboard analytics, top performers, and AI recommendations."""

import uuid
from datetime import datetime, timezone, date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.artwork import Artwork, ArtworkStatus
from backend.models.analytics import ArtworkAnalytics
from backend.models.user import User
from backend.services.ai_recommendations import AIRecommendationService


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


# ── AI Recommendation Service Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_recommendations_fallback_when_no_data(mock_db_session: AsyncSession) -> None:
    """Test AIRecommendationService returns presets when no DB records are available."""
    # Mock database executing returning empty list
    mock_db_session.execute = AsyncMock()
    mock_db_session.execute.return_value.all = MagicMock(return_value=[])

    service = AIRecommendationService()
    result = await service.generate_recommendations(mock_db_session)

    assert "baseline" in result["rationale"]
    assert "best_posting_time" in result
    assert "best_platform" in result


@pytest.mark.asyncio
async def test_ai_recommendations_success_with_llm(mock_db_session: AsyncSession) -> None:
    """Test AIRecommendationService successfully compiles dataset and triggers Gemini."""
    # Mock analytics + artwork records in DB
    mock_art = Artwork(
        id=uuid.uuid4(),
        title="My Generative Landscape",
        hashtags=["#aiart", "#landscape"],
        analysis_data={"subjects": ["landscape", "abstract"]},
        instagram_published_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        original_filename="landscape.png",
        file_path="artworks/landscape.png",
        file_size=1024,
        mime_type="image/png",
    )
    mock_analytics = ArtworkAnalytics(
        artwork_id=mock_art.id,
        platform="instagram",
        views=1500,
        reach=1500,
        impressions=1500,
        likes=120,
        comments=15,
        shares=10,
        saves=5,
        watch_time=0.0,
        engagement_rate=0.09,
        collected_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_db_session.execute = AsyncMock()
    mock_db_session.execute.return_value.all = MagicMock(return_value=[(mock_analytics, mock_art)])

    mock_llm_response = {
        "best_posting_time": "Sunday at 6:00 PM",
        "best_platform": "Instagram Reels",
        "best_hashtag_patterns": "Use 5 custom tags",
        "best_artwork_category": "Landscapes",
        "rationale": "High engagement on landscapes on Sunday evening.",
    }

    from backend.providers.base import AIStructuredResult
    mock_structured_res = AIStructuredResult(
        data=mock_llm_response,
        model="gemini",
        usage={},
    )

    service = AIRecommendationService()
    
    with patch.object(service._provider, "generate_structured", AsyncMock(return_value=mock_structured_res)) as mock_gemini:
        result = await service.generate_recommendations(mock_db_session)

        assert result["best_posting_time"] == "Sunday at 6:00 PM"
        assert result["best_platform"] == "Instagram Reels"
        assert mock_gemini.called


# ── FastAPI Router Endpoints Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_dashboard_analytics_api_endpoints(
    client: AsyncClient,
    mock_db_session: AsyncSession,
    mock_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test GET /api/v1/dashboard/analytics endpoint returns combined dashboard metrics."""
    mock_db_session.get = AsyncMock(return_value=mock_user)

    # 1. Mock Summary Result
    mock_summary_row = MagicMock()
    mock_summary_row.views = 10000
    mock_summary_row.likes = 850
    mock_summary_row.comments = 110
    mock_summary_row.reach = 8000
    mock_summary_row.impressions = 9500
    mock_summary_row.posts = 5

    # 2. Mock Daily Views rows
    mock_view_row = MagicMock()
    mock_view_row.date = date(2026, 6, 10)
    mock_view_row.views = 5000
    mock_view_row.platform = "youtube"

    # 3. Mock Daily Engagement rows
    mock_eng_row = MagicMock()
    mock_eng_row.date = date(2026, 6, 10)
    mock_eng_row.eng_rate = 0.057
    mock_eng_row.platform = "youtube"

    # 4. Mock Comparison rows
    mock_comp_row = MagicMock()
    mock_comp_row.platform = "youtube"
    mock_comp_row.views = 5000
    mock_comp_row.likes = 400
    mock_comp_row.comments = 60
    mock_comp_row.shares = 0
    mock_comp_row.saves = 0
    mock_comp_row.watch_time = 32.5
    mock_comp_row.eng_rate = 0.092

    # Override session execute return values in order
    mock_execute = AsyncMock()
    mock_execute.side_effect = [
        MagicMock(fetchone=MagicMock(return_value=mock_summary_row)),  # summary
        MagicMock(all=MagicMock(return_value=[mock_view_row])),       # views
        MagicMock(all=MagicMock(return_value=[mock_eng_row])),        # engagement
        MagicMock(all=MagicMock(return_value=[mock_comp_row])),       # comparison
    ]
    mock_db_session.execute = mock_execute

    # Mock recommendations engine
    mock_recs = {
        "best_posting_time": "Sunday Evening",
        "best_platform": "YouTube Shorts",
        "best_hashtag_patterns": "Niche tags",
        "best_artwork_category": "Vibrant lands",
        "rationale": "Observational study",
    }

    with patch("backend.services.ai_recommendations.AIRecommendationService.generate_recommendations", AsyncMock(return_value=mock_recs)):
        resp = await client.get("/api/v1/dashboard/analytics", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_views"] == 10000
        assert data["total_likes"] == 850
        assert len(data["daily_views"]) == 1
        assert data["daily_views"][0]["views"] == 5000
        assert data["platform_comparison"][0]["platform"] == "youtube"
        assert data["ai_recommendations"]["best_platform"] == "YouTube Shorts"


@pytest.mark.asyncio
async def test_dashboard_top_performing_api_endpoint(
    client: AsyncClient,
    mock_db_session: AsyncSession,
    mock_user: User,
    mock_artwork_id: uuid.UUID,
    auth_headers: dict[str, str],
) -> None:
    """Test GET /api/v1/dashboard/top-performing endpoint resolves performers successfully."""
    mock_db_session.get = AsyncMock(return_value=mock_user)

    # 1. Top artwork row
    mock_art_row = MagicMock()
    mock_art_row.artwork_id = mock_artwork_id
    mock_art_row.total_views = 12000

    # 2. Top reel row
    mock_reel_row = MagicMock()
    mock_reel_row.artwork_id = mock_artwork_id
    mock_reel_row.views = 7000
    mock_reel_row.platform = "instagram"
    mock_reel_row.title = "Sunset Reel"
    mock_reel_row.reel_path = "outputs/reels/sunset.mp4"

    # 3. Top platform row
    mock_plat_row = MagicMock()
    mock_plat_row.platform = "instagram"
    mock_plat_row.total_views = 15000

    # Database mock setup for execution side effects
    mock_execute = AsyncMock()
    mock_execute.side_effect = [
        MagicMock(fetchone=MagicMock(return_value=mock_art_row)),        # top artwork search
        MagicMock(fetchone=MagicMock(return_value=mock_reel_row)),       # top reel search
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[["#art", "#sun"]])))),  # top hashtags
        MagicMock(fetchone=MagicMock(return_value=mock_plat_row)),       # top platform search
    ]
    mock_db_session.execute = mock_execute

    # Mock artwork load from repo
    mock_artwork = Artwork(
        id=mock_artwork_id,
        title="Sunset Artwork",
        original_filename="sunset.png",
        file_path="artworks/sunset.png",
        file_size=2048,
        mime_type="image/png",
        status=ArtworkStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    from backend.database.repository import BaseRepository
    with patch.object(BaseRepository, "get_by_id", AsyncMock(return_value=mock_artwork)):
        resp = await client.get("/api/v1/dashboard/top-performing", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["top_artwork"]["title"] == "Sunset Artwork"
        assert data["top_reel"]["views"] == 7000
        assert data["top_reel"]["platform"] == "instagram"
        assert data["top_hashtag"] in ["#art", "#sun"]
        assert data["top_platform"] == "instagram"


@pytest.mark.asyncio
async def test_artwork_individual_analytics_api_endpoint(
    client: AsyncClient,
    mock_db_session: AsyncSession,
    mock_user: User,
    mock_artwork_id: uuid.UUID,
    auth_headers: dict[str, str],
) -> None:
    """Test GET /api/v1/artworks/{id}/analytics endpoint parses metrics cleanly."""
    mock_db_session.get = AsyncMock(return_value=mock_user)

    # Setup mock artwork and pre-load relationship analytics list
    mock_analytics_item = ArtworkAnalytics(
        id=uuid.uuid4(),
        artwork_id=mock_artwork_id,
        platform="youtube",
        views=3400,
        reach=3400,
        impressions=3400,
        likes=210,
        comments=18,
        shares=0,
        saves=0,
        watch_time=15.5,
        engagement_rate=0.067,
        collected_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_artwork = Artwork(
        id=mock_artwork_id,
        title="Vase of Flowers",
        original_filename="flowers.png",
        file_path="artworks/flowers.png",
        file_size=2048,
        mime_type="image/png",
        status=ArtworkStatus.COMPLETED,
        analytics=[mock_analytics_item],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    from backend.database.repository import BaseRepository
    with patch.object(BaseRepository, "get_by_id", AsyncMock(return_value=mock_artwork)):
        resp = await client.get(f"/api/v1/artworks/{mock_artwork_id}/analytics", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["platform"] == "youtube"
        assert data[0]["views"] == 3400
        assert data[0]["likes"] == 210
