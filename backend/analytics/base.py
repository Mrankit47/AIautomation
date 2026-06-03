"""Abstract analytics interfaces for metric collection and reporting."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PostMetrics:
    """Metrics for a single published post."""

    post_id: str
    platform: str
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    views: int = 0
    engagement_rate: float = 0.0
    collected_at: datetime | None = None


@dataclass
class AccountMetrics:
    """Account-level metrics for a platform."""

    platform: str
    followers: int = 0
    following: int = 0
    total_posts: int = 0
    collected_at: datetime | None = None


@dataclass
class PeriodMetrics:
    """Aggregated metrics over a time period."""

    platform: str
    start: datetime
    end: datetime
    total_impressions: int = 0
    total_reach: int = 0
    total_engagement: int = 0
    post_count: int = 0
    avg_engagement_rate: float = 0.0


@dataclass
class Report:
    """Generated analytics report."""

    artwork_id: str
    period: str
    platforms: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    generated_at: datetime | None = None


@dataclass
class ComparisonReport:
    """Comparative report across multiple artworks."""

    artwork_ids: list[str] = field(default_factory=list)
    rankings: dict[str, Any] = field(default_factory=dict)
    insights: list[str] = field(default_factory=list)
    generated_at: datetime | None = None


class AnalyticsCollector(ABC):
    """Abstract interface for platform analytics collection."""

    @property
    @abstractmethod
    def platform(self) -> str:
        ...

    @abstractmethod
    async def collect_post_metrics(self, post_id: str) -> PostMetrics:
        ...

    @abstractmethod
    async def collect_account_metrics(self) -> AccountMetrics:
        ...

    @abstractmethod
    async def collect_period_metrics(
        self, start: datetime, end: datetime
    ) -> PeriodMetrics:
        ...


class ReportGenerator(ABC):
    """Abstract interface for analytics report generation."""

    @abstractmethod
    async def generate(
        self, artwork_id: str, period: str = "7d"
    ) -> Report:
        ...

    @abstractmethod
    async def generate_comparison(
        self, artwork_ids: list[str]
    ) -> ComparisonReport:
        ...
