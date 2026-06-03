"""Workflow v1 — baseline linear pipeline.

This module defines the v1 workflow configuration used by the
LangGraph workflow builder.  Future versions can override node
implementations, add/remove stages, or change routing logic.
"""

from __future__ import annotations

from typing import Any

from backend.core.logging import get_logger

logger = get_logger(__name__)

WORKFLOW_VERSION = "v1"

# Pipeline stage definitions for v1
STAGES: list[dict[str, Any]] = [
    {"name": "analyze_artwork", "required": True},
    {"name": "generate_metadata", "required": True},
    {"name": "generate_seo", "required": True},
    {"name": "generate_caption", "required": True},
    {"name": "generate_hashtags", "required": True},
    {"name": "generate_reel", "required": False, "feature_flag": "enable_reel_generation"},
    {"name": "publish_instagram", "required": False, "feature_flag": "enable_instagram_publish"},
    {"name": "publish_youtube", "required": False, "feature_flag": "enable_youtube_publish"},
    {"name": "publish_pinterest", "required": False, "feature_flag": "enable_pinterest_publish"},
    {"name": "publish_tiktok", "required": False, "feature_flag": "enable_tiktok_publish"},
    {"name": "collect_analytics", "required": False, "feature_flag": "enable_analytics_collection"},
]


def get_config() -> dict[str, Any]:
    """Return the v1 workflow configuration."""
    return {
        "version": WORKFLOW_VERSION,
        "stages": STAGES,
        "description": "Baseline linear artwork processing pipeline.",
    }
