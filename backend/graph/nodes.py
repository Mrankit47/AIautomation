"""LangGraph node functions for the artwork processing workflow.

Each node is an async function that receives the current state, performs
its task, updates the database in a production-safe way, and returns a
partial state update dict.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import os
from backend.agents.artwork_analyzer import ArtworkAnalyzerAgent
from backend.agents.caption_agent import CaptionAgent
from backend.agents.hashtag_agent import HashtagAgent
from backend.agents.metadata_generator import MetadataGeneratorAgent
from backend.agents.reel_script_agent import ReelScriptAgent
from backend.agents.seo_agent import SEOAgent
from backend.core.logging import get_logger
from backend.graph.state import ArtworkWorkflowState
from backend.services.reel_generator import ReelGenerator

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
            elif status == "completed_with_warnings":
                run.status = WorkflowStatus.COMPLETED_WITH_WARNINGS

            if error_history is not None:
                current_errs = list(run.error_history or [])
                for eh in error_history:
                    if eh not in current_errs:
                        current_errs.append(eh)
                run.error_history = current_errs

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
        _update_run_node(workflow_id, "generate_caption", status="running", error_history=[err])
        return {
            "caption": None,
            "youtube_title": None,
            "youtube_description": None,
            "current_node": "generate_caption",
            "workflow_status": "completed_with_warnings",
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
        _update_run_node(workflow_id, "generate_hashtags", status="running", error_history=[err])
        return {
            "hashtags": None,
            "current_node": "generate_hashtags",
            "workflow_status": "completed_with_warnings",
            "error_history": [err],
        }


async def generate_reel(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Generate reel/short video from artwork."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("node_execute", node="generate_reel", artwork_id=artwork_id)
    _update_run_node(workflow_id, "generate_reel")

    # Structured logging for start
    logger.info("reel_script_start", artwork_id=artwork_id, workflow_id=workflow_id)

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

        # Real reel rendering instead of simulated path
        logger.info("reel_render_started", artwork_id=artwork_id, workflow_id=workflow_id)

        output_dir = "/app/outputs/reels"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"{artwork_id}.mp4")

        try:
            generator = ReelGenerator()
            reel_path = generator.generate_reel(
                image_path=state["image_path"],
                output_path=output_path,
                reel_script=result.data,
            )
            logger.info("reel_render_completed", artwork_id=artwork_id, workflow_id=workflow_id, reel_path=reel_path)
        except Exception as render_exc:
            logger.error("reel_render_failed", artwork_id=artwork_id, workflow_id=workflow_id, error=str(render_exc))
            raise render_exc

        _update_artwork_multiple_fields(
            artwork_id,
            {
                "reel_script": result.data,
                "reel_path": reel_path,
            }
        )

        # Structured logging for success
        logger.info(
            "reel_script_success",
            artwork_id=artwork_id,
            workflow_id=workflow_id,
            execution_time_ms=result.execution_time_ms,
        )

        return {
            "reel_script": result.data,
            "reel_path": reel_path,
            "current_node": "generate_reel",
        }
    except Exception as exc:
        # Structured logging for failure
        logger.error(
            "reel_script_failure",
            artwork_id=artwork_id,
            workflow_id=workflow_id,
            error=str(exc),
        )

        err = _make_error("generate_reel", exc)
        _update_run_node(workflow_id, "generate_reel", status="running", error_history=[err])
        return {
            "reel_script": None,
            "reel_path": None,
            "current_node": "generate_reel",
            "workflow_status": "completed_with_warnings",
            "error_history": [err],
        }


async def publish_instagram(state: ArtworkWorkflowState) -> dict[str, Any]:
    """Node: Publish to Instagram."""
    artwork_id = state["artwork_id"]
    workflow_id = state["workflow_id"]
    logger.info("instagram_publish_started", artwork_id=artwork_id, workflow_id=workflow_id)
    _update_run_node(workflow_id, "publish_instagram")
    _update_run_publishing_status(workflow_id, "instagram", "pending")
    _update_artwork_multiple_fields(artwork_id, {"instagram_status": "pending"})

    try:
        # Load reel_path and caption from DB
        from backend.database.session import get_sync_session
        from backend.models.artwork import Artwork
        from sqlalchemy import select

        session = get_sync_session()
        reel_path = None
        caption = None
        try:
            art = session.execute(
                select(Artwork).where(Artwork.id == uuid.UUID(artwork_id))
            ).scalar_one_or_none()
            if art:
                reel_path = art.reel_path
                caption = art.caption
        finally:
            session.close()

        if not reel_path:
            raise ValueError("No generated reel path found to publish.")
        if not caption:
            raise ValueError("No caption found to publish.")

        # Transition to processing status
        _update_run_publishing_status(workflow_id, "instagram", "processing")
        _update_artwork_multiple_fields(artwork_id, {"instagram_status": "processing"})

        # Instantiate service and publish
        from backend.services.instagram_publisher import InstagramPublisher
        publisher = InstagramPublisher()
        result = await publisher.publish_reel(reel_path, caption)

        # Success - update fields and set status to published
        _update_artwork_multiple_fields(
            artwork_id,
            {
                "instagram_status": "published",
                "instagram_post_id": result["instagram_post_id"],
                "instagram_permalink": result["instagram_permalink"],
                "instagram_published_at": result["instagram_published_at"],
            }
        )
        _update_run_publishing_status(workflow_id, "instagram", "published")
        logger.info("instagram_publish_completed", artwork_id=artwork_id, workflow_id=workflow_id, post_id=result["instagram_post_id"])

        return {
            "instagram_status": "published",
            "current_node": "publish_instagram",
        }
    except Exception as exc:
        logger.error("instagram_publish_failed", artwork_id=artwork_id, workflow_id=workflow_id, error=str(exc))
        err = _make_error("publish_instagram", exc)
        _update_run_node(workflow_id, "publish_instagram", status="failed", error_history=[err])
        _update_run_publishing_status(workflow_id, "instagram", "failed")
        _update_artwork_multiple_fields(artwork_id, {"instagram_status": "failed", "error_message": str(exc)})
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
    logger.info("youtube_publish_started", artwork_id=artwork_id, workflow_id=workflow_id)
    _update_run_node(workflow_id, "publish_youtube")
    _update_run_publishing_status(workflow_id, "youtube", "pending")
    _update_artwork_multiple_fields(artwork_id, {"youtube_status": "pending"})

    try:
        # Load reel_path, youtube_title, and youtube_description from DB
        from backend.database.session import get_sync_session
        from backend.models.artwork import Artwork
        from sqlalchemy import select

        session = get_sync_session()
        reel_path = None
        title = None
        description = None
        try:
            art = session.execute(
                select(Artwork).where(Artwork.id == uuid.UUID(artwork_id))
            ).scalar_one_or_none()
            if art:
                reel_path = art.reel_path
                title = art.youtube_title or art.title or art.original_filename.rsplit(".", 1)[0]
                description = art.youtube_description or art.caption or ""
        finally:
            session.close()

        if not reel_path:
            raise ValueError("No generated reel path found to publish to YouTube.")

        # Transition to processing status
        _update_run_publishing_status(workflow_id, "youtube", "processing")
        _update_artwork_multiple_fields(artwork_id, {"youtube_status": "processing"})

        # Instantiate service and publish
        from backend.services.youtube_publisher import YouTubePublisher
        publisher = YouTubePublisher()
        result = await publisher.publish_short(
            reel_path=reel_path,
            title=title,
            description=description,
        )

        # Success - update fields and set status to published
        _update_artwork_multiple_fields(
            artwork_id,
            {
                "youtube_status": "published",
                "youtube_video_id": result["youtube_video_id"],
                "youtube_url": result["youtube_url"],
                "youtube_published_at": result["youtube_published_at"],
            }
        )
        _update_run_publishing_status(workflow_id, "youtube", "published")
        logger.info("youtube_publish_completed", artwork_id=artwork_id, workflow_id=workflow_id, video_id=result["youtube_video_id"])

        return {
            "youtube_status": "published",
            "current_node": "publish_youtube",
        }
    except Exception as exc:
        logger.error("youtube_publish_failed", artwork_id=artwork_id, workflow_id=workflow_id, error=str(exc))
        err = _make_error("publish_youtube", exc)
        _update_run_node(workflow_id, "publish_youtube", status="failed", error_history=[err])
        _update_run_publishing_status(workflow_id, "youtube", "failed")
        _update_artwork_multiple_fields(artwork_id, {"youtube_status": "failed", "error_message": str(exc)})
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
    logger.info("analytics_collection_started", artwork_id=artwork_id, workflow_id=workflow_id)
    _update_run_node(workflow_id, "collect_analytics")

    # Load artwork details and invoke publisher analytics
    from backend.database.session import get_sync_session
    from backend.models.artwork import Artwork
    from backend.models.analytics import ArtworkAnalytics
    from sqlalchemy import select

    session = get_sync_session()
    try:
        art = session.execute(
            select(Artwork).where(Artwork.id == uuid.UUID(artwork_id))
        ).scalar_one_or_none()
        if art:
            # ── Instagram Analytics Collection ──
            if art.instagram_status == "published" and art.instagram_post_id:
                try:
                    from backend.services.instagram_analytics import InstagramAnalyticsService
                    ig_service = InstagramAnalyticsService()
                    ig_metrics = await ig_service.collect_metrics(art.instagram_post_id)
                    
                    ig_analytics = ArtworkAnalytics(
                        artwork_id=art.id,
                        platform="instagram",
                        views=ig_metrics["views"],
                        reach=ig_metrics["reach"],
                        impressions=ig_metrics["impressions"],
                        likes=ig_metrics["likes"],
                        comments=ig_metrics["comments"],
                        shares=ig_metrics["shares"],
                        saves=ig_metrics["saves"],
                        watch_time=ig_metrics["watch_time"],
                        engagement_rate=ig_metrics["engagement_rate"],
                        collected_at=ig_metrics["collected_at"],
                    )
                    session.add(ig_analytics)
                except Exception as e:
                    logger.warning("instagram_analytics_collection_failed_in_node", artwork_id=artwork_id, error=str(e))

            # ── YouTube Analytics Collection ──
            if art.youtube_status == "published" and art.youtube_video_id:
                try:
                    from backend.services.youtube_analytics import YouTubeAnalyticsService
                    yt_service = YouTubeAnalyticsService()
                    yt_metrics = await yt_service.collect_metrics(art.youtube_video_id, art.youtube_published_at)
                    
                    yt_analytics = ArtworkAnalytics(
                        artwork_id=art.id,
                        platform="youtube",
                        views=yt_metrics["views"],
                        reach=yt_metrics["reach"],
                        impressions=yt_metrics["impressions"],
                        likes=yt_metrics["likes"],
                        comments=yt_metrics["comments"],
                        shares=yt_metrics["shares"],
                        saves=yt_metrics["saves"],
                        watch_time=yt_metrics["watch_time"],
                        engagement_rate=yt_metrics["engagement_rate"],
                        collected_at=yt_metrics["collected_at"],
                    )
                    session.add(yt_analytics)
                except Exception as e:
                    logger.warning("youtube_analytics_collection_failed_in_node", artwork_id=artwork_id, error=str(e))

        session.commit()
    except Exception as exc:
        logger.error("analytics_persistence_failed_in_node", artwork_id=artwork_id, error=str(exc))
        session.rollback()
    finally:
        session.close()

    # Mark node and artwork as completed
    final_status = "completed"
    if state.get("workflow_status") == "completed_with_warnings":
        final_status = "completed_with_warnings"

    _update_run_node(workflow_id, "collect_analytics", status=final_status)
    _update_artwork_multiple_fields(artwork_id, {}, status=final_status)
    logger.info("analytics_collection_completed", artwork_id=artwork_id, workflow_id=workflow_id, status=final_status)

    return {
        "current_node": "collect_analytics",
        "workflow_status": final_status,
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
