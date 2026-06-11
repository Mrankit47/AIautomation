"""Dashboard API router — endpoints for analytics aggregation, charts, and recommendations."""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import Date, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import (
    get_db_session,
    get_ai_recommendation_service,
)
from backend.auth.dependencies import get_current_active_user
from backend.models.analytics import ArtworkAnalytics
from backend.models.artwork import Artwork
from backend.models.user import User
from backend.schemas.analytics import (
    DashboardAnalyticsResponse,
    DailyViewsItem,
    DailyEngagementItem,
    PlatformMetrics,
    TopPerformingResponse,
    TopPerformingReel,
    AIRecommendationResponse,
)
from backend.services.ai_recommendations import AIRecommendationService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/analytics", response_model=DashboardAnalyticsResponse)
async def get_dashboard_analytics(
    session: AsyncSession = Depends(get_db_session),
    recommendation_service: AIRecommendationService = Depends(get_ai_recommendation_service),
    current_user: User = Depends(get_current_active_user),
) -> DashboardAnalyticsResponse:
    """Retrieve top-level dashboard metrics, daily performance charts, and AI recommendations."""
    # 1. Query top-level metrics summary
    summary_stmt = select(
        func.coalesce(func.sum(ArtworkAnalytics.views), 0).label("views"),
        func.coalesce(func.sum(ArtworkAnalytics.likes), 0).label("likes"),
        func.coalesce(func.sum(ArtworkAnalytics.comments), 0).label("comments"),
        func.coalesce(func.sum(ArtworkAnalytics.reach), 0).label("reach"),
        func.coalesce(func.sum(ArtworkAnalytics.impressions), 0).label("impressions"),
        func.count(func.distinct(ArtworkAnalytics.artwork_id)).label("posts"),
    )
    summary_res = await session.execute(summary_stmt)
    summary = summary_res.fetchone()

    total_views = summary.views if summary else 0
    total_likes = summary.likes if summary else 0
    total_comments = summary.comments if summary else 0
    total_reach = summary.reach if summary else 0
    total_impressions = summary.impressions if summary else 0
    total_posts = summary.posts if summary else 0

    # 2. Query daily views (grouped by day and platform)
    date_col = func.cast(ArtworkAnalytics.collected_at, Date)
    views_stmt = (
        select(
            date_col.label("date"),
            func.coalesce(func.sum(ArtworkAnalytics.views), 0).label("views"),
            ArtworkAnalytics.platform,
        )
        .group_by(date_col, ArtworkAnalytics.platform)
        .order_by(date_col.asc())
    )
    views_res = await session.execute(views_stmt)
    views_rows = views_res.all()

    daily_views = []
    for r in views_rows:
        date_str = r.date.strftime("%Y-%m-%d") if isinstance(r.date, (datetime, date)) else str(r.date)
        daily_views.append(DailyViewsItem(
            date=date_str,
            views=r.views,
            platform=r.platform,
        ))

    # 3. Query daily engagement rate (average per day per platform)
    eng_stmt = (
        select(
            date_col.label("date"),
            func.coalesce(func.avg(ArtworkAnalytics.engagement_rate), 0.0).label("eng_rate"),
            ArtworkAnalytics.platform,
        )
        .group_by(date_col, ArtworkAnalytics.platform)
        .order_by(date_col.asc())
    )
    eng_res = await session.execute(eng_stmt)
    eng_rows = eng_res.all()

    daily_engagement = []
    for r in eng_rows:
        date_str = r.date.strftime("%Y-%m-%d") if isinstance(r.date, (datetime, date)) else str(r.date)
        daily_engagement.append(DailyEngagementItem(
            date=date_str,
            engagement_rate=float(r.eng_rate),
            platform=r.platform,
        ))

    # 4. Query platform comparison table metrics
    comparison_stmt = (
        select(
            ArtworkAnalytics.platform,
            func.coalesce(func.sum(ArtworkAnalytics.views), 0).label("views"),
            func.coalesce(func.sum(ArtworkAnalytics.likes), 0).label("likes"),
            func.coalesce(func.sum(ArtworkAnalytics.comments), 0).label("comments"),
            func.coalesce(func.sum(ArtworkAnalytics.shares), 0).label("shares"),
            func.coalesce(func.sum(ArtworkAnalytics.saves), 0).label("saves"),
            func.coalesce(func.sum(ArtworkAnalytics.watch_time), 0.0).label("watch_time"),
            func.coalesce(func.avg(ArtworkAnalytics.engagement_rate), 0.0).label("eng_rate"),
        )
        .group_by(ArtworkAnalytics.platform)
    )
    comparison_res = await session.execute(comparison_stmt)
    comparison_rows = comparison_res.all()

    platform_comparison = []
    for r in comparison_rows:
        platform_comparison.append(PlatformMetrics(
            platform=r.platform,
            views=r.views,
            likes=r.likes,
            comments=r.comments,
            shares=r.shares,
            saves=r.saves,
            watch_time=float(r.watch_time),
            engagement_rate=float(r.eng_rate),
        ))

    # 5. Generate AI posting recommendations
    ai_recs_dict = await recommendation_service.generate_recommendations(session)
    ai_recommendations = AIRecommendationResponse(**ai_recs_dict)

    return DashboardAnalyticsResponse(
        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments,
        total_reach=total_reach,
        total_impressions=total_impressions,
        total_posts=total_posts,
        daily_views=daily_views,
        daily_engagement=daily_engagement,
        platform_comparison=platform_comparison,
        ai_recommendations=ai_recommendations,
    )


