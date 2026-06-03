"""YouTube analytics collector stub."""

from __future__ import annotations

from datetime import datetime

from backend.analytics.base import (
    AccountMetrics,
    AnalyticsCollector,
    PeriodMetrics,
    PostMetrics,
)
from backend.core.logging import get_logger

logger = get_logger(__name__)


class YouTubeAnalyticsCollector(AnalyticsCollector):
    """Collects analytics from YouTube Analytics API.

    Note: Full implementation deferred to analytics phase.
    """

    @property
    def platform(self) -> str:
        return "youtube"

    async def collect_post_metrics(self, post_id: str) -> PostMetrics:
        logger.info("collecting_youtube_metrics", post_id=post_id)
        raise NotImplementedError("YouTube analytics collection — future phase.")

    async def collect_account_metrics(self) -> AccountMetrics:
        raise NotImplementedError("YouTube account metrics — future phase.")

    async def collect_period_metrics(
        self, start: datetime, end: datetime
    ) -> PeriodMetrics:
        raise NotImplementedError("YouTube period metrics — future phase.")
