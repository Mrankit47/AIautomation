"""AI Recommendation engine service using Google Gemini."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import get_logger
from backend.models.analytics import ArtworkAnalytics
from backend.models.artwork import Artwork
from backend.providers.gemini import GeminiProvider

logger = get_logger(__name__)


class AIRecommendationService:
    """Analyzes historic artwork performance and provides AI recommendations via Gemini."""

    def __init__(self) -> None:
        self._provider = GeminiProvider()

    async def generate_recommendations(self, session: AsyncSession) -> dict[str, Any]:
        """Fetch past performance metrics and generate structured post recommendations.

        Args:
            session: SQLAlchemy AsyncSession.

        Returns:
            Dict containing best_posting_time, best_platform, best_hashtag_patterns,
            best_artwork_category, and rationale.
        """
        logger.info("ai_recommendations_generate_started")

        # 1. Fetch recent analytics records joined with their Artwork model
        stmt = (
            select(ArtworkAnalytics, Artwork)
            .join(Artwork, ArtworkAnalytics.artwork_id == Artwork.id)
            .order_by(ArtworkAnalytics.collected_at.desc())
            .limit(50)
        )
        result = await session.execute(stmt)
        records = result.all()

        if not records:
            # Fallback to default presets if there's no data yet
            logger.info("ai_recommendations_fallback_no_data")
            return {
                "best_posting_time": "12:00 PM - 3:00 PM and 6:00 PM - 9:00 PM (Local Time)",
                "best_platform": "YouTube Shorts (for reach/views) & Instagram Reels (for engagement/community)",
                "best_hashtag_patterns": "5-10 highly relevant niche tags mixed with 2-3 broad tags (e.g., #digitalart, #aiartist)",
                "best_artwork_category": "Vibrant landscape, abstract generative art, or storytelling concept art",
                "rationale": "Initial baseline recommendation derived from general industry best practices for art and creative media platforms, due to lack of historical performance records in the database.",
            }

        # 2. Compile dataset for LLM analysis
        data_points = []
        for analytics, artwork in records:
            # Parse categories/labels from analysis data if present
            labels = []
            if artwork.analysis_data:
                labels = artwork.analysis_data.get("subjects", artwork.analysis_data.get("objects", []))

            # Resolve publish time details
            pub_time = None
            if analytics.platform == "instagram":
                pub_time = artwork.instagram_published_at
            elif analytics.platform == "youtube":
                pub_time = artwork.youtube_published_at

            pub_time_str = pub_time.strftime("%A, %I:%M %p") if pub_time else "unknown"

            data_points.append({
                "artwork_id": str(artwork.id),
                "title": artwork.title or "Untitled",
                "platform": analytics.platform,
                "publish_time": pub_time_str,
                "views": analytics.views,
                "likes": analytics.likes,
                "comments": analytics.comments,
                "engagement_rate": analytics.engagement_rate,
                "hashtags": artwork.hashtags or [],
                "labels": labels,
            })

        # 3. Create Gemini Prompt
        prompt = (
            "You are a Senior Social Media Strategist and AI Analytics Specialist. "
            "Analyze the following performance dataset of published artworks and reels. "
            "Identify the optimization patterns that drive maximum views and engagement:\n\n"
            f"Dataset:\n{json.dumps(data_points, indent=2)}\n\n"
            "Based on this data, provide the single best posting time (with day/hour), the best platform, "
            "the best hashtag patterns (how many, and which categories/keywords), and the best artwork style/category "
            "along with a clear rationale. Make your recommendations highly specific to this dataset."
        )

        output_schema = {
            "type": "object",
            "properties": {
                "best_posting_time": {
                    "type": "string",
                    "description": "Specific times and days that perform best.",
                },
                "best_platform": {
                    "type": "string",
                    "description": "The highest-performing social media platform.",
                },
                "best_hashtag_patterns": {
                    "type": "string",
                    "description": "Optimal number of tags, style, and keyword groupings.",
                },
                "best_artwork_category": {
                    "type": "string",
                    "description": "Most successful visual subjects, themes, or styles.",
                },
                "rationale": {
                    "type": "string",
                    "description": "Summary of data observations supporting these recommendations.",
                },
            },
            "required": [
                "best_posting_time",
                "best_platform",
                "best_hashtag_patterns",
                "best_artwork_category",
                "rationale",
            ],
        }

        try:
            res = await self._provider.generate_structured(
                prompt=prompt,
                output_schema=output_schema,
                system_prompt="You are a data analyst specialized in art publishing performance insights.",
                temperature=0.2,
            )
            logger.info("ai_recommendations_generate_success")
            return res.data
        except Exception as e:
            logger.error("ai_recommendations_generate_failed", error=str(e))
            # Graceful fallback on API failure
            return {
                "best_posting_time": "12:00 PM - 3:00 PM (Local Time)",
                "best_platform": "YouTube Shorts",
                "best_hashtag_patterns": "5-10 relevant niche tags",
                "best_artwork_category": "Vibrant landscape or generative abstracts",
                "rationale": f"Fallback recommendation generated due to an error querying the AI Provider: {str(e)}",
            }
