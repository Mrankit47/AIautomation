"""Workflow v2 — enhanced pipeline with parallel publishing.

This module defines the v2 workflow configuration.  v2 differs from v1
by executing publishing stages in parallel instead of sequentially.
"""

from __future__ import annotations

from typing import Any

from backend.core.logging import get_logger

logger = get_logger(__name__)

WORKFLOW_VERSION = "v2"

STAGES: list[dict[str, Any]] = [
    {"name": "analyze_artwork", "required": True},
    {"name": "generate_metadata", "required": True},
    {"name": "generate_seo", "required": True},
    {"name": "generate_caption", "required": True},
    {"name": "generate_hashtags", "required": True},
    {"name": "generate_reel", "required": False, "feature_flag": "enable_reel_generation"},
    # v2: publishing stages run in parallel
    {
        "name": "publish_all",
        "required": False,
        "parallel": True,
        "sub_stages": [
            {"name": "publish_instagram", "feature_flag": "enable_instagram_publish"},
            {"name": "publish_youtube", "feature_flag": "enable_youtube_publish"},
            {"name": "publish_pinterest", "feature_flag": "enable_pinterest_publish"},
            {"name": "publish_tiktok", "feature_flag": "enable_tiktok_publish"},
        ],
    },
    {"name": "collect_analytics", "required": False, "feature_flag": "enable_analytics_collection"},
]


def get_config() -> dict[str, Any]:
    """Return the v2 workflow configuration."""
    return {
        "version": WORKFLOW_VERSION,
        "stages": STAGES,
        "description": "Enhanced pipeline with parallel social media publishing.",
    }
