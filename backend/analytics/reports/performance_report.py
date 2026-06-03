"""Performance report generator — aggregates cross-platform metrics."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.analytics.base import ComparisonReport, Report, ReportGenerator
from backend.core.logging import get_logger

logger = get_logger(__name__)


class PerformanceReportGenerator(ReportGenerator):
    """Generates performance reports by aggregating metrics across platforms.

    Note: Full implementation deferred to analytics phase.
    """

    async def generate(
        self, artwork_id: str, period: str = "7d"
    ) -> Report:
        logger.info(
            "generating_report",
            artwork_id=artwork_id,
            period=period,
        )
        # Stub — will aggregate from all collectors
        return Report(
            artwork_id=artwork_id,
            period=period,
            platforms=[],
            metrics={},
            generated_at=datetime.now(timezone.utc),
        )

    async def generate_comparison(
        self, artwork_ids: list[str]
    ) -> ComparisonReport:
        logger.info(
            "generating_comparison_report",
            artwork_count=len(artwork_ids),
        )
        return ComparisonReport(
            artwork_ids=artwork_ids,
            rankings={},
            insights=[],
            generated_at=datetime.now(timezone.utc),
        )
