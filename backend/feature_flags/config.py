"""Feature flag system for controlling pipeline stages at runtime.

Feature flags are loaded from settings (environment variables) and can
be queried to enable/disable specific pipeline stages without code changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from backend.config.settings import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


class FeatureFlag(str, Enum):
    """Enumeration of all available feature flags."""

    INSTAGRAM_PUBLISH = "enable_instagram_publish"
    YOUTUBE_PUBLISH = "enable_youtube_publish"
    PINTEREST_PUBLISH = "enable_pinterest_publish"
    TIKTOK_PUBLISH = "enable_tiktok_publish"
    REEL_GENERATION = "enable_reel_generation"
    ANALYTICS_COLLECTION = "enable_analytics_collection"


@dataclass
class FeatureFlagState:
    """Snapshot of all feature flag values."""

    flags: dict[str, bool]
    workflow_version: str


def get_feature_flags() -> FeatureFlagState:
    """Return the current state of all feature flags from settings."""
    settings = get_settings()
    ff = settings.feature_flags

    flags = {
        FeatureFlag.INSTAGRAM_PUBLISH.value: ff.enable_instagram_publish,
        FeatureFlag.YOUTUBE_PUBLISH.value: ff.enable_youtube_publish,
        FeatureFlag.PINTEREST_PUBLISH.value: ff.enable_pinterest_publish,
        FeatureFlag.TIKTOK_PUBLISH.value: ff.enable_tiktok_publish,
        FeatureFlag.REEL_GENERATION.value: ff.enable_reel_generation,
        FeatureFlag.ANALYTICS_COLLECTION.value: ff.enable_analytics_collection,
    }

    return FeatureFlagState(
        flags=flags,
        workflow_version=ff.workflow_version,
    )


def is_enabled(flag: FeatureFlag) -> bool:
    """Check whether a specific feature flag is enabled."""
    state = get_feature_flags()
    return state.flags.get(flag.value, False)


def get_workflow_version() -> str:
    """Return the currently configured workflow version."""
    settings = get_settings()
    return settings.feature_flags.workflow_version
