"""Pinterest analytics collector stub."""

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


class PinterestAnalyticsCollector(AnalyticsCollector):
    """Collects analytics from Pinterest API.

    Note: Full implementation deferred to analytics phase.
    """

    @property
    def platform(self) -> str:
        return "pinterest"

    async def collect_post_metrics(self, post_id: str) -> PostMetrics:
        logger.info("collecting_pinterest_metrics", post_id=post_id)
        raise NotImplementedError("Pinterest analytics collection — future phase.")

    async def collect_account_metrics(self) -> AccountMetrics:
        raise NotImplementedError("Pinterest account metrics — future phase.")

    async def collect_period_metrics(
        self, start: datetime, end: datetime
    ) -> PeriodMetrics:
        raise NotImplementedError("Pinterest period metrics — future phase.")
