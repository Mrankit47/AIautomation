"""Unit tests for the Reel Script Agent using the Groq provider via factory."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.reel_script_agent import ReelScriptAgent


@pytest.mark.asyncio
async def test_reel_script_agent_groq_success() -> None:
    """Test ReelScriptAgent executes successfully when get_provider resolves to Groq."""
    mock_result_data = {
        "hook": "Watch how this concept art was made!",
        "narration": "First I sketch the details, then I paint the light.",
        "visuals": "Timelapse video showing digital concept art creation.",
        "call_to_action": "Follow for more art tutorials!",
    }

    mock_provider = AsyncMock()
    mock_provider.generate_structured.return_value.data = mock_result_data

    with patch("backend.agents.reel_script_agent.get_provider", return_value=mock_provider) as mock_get_provider:
        agent = ReelScriptAgent()
        context = {
            "analysis": {"subjects": ["digital illustration"], "colors": ["cyan"]},
            "caption": "Workflow caption text.",
            "artwork_id": "test-artwork-id",
        }
        res = await agent.execute(context)

        assert res.success is True
        assert res.data == mock_result_data
        assert res.agent_name == "reel_script_agent"
        mock_get_provider.assert_called_once()
        mock_provider.generate_structured.assert_called_once()
