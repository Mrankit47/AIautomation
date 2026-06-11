"""Unit tests for workflow warnings propagation and graph node resiliency."""

from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from backend.agents.base import AgentResult
from backend.graph.workflow import compile_artwork_workflow


@pytest.mark.asyncio
async def test_workflow_warning_propagation() -> None:
    """Test that CaptionAgent failure propagates as a warning and lets the workflow complete."""
    # Compile the graph
    graph = compile_artwork_workflow()

    artwork_id = str(uuid.uuid4())
    workflow_id = str(uuid.uuid4())

    initial_state = {
        "artwork_id": artwork_id,
        "workflow_id": workflow_id,
        "workflow_version": "v1",
        "image_path": "artworks/test.png",
        "storage_url": "http://mock/test.png",
        "original_filename": "test.png",
        "analysis": {"subjects": ["test"]},
        "metadata": None,
        "seo": None,
        "caption": None,
        "hashtags": None,
        "youtube_title": None,
        "youtube_description": None,
        "reel_script": None,
        "reel_path": None,
        "instagram_status": None,
        "youtube_status": None,
        "workflow_status": "running",
        "current_node": "start",
        "error_history": [],
        "messages": [],
    }

    # Mock database helpers
    with patch("backend.graph.nodes._update_run_node") as mock_update_run, \
         patch("backend.graph.nodes._update_artwork_multiple_fields") as mock_update_art:

        mock_analyzer = AsyncMock(return_value=AgentResult(success=True, data={"subjects": ["landscape"]}))
        mock_metadata = AsyncMock(return_value=AgentResult(success=True, data={"title": "Test Artwork"}))
        mock_seo = AsyncMock(return_value=AgentResult(success=True, data={"seo_title": "SEO Title"}))
        mock_caption = AsyncMock(return_value=AgentResult(success=False, error="Caption API timeout"))
        mock_hashtags = AsyncMock(return_value=AgentResult(success=True, data={"hashtags": ["#test"]}))

        with patch("backend.graph.nodes.ArtworkAnalyzerAgent.execute", mock_analyzer), \
             patch("backend.graph.nodes.MetadataGeneratorAgent.execute", mock_metadata), \
             patch("backend.graph.nodes.SEOAgent.execute", mock_seo), \
             patch("backend.graph.nodes.CaptionAgent.execute", mock_caption), \
             patch("backend.graph.nodes.HashtagAgent.execute", mock_hashtags), \
             patch("backend.graph.workflow.get_settings") as mock_settings:

             mock_settings.return_value.feature_flags.enable_reel_generation = False
             mock_settings.return_value.feature_flags.enable_instagram_publish = False
             mock_settings.return_value.feature_flags.enable_youtube_publish = False
             mock_settings.return_value.feature_flags.enable_analytics_collection = True

             with patch("backend.database.session.get_sync_session") as mock_get_sync_session:
                 mock_session_inst = MagicMock()
                 mock_get_sync_session.return_value = mock_session_inst
                 
                 # Invoke workflow graph
                 final_state = await graph.ainvoke(initial_state)

                 # State checks
                 assert final_state["workflow_status"] == "completed_with_warnings"
                 assert len(final_state["error_history"]) == 1
                 assert final_state["error_history"][0]["node"] == "generate_caption"
                 assert final_state["error_history"][0]["message"] == "Caption API timeout"

                 # Verification of helper update calls
                 mock_update_run.assert_any_call(
                     workflow_id,
                     "collect_analytics",
                     status="completed_with_warnings"
                 )
