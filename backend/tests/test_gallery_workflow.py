import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.graph.state import ArtworkWorkflowState
from backend.graph.workflow import build_artwork_workflow
from backend.graph.nodes import generate_reel, publish_youtube

@pytest.mark.asyncio
async def test_workflow_routing_skips_youtube_for_gallery():
    # Test routing logic directly
    from backend.graph.workflow import _after_publish_instagram, _should_generate_reel, _after_reel
    from backend.config.settings import get_settings
    
    # Mock settings
    settings = get_settings()
    settings.feature_flags.enable_youtube_publish = True
    
    state: ArtworkWorkflowState = {
        "artwork_id": "mock-id",
        "workflow_id": "mock-run-id",
        "category": "gallery",
        "workflow_status": "RUNNING",
    }
    
    # Category gallery must return publish_pinterest, collect_analytics or end, but NOT publish_youtube
    next_step = _after_publish_instagram(state)
    assert next_step != "publish_youtube"

@pytest.mark.asyncio
@patch("backend.graph.nodes.ReelGenerator")
@patch("backend.graph.nodes.ReelScriptAgent")
@patch("backend.graph.nodes._update_artwork_multiple_fields")
@patch("backend.graph.nodes._update_run_node")
async def test_generate_reel_node_is_static_for_gallery(
    mock_update_run_node,
    mock_update_fields,
    mock_reel_script_agent,
    mock_reel_generator_class,
):
    mock_generator = MagicMock()
    mock_generator.generate_reel.return_value = "mock_reel_path.mp4"
    mock_reel_generator_class.return_value = mock_generator
    
    state = {
        "artwork_id": "12345678-1234-1234-1234-123456789012",
        "workflow_id": "87654321-4321-4321-4321-210987654321",
        "category": "gallery",
        "image_path": "test_image.jpg",
        "analysis": {},
        "caption": "Test caption",
    }
    
    result = await generate_reel(state)
    
    # Verify ReelScriptAgent was NOT instantiated or called
    mock_reel_script_agent.assert_not_called()
    
    # Verify ReelGenerator was called with is_static=True
    from unittest.mock import ANY
    mock_generator.generate_reel.assert_called_once_with(
        image_path="test_image.jpg",
        output_path=ANY,
        reel_script={},
        analysis={},
        is_static=True,
    )
    
    assert result["reel_script"] is None
    assert result["reel_path"] == "mock_reel_path.mp4"

@pytest.mark.asyncio
@patch("backend.graph.nodes._update_run_publishing_status")
@patch("backend.graph.nodes._update_artwork_multiple_fields")
@patch("backend.graph.nodes._update_run_node")
async def test_publish_youtube_skipped_for_gallery(
    mock_update_run_node,
    mock_update_fields,
    mock_update_publishing,
):
    state = {
        "artwork_id": "12345678-1234-1234-1234-123456789012",
        "workflow_id": "87654321-4321-4321-4321-210987654321",
        "category": "gallery",
    }
    
    result = await publish_youtube(state)
    assert result["youtube_status"] == "skipped"
    mock_update_fields.assert_called_once_with("12345678-1234-1234-1234-123456789012", {"youtube_status": "skipped"})
    mock_update_publishing.assert_called_once_with("87654321-4321-4321-4321-210987654321", "youtube", "skipped")
