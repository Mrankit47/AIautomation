"""Strongly-typed LangGraph state for the artwork processing workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


@dataclass
class WorkflowError:
    """A single error entry in the workflow error history."""

    node: str
    error_type: str
    message: str
    timestamp: str
    recoverable: bool = True


def _append_errors(
    existing: list[dict[str, Any]],
    new: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reducer: append new errors to the existing error history."""
    return existing + new


class ArtworkWorkflowState(TypedDict):
    """Strongly-typed state for the artwork processing LangGraph workflow.

    Each field corresponds to a stage in the pipeline.  LangGraph reducers
    control how fields are merged when nodes return partial updates.
    """

    # ── Identity ─────────────────────────────────────────────────────────
    artwork_id: str
    workflow_id: str
    workflow_version: str

    # ── Input ────────────────────────────────────────────────────────────
    image_path: str
    storage_url: str
    original_filename: str
    category: str

    # ── Analysis ─────────────────────────────────────────────────────────
    analysis: dict[str, Any] | None

    # ── Generated Content ────────────────────────────────────────────────
    metadata: dict[str, Any] | None
    seo: dict[str, Any] | None
    caption: str | None
    hashtags: list[str] | None
    youtube_title: str | None
    youtube_description: str | None

    # ── Media ────────────────────────────────────────────────────────────
    reel_script: dict[str, Any] | None
    reel_path: str | None

    # ── Publishing Status ────────────────────────────────────────────────
    instagram_status: str | None
    youtube_status: str | None
    pinterest_status: str | None
    tiktok_status: str | None

    # ── Workflow Control ─────────────────────────────────────────────────
    workflow_status: str  # pending | running | completed | failed
    current_node: str

    # ── Error Tracking (append-only) ─────────────────────────────────────
    error_history: Annotated[list[dict[str, Any]], _append_errors]

    # ── LangGraph Messages ───────────────────────────────────────────────
    messages: Annotated[list[Any], add_messages]
