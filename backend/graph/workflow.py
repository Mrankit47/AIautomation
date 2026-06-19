"""LangGraph workflow builder — constructs the artwork processing StateGraph."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.graph.nodes import (
    analyze_artwork,
    collect_analytics,
    generate_caption,
    generate_hashtags,
    generate_metadata,
    generate_reel,
    generate_seo,
    handle_error,
    publish_instagram,
    publish_pinterest,
    publish_tiktok,
    publish_youtube,
)
from backend.graph.state import ArtworkWorkflowState

logger = get_logger(__name__)


def _should_continue(state: ArtworkWorkflowState) -> str:
    """Router: check if workflow should continue or go to error handler."""
    if state.get("workflow_status") == "failed":
        return "handle_error"
    return "continue"


def _should_generate_reel(state: ArtworkWorkflowState) -> str:
    """Router: check if reel generation is enabled."""
    if state.get("category") == "photography":
        return "publish_instagram"

    settings = get_settings()
    if settings.feature_flags.enable_reel_generation:
        return "generate_reel"
    
    # Skip reel and route to next active node
    if settings.feature_flags.enable_instagram_publish:
        return "publish_instagram"
    if settings.feature_flags.enable_youtube_publish and state.get("category") != "gallery":
        return "publish_youtube"
    if settings.feature_flags.enable_pinterest_publish:
        return "publish_pinterest"
    if settings.feature_flags.enable_analytics_collection:
        return "collect_analytics"
    return "end"


def _after_reel(state: ArtworkWorkflowState) -> str:
    """Router: determine where to go after reel node."""
    if state.get("workflow_status") == "failed":
        return "handle_error"
    
    settings = get_settings()
    if settings.feature_flags.enable_instagram_publish:
        return "publish_instagram"
    if settings.feature_flags.enable_youtube_publish and state.get("category") != "gallery":
        return "publish_youtube"
    if settings.feature_flags.enable_pinterest_publish:
        return "publish_pinterest"
    if settings.feature_flags.enable_analytics_collection:
        return "collect_analytics"
    return "end"


def _after_publish_instagram(state: ArtworkWorkflowState) -> str:
    """Router: determine where to go after Instagram publishing."""
    if state.get("workflow_status") == "failed":
        return "handle_error"
    
    if state.get("category") == "photography":
        settings = get_settings()
        if settings.feature_flags.enable_analytics_collection:
            return "collect_analytics"
        return "end"

    settings = get_settings()
    if settings.feature_flags.enable_youtube_publish and state.get("category") != "gallery":
        return "publish_youtube"
    if settings.feature_flags.enable_pinterest_publish:
        return "publish_pinterest"
    if settings.feature_flags.enable_analytics_collection:
        return "collect_analytics"
    return "end"


def _after_publish_youtube(state: ArtworkWorkflowState) -> str:
    """Router: determine where to go after YouTube publishing."""
    if state.get("workflow_status") == "failed":
        return "handle_error"
    
    settings = get_settings()
    if settings.feature_flags.enable_pinterest_publish:
        return "publish_pinterest"
    if settings.feature_flags.enable_analytics_collection:
        return "collect_analytics"
    return "end"


def _after_publish_pinterest(state: ArtworkWorkflowState) -> str:
    """Router: determine where to go after Pinterest publishing."""
    if state.get("workflow_status") == "failed":
        return "handle_error"
    
    settings = get_settings()
    if settings.feature_flags.enable_analytics_collection:
        return "collect_analytics"
    return "end"


def build_artwork_workflow() -> StateGraph:
    """Construct the full artwork processing workflow graph.

    Pipeline:
        analyze → metadata → seo → caption → hashtags
        → reel (conditional) → publish_instagram (conditional)
        → publish_youtube (conditional) → collect_analytics (conditional) → END

        Any node failure → handle_error → END
    """
    graph = StateGraph(ArtworkWorkflowState)

    # ── Register Nodes ───────────────────────────────────────────────────
    graph.add_node("analyze_artwork", analyze_artwork)
    graph.add_node("generate_metadata", generate_metadata)
    graph.add_node("generate_seo", generate_seo)
    graph.add_node("generate_caption", generate_caption)
    graph.add_node("generate_hashtags", generate_hashtags)
    graph.add_node("generate_reel", generate_reel)
    graph.add_node("publish_instagram", publish_instagram)
    graph.add_node("publish_youtube", publish_youtube)
    graph.add_node("publish_pinterest", publish_pinterest)
    graph.add_node("collect_analytics", collect_analytics)
    graph.add_node("handle_error", handle_error)

    # ── Entry Point ──────────────────────────────────────────────────────
    graph.set_entry_point("analyze_artwork")

    # ── Core Pipeline (linear) ───────────────────────────────────────────
    graph.add_conditional_edges(
        "analyze_artwork",
        _should_continue,
        {"continue": "generate_metadata", "handle_error": "handle_error"},
    )
    graph.add_conditional_edges(
        "generate_metadata",
        _should_continue,
        {"continue": "generate_seo", "handle_error": "handle_error"},
    )
    graph.add_conditional_edges(
        "generate_seo",
        _should_continue,
        {"continue": "generate_caption", "handle_error": "handle_error"},
    )
    graph.add_conditional_edges(
        "generate_caption",
        _should_continue,
        {"continue": "generate_hashtags", "handle_error": "handle_error"},
    )

    # ── Reel Generation (feature-flagged) ────────────────────────────────
    graph.add_conditional_edges(
        "generate_hashtags",
        _should_generate_reel,
        {
            "generate_reel": "generate_reel",
            "publish_instagram": "publish_instagram",
            "publish_youtube": "publish_youtube",
            "publish_pinterest": "publish_pinterest",
            "collect_analytics": "collect_analytics",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "generate_reel",
        _after_reel,
        {
            "publish_instagram": "publish_instagram",
            "publish_youtube": "publish_youtube",
            "publish_pinterest": "publish_pinterest",
            "collect_analytics": "collect_analytics",
            "end": END,
            "handle_error": "handle_error",
        },
    )

    # ── Publishing (feature-flagged per platform) ────────────────────────
    graph.add_conditional_edges(
        "publish_instagram",
        _after_publish_instagram,
        {
            "publish_youtube": "publish_youtube",
            "publish_pinterest": "publish_pinterest",
            "collect_analytics": "collect_analytics",
            "end": END,
            "handle_error": "handle_error",
        },
    )
    graph.add_conditional_edges(
        "publish_youtube",
        _after_publish_youtube,
        {
            "publish_pinterest": "publish_pinterest",
            "collect_analytics": "collect_analytics",
            "end": END,
            "handle_error": "handle_error",
        },
    )
    graph.add_conditional_edges(
        "publish_pinterest",
        _after_publish_pinterest,
        {
            "collect_analytics": "collect_analytics",
            "end": END,
            "handle_error": "handle_error",
        },
    )

    # ── Analytics ────────────────────────────────────────────────────────
    graph.add_edge("collect_analytics", END)

    # ── Error Handler ────────────────────────────────────────────────────
    graph.add_edge("handle_error", END)

    logger.info("workflow_graph_built", node_count=12)
    return graph


def compile_artwork_workflow() -> Any:
    """Build and compile the workflow for execution."""
    graph = build_artwork_workflow()
    return graph.compile()