@router.get("/top-performing", response_model=TopPerformingResponse)
async def get_top_performing(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> TopPerformingResponse:
    """Retrieve top performing artwork, reel video, platform, and hashtag."""
    # 1. Resolve Top Artwork (by total views)
    top_art_stmt = (
        select(ArtworkAnalytics.artwork_id, func.sum(ArtworkAnalytics.views).label("total_views"))
        .group_by(ArtworkAnalytics.artwork_id)
        .order_by(func.sum(ArtworkAnalytics.views).desc())
        .limit(1)
    )
    top_art_res = await session.execute(top_art_stmt)
    top_art_row = top_art_res.fetchone()

    top_artwork = None
    if top_art_row:
        from backend.database.repository import BaseRepository
        repo = BaseRepository(Artwork, session)
        top_artwork = await repo.get_by_id(top_art_row.artwork_id)

    # 2. Resolve Top Reel (highest views)
    top_reel_stmt = (
        select(
            ArtworkAnalytics.artwork_id,
            ArtworkAnalytics.views,
            ArtworkAnalytics.platform,
            Artwork.title,
            Artwork.reel_path,
        )
        .join(Artwork, ArtworkAnalytics.artwork_id == Artwork.id)
        .where(Artwork.reel_path.is_not(None))
        .order_by(ArtworkAnalytics.views.desc())
        .limit(1)
    )
    top_reel_res = await session.execute(top_reel_stmt)
    top_reel_row = top_reel_res.fetchone()

    top_reel = None
    if top_reel_row:
        top_reel = TopPerformingReel(
            artwork_id=top_reel_row.artwork_id,
            title=top_reel_row.title,
            reel_path=top_reel_row.reel_path,
            views=top_reel_row.views,
            platform=top_reel_row.platform,
        )

    # 3. Resolve Top Hashtag (most frequent among top views posts)
    hashtag_stmt = (
        select(Artwork.hashtags)
        .join(ArtworkAnalytics, Artwork.id == ArtworkAnalytics.artwork_id)
        .where(Artwork.hashtags.is_not(None))
        .order_by(ArtworkAnalytics.views.desc())
        .limit(10)
    )
    hashtag_res = await session.execute(hashtag_stmt)
    hashtag_rows = hashtag_res.scalars().all()

    from collections import Counter
    all_tags = []
    for tags in hashtag_rows:
        if isinstance(tags, list):
            all_tags.extend(tags)

    top_hashtag = None
    if all_tags:
        top_hashtag = Counter(all_tags).most_common(1)[0][0]

    # 4. Resolve Top Platform (highest total views)
    top_plat_stmt = (
        select(ArtworkAnalytics.platform, func.sum(ArtworkAnalytics.views).label("total_views"))
        .group_by(ArtworkAnalytics.platform)
        .order_by(func.sum(ArtworkAnalytics.views).desc())
        .limit(1)
    )
    top_plat_res = await session.execute(top_plat_stmt)
    top_plat_row = top_plat_res.fetchone()
    top_platform = top_plat_row.platform if top_plat_row else None

    # Map database Artwork models to response schemas if present
    from backend.schemas.artwork import ArtworkResponse
    top_artwork_response = ArtworkResponse.model_validate(top_artwork) if top_artwork else None

    return TopPerformingResponse(
        top_artwork=top_artwork_response,
        top_reel=top_reel,
        top_hashtag=top_hashtag,
        top_platform=top_platform,
    )
