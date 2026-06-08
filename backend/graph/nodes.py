"""LangGraph node functions for the artwork processing workflow.

Each node is an async function that receives the current state, performs
its task, updates the database in a production-safe way, and returns a
partial state update dict.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.agents.artwork_analyzer import ArtworkAnalyzerAgent
from backend.agents.caption_agent import CaptionAgent
from backend.agents.hashtag_agent import HashtagAgent
from backend.agents.metadata_generator import MetadataGeneratorAgent
from backend.agents.reel_script_agent import ReelScriptAgent
from backend.agents.seo_agent import SEOAgent
from backend.core.logging import get_logger
from backend.graph.state import ArtworkWorkflowState

logger = get_logger(__name__)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_error(node: str, exc: Exception) -> dict[str, Any]:
    return {
        "node": node,
        "error_type": type(exc).__name__,
        "message": str(exc),
        "timestamp": _timestamp(),
        "recoverable": True,
    }


# ── Database Persistence Helpers ─────────────────────────────────────────────


def _update_run_node(
    workflow_run_id: str,
    node_name: str,
    status: str = "running",
    error_history: list | None = None,
) -> None:
    """Update current_node and overall status in the workflow run."""
    from backend.database.session import get_sync_session
    from backend.models.workflow_run import WorkflowRun, WorkflowStatus
    from sqlalchemy import select

    session = get_sync_session()
    try:
        run = session.execute(
            select(WorkflowRun).where(WorkflowRun.id == uuid.UUID(workflow_run_id))
        ).scalar_one_or_none()
        if run:
            run.current_node = node_name
            if status == "running":
                run.status = WorkflowStatus.RUNNING
            elif status == "completed":
                run.status = WorkflowStatus.COMPLETED
            elif status == "failed":
                run.status = WorkflowStatus.FAILED

            if error_history is not None:
                run.error_history = error_history

            session.commit()
    except Exception as exc:
        logger.error("db_update_run_node_failed", node=node_name, error=str(exc))
        session.rollback()
    finally:
        session.close()


def _update_run_publishing_status(
    workflow_run_id: str,
    platform: str,
    status: str,
) -> None:
    """Update publishing status for a platform in the workflow run."""
    from backend.database.session import get_sync_session
    from backend.models.workflow_run import WorkflowRun
    from sqlalchemy import select

    session = get_sync_session()
    try:
        run = session.execute(
            select(WorkflowRun).where(WorkflowRun.id == uuid.UUID(workflow_run_id))
        ).scalar_one_or_none()
        if run:
            field_name = f"{platform}_status"
            if hasattr(run, field_name):
                setattr(run, field_name, status)
            session.commit()
    except Exception as exc:
        logger.error("db_update_run_publishing_status_failed", platform=platform, error=str(exc))
        session.rollback()
    finally:
        session.close()


def _update_artwork_multiple_fields(
    artwork_id: str,
    fields: dict[str, Any],
    status: str | None = None,
) -> None:
    """Update multiple fields on the Artwork model."""
    from backend.database.session import get_sync_session
    from backend.models.artwork import Artwork, ArtworkStatus
    from sqlalchemy import select

    session = get_sync_session()
    try:
        art = session.execute(
            select(Artwork).where(Artwork.id == uuid.UUID(artwork_id))
        ).scalar_one_or_none()
        if art:
            for k, v in fields.items():
                setattr(art, k, v)
            if status:
                art.status = ArtworkStatus(status)
            session.commit()
    except Exception as exc:
        logger.error("db_update_artwork_multiple_fields_failed", artwork_id=artwork_id, error=str(exc))
        session.rollback()
    finally:
        session.close()


# ── Pipeline Nodes ───────────────────────────────────────────────────────────


async def analyze_artwork(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Analyze the artwork image."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("node_execute", node="analyze_artwork", artwork_id=artwork_id)
    _update_run_node(workflow_id, "analyze_artwork")

    try:
        # Load the artwork title from DB
        artwork_title = None
        from backend.database.session import get_sync_session
        from backend.models.artwork import Artwork
        from sqlalchemy import select

        session = get_sync_session()
        try:
            art = session.execute(
                select(Artwork).where(Artwork.id == uuid.UUID(artwork_id))
            ).scalar_one_or_none()
            if art:
                artwork_title = art.title
        finally:
            session.close()

        agent = ArtworkAnalyzerAgent()
        context = {
            "image_path": state["image_path"],
            "artwork_id": artwork_id,
            "artwork_title": artwork_title or "",
            "mime_type": state.get("mime_type", "image/png"),
        }

        result = await agent.execute(context)
        if not result.success:
            raise RuntimeError(result.error or "Artwork analysis agent failed.")

        # Save to database and set artwork status to processing
        _update_artwork_multiple_fields(artwork_id, {"analysis_data": result.data}, status="processing")

        return {
            "analysis": result.data,
            "current_node": "analyze_artwork",
            "workflow_status": "running",
        }
    except Exception as exc:
        err = _make_error("analyze_artwork", exc)
        _update_run_node(workflow_id, "analyze_artwork", status="failed", error_history=[err])
        return {
            "current_node": "analyze_artwork",
            "workflow_status": "failed",
            "error_history": [err],
        }


async def generate_metadata(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Generate artwork metadata from analysis."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("node_execute", node="generate_metadata", artwork_id=artwork_id)
    _update_run_node(workflow_id, "generate_metadata")

    try:
        agent = MetadataGeneratorAgent()
        context = {
            "analysis": state["analysis"],
            "artwork_id": artwork_id,
        }
        result = await agent.execute(context)
        if not result.success:
            raise RuntimeError(result.error or "Metadata generator agent failed.")

        # Saves to artworks.metadata
        _update_artwork_multiple_fields(artwork_id, {"metadata_": result.data})

        return {
            "metadata": result.data,
            "current_node": "generate_metadata",
        }
    except Exception as exc:
        err = _make_error("generate_metadata", exc)
        _update_run_node(workflow_id, "generate_metadata", status="failed", error_history=[err])
        return {
            "current_node": "generate_metadata",
            "workflow_status": "failed",
            "error_history": [err],
        }


async def generate_seo(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Generate SEO-optimized title, description, keywords."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("node_execute", node="generate_seo", artwork_id=artwork_id)
    _update_run_node(workflow_id, "generate_seo")

    try:
        agent = SEOAgent()
        context = {
            "analysis": state["analysis"],
            "artwork_id": artwork_id,
        }
        result = await agent.execute(context)
        if not result.success:
            raise RuntimeError(result.error or "SEO agent failed.")

        # Saves to artworks.seo_data
        _update_artwork_multiple_fields(artwork_id, {"seo_data": result.data})

        return {
            "seo": result.data,
            "current_node": "generate_seo",
        }
    except Exception as exc:
        err = _make_error("generate_seo", exc)
        _update_run_node(workflow_id, "generate_seo", status="failed", error_history=[err])
        return {
            "current_node": "generate_seo",
            "workflow_status": "failed",
            "error_history": [err],
        }


async def generate_caption(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Generate social media caption."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("node_execute", node="generate_caption", artwork_id=artwork_id)
    _update_run_node(workflow_id, "generate_caption")

    try:
        agent = CaptionAgent()
        context = {
            "analysis": state["analysis"],
            "seo": state["seo"],
            "artwork_id": artwork_id,
        }
        result = await agent.execute(context)
        if not result.success:
            raise RuntimeError(result.error or "Caption agent failed.")

        caption_text = result.data.get("instagram_caption", "")
        yt_description = result.data.get("youtube_description", "")
        yt_title = (state["seo"] or {}).get("seo_title", "")

        _update_artwork_multiple_fields(artwork_id, {
            "caption": caption_text,
            "youtube_title": yt_title,
            "youtube_description": yt_description,
        })

        return {
            "caption": caption_text,
            "youtube_title": yt_title,
            "youtube_description": yt_description,
            "current_node": "generate_caption",
        }
    except Exception as exc:
        err = _make_error("generate_caption", exc)
        _update_run_node(workflow_id, "generate_caption", status="failed", error_history=[err])
        return {
            "current_node": "generate_caption",
            "workflow_status": "failed",
            "error_history": [err],
        }


async def generate_hashtags(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Generate hashtags."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("node_execute", node="generate_hashtags", artwork_id=artwork_id)
    _update_run_node(workflow_id, "generate_hashtags")

    try:
        agent = HashtagAgent()
        context = {
            "analysis": state["analysis"],
            "seo": state["seo"],
            "artwork_id": artwork_id,
        }
        result = await agent.execute(context)
        if not result.success:
            raise RuntimeError(result.error or "Hashtag agent failed.")

        hashtags_list = result.data.get("hashtags", [])
        _update_artwork_multiple_fields(artwork_id, {"hashtags": hashtags_list})

        return {
            "hashtags": hashtags_list,
            "current_node": "generate_hashtags",
        }
    except Exception as exc:
        err = _make_error("generate_hashtags", exc)
        _update_run_node(workflow_id, "generate_hashtags", status="failed", error_history=[err])
        return {
            "current_node": "generate_hashtags",
            "workflow_status": "failed",
            "error_history": [err],
        }


async def generate_reel(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Generate reel/short video from artwork."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("node_execute", node="generate_reel", artwork_id=artwork_id)
    _update_run_node(workflow_id, "generate_reel")

    try:
        agent = ReelScriptAgent()
        context = {
            "analysis": state["analysis"],
            "caption": state["caption"],
            "artwork_id": artwork_id,
        }
        result = await agent.execute(context)
        if not result.success:
            raise RuntimeError(result.error or "Reel script agent failed.")

        _update_artwork_multiple_fields(artwork_id, {"reel_script": result.data})

        return {
            "reel_script": result.data,
            "current_node": "generate_reel",
        }
    except Exception as exc:
        err = _make_error("generate_reel", exc)
        _update_run_node(workflow_id, "generate_reel", status="failed", error_history=[err])
        return {
            "current_node": "generate_reel",
            "workflow_status": "failed",
            "error_history": [err],
        }


async def publish_instagram(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Publish to Instagram."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("node_execute", node="publish_instagram", artwork_id=artwork_id)
    _update_run_node(workflow_id, "publish_instagram")

    try:
        _update_run_publishing_status(workflow_id, "instagram", "pending")
        return {
            "instagram_status": "pending",
            "current_node": "publish_instagram",
        }
    except Exception as exc:
        err = _make_error("publish_instagram", exc)
        _update_run_node(workflow_id, "publish_instagram", status="failed", error_history=[err])
        return {
            "instagram_status": "failed",
            "current_node": "publish_instagram",
            "workflow_status": "failed",
            "error_history": [err],
        }


async def publish_youtube(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Publish to YouTube Shorts."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("node_execute", node="publish_youtube", artwork_id=artwork_id)
    _update_run_node(workflow_id, "publish_youtube")

    try:
        _update_run_publishing_status(workflow_id, "youtube", "pending")
        return {
            "youtube_status": "pending",
            "current_node": "publish_youtube",
        }
    except Exception as exc:
        err = _make_error("publish_youtube", exc)
        _update_run_node(workflow_id, "publish_youtube", status="failed", error_history=[err])
        return {
            "youtube_status": "failed",
            "current_node": "publish_youtube",
            "workflow_status": "failed",
            "error_history": [err],
        }


async def publish_pinterest(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Publish to Pinterest."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("node_execute", node="publish_pinterest", artwork_id=artwork_id)
    _update_run_node(workflow_id, "publish_pinterest")

    try:
        _update_run_publishing_status(workflow_id, "pinterest", "pending")
        return {
            "pinterest_status": "pending",
            "current_node": "publish_pinterest",
        }
    except Exception as exc:
        err = _make_error("publish_pinterest", exc)
        _update_run_node(workflow_id, "publish_pinterest", status="failed", error_history=[err])
        return {
            "pinterest_status": "failed",
            "current_node": "publish_pinterest",
            "workflow_status": "failed",
            "error_history": [err],
        }


async def publish_tiktok(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Publish to TikTok."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("node_execute", node="publish_tiktok", artwork_id=artwork_id)
    _update_run_node(workflow_id, "publish_tiktok")

    try:
        _update_run_publishing_status(workflow_id, "tiktok", "pending")
        return {
            "tiktok_status": "pending",
            "current_node": "publish_tiktok",
        }
    except Exception as exc:
        err = _make_error("publish_tiktok", exc)
        _update_run_node(workflow_id, "publish_tiktok", status="failed", error_history=[err])
        return {
            "tiktok_status": "failed",
            "current_node": "publish_tiktok",
            "workflow_status": "failed",
            "error_history": [err],
        }


async def collect_analytics(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Collect analytics across published platforms."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("node_execute", node="collect_analytics", artwork_id=artwork_id)
    _update_run_node(workflow_id, "collect_analytics", status="completed")

    # Update artwork status to completed since workflow completed
    _update_artwork_multiple_fields(artwork_id, {}, status="completed")

    return {
        "current_node": "collect_analytics",
        "workflow_status": "completed",
    }


async def handle_error(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Handle workflow errors — log, update status, notify."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.error(
        "workflow_error_handler",
        artwork_id=artwork_id,
        error_count=len(state.get("error_history", [])),
    )

    error_msg = "Workflow processing failed."
    if state.get("error_history"):
        error_msg = state["error_history"][-1].get("message", error_msg)

    _update_run_node(workflow_id, "error_handler", status="failed", error_history=state.get("error_history"))
    _update_artwork_multiple_fields(artwork_id, {"error_message": error_msg}, status="failed")

    return {
        "workflow_status": "failed",
        "current_node": "error_handler",
    }
