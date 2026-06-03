"""Base report generator — re-exports the abstract interface."""

from backend.analytics.base import ComparisonReport, Report, ReportGenerator

__all__ = ["ReportGenerator", "Report", "ComparisonReport"]
