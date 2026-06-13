"""Unit tests for the Caption Agent using the Groq provider via factory."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.caption_agent import CaptionAgent


@pytest.mark.asyncio
async def test_caption_agent_groq_success() -> None:
    """Test CaptionAgent executes successfully when get_provider resolves to Groq."""
    mock_result_data = {
        "instagram_caption": "Vibrant concept art showing digital illustration.",
        "pinterest_description": "Beautiful concept art illustration in local styles.",
        "youtube_description": "Process details on concept art generation.",
    }

    mock_provider = AsyncMock()
    mock_provider.generate_structured.return_value.data = mock_result_data

    with patch("backend.agents.caption_agent.get_provider", return_value=mock_provider) as mock_get_provider:
        agent = CaptionAgent()
        context = {
            "analysis": {"subjects": ["digital illustration"], "colors": ["cyan"]},
            "seo": {"seo_title": "Concept Art Illustration"},
            "artwork_id": "test-artwork-id",
        }
        res = await agent.execute(context)

        assert res.success is True
        assert res.data == mock_result_data
        assert res.agent_name == "caption_agent"
        mock_get_provider.assert_called_once()
        mock_provider.generate_structured.assert_called_once()
