"""Base analytics collector — re-exports the abstract interface."""

from backend.analytics.base import AnalyticsCollector, PostMetrics

__all__ = ["AnalyticsCollector", "PostMetrics"]
