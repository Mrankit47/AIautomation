"""Unit tests for the Groq provider."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.config.settings import get_settings
from backend.core.exceptions import AIProviderException
from backend.providers.base import AIStructuredResult, AITextResult
from backend.providers.groq import GroqProvider


@pytest.fixture
def mock_groq_env():
    with patch.dict(os.environ, {
        "GROQ_API_KEY": "test-groq-key",
        "GROQ_MODEL": "llama-3.3-70b-versatile",
    }):
        yield


@pytest.mark.asyncio
async def test_groq_provider_init_and_name(mock_groq_env) -> None:
    """Test GroqProvider initialization and basic property attributes."""
    provider = GroqProvider()
    assert provider.provider_name == "Groq"
    assert provider._model_name == "llama-3.3-70b-versatile"


@pytest.mark.asyncio
async def test_groq_provider_analyze_image_raises(mock_groq_env) -> None:
    """Test analyze_image raises NotImplementedError for Groq."""
    provider = GroqProvider()
    with pytest.raises(NotImplementedError):
        await provider.analyze_image(b"fake-image-bytes", "fake-prompt")


@pytest.mark.asyncio
async def test_groq_provider_generate_text_success(mock_groq_env) -> None:
    """Test successful generate_text execution with mock AsyncGroq."""
    provider = GroqProvider()

    # Mock response completion
    mock_choice = MagicMock()
    mock_choice.message.content = "This is a groq generated caption response."
    
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 30
    mock_response.model_dump.return_value = {"mock": "data"}

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response
    provider._client = mock_client

    result = await provider.generate_text(
        prompt="Write a caption",
        system_prompt="You are a writer",
        temperature=0.7,
        max_tokens=100,
    )

    assert isinstance(result, AITextResult)
    assert result.text == "This is a groq generated caption response."
    assert result.model == "llama-3.3-70b-versatile"
    assert result.usage["total_tokens"] == 30
    assert mock_client.chat.completions.create.called


@pytest.mark.asyncio
async def test_groq_provider_generate_structured_success(mock_groq_env) -> None:
    """Test successful generate_structured execution using JSON Mode."""
    provider = GroqProvider()

    mock_choice = MagicMock()
    mock_choice.message.content = '{"seo_title": "Cool Title", "seo_description": "Cool Desc", "seo_keywords": ["art"]}'
    
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 50
    mock_response.usage.completion_tokens = 60
    mock_response.usage.total_tokens = 110
    mock_response.model_dump.return_value = {"mock": "data"}

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response
    provider._client = mock_client

    output_schema = {
        "type": "object",
        "properties": {
            "seo_title": {"type": "string"},
            "seo_description": {"type": "string"},
            "seo_keywords": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["seo_title", "seo_description", "seo_keywords"],
    }

    result = await provider.generate_structured(
        prompt="Write SEO details",
        output_schema=output_schema,
        system_prompt="You are a data assistant",
        temperature=0.3,
    )

    assert isinstance(result, AIStructuredResult)
    assert result.data["seo_title"] == "Cool Title"
    assert result.data["seo_keywords"] == ["art"]
    assert result.usage["total_tokens"] == 110


@pytest.mark.asyncio
async def test_groq_provider_generate_text_failure_and_retries(mock_groq_env) -> None:
    """Test that GroqProvider retry logic triggers and raises AIProviderException after failure."""
    provider = GroqProvider()
    provider._max_retries = 2

    mock_client = AsyncMock()
    # Call fails with exception every time
    mock_client.chat.completions.create.side_effect = Exception("Groq RateLimitError")
    provider._client = mock_client

    with patch("time.sleep") as mock_sleep:  # bypass sleeping in tests
        with pytest.raises(AIProviderException) as excinfo:
            await provider.generate_text("test prompt")
        
        assert "Groq text generation failed" in str(excinfo.value)
        # 1 initial try + 2 retries = 3 calls
        assert mock_client.chat.completions.create.call_count == 3
        assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_groq_provider_health_check_success(mock_groq_env) -> None:
    """Test health check returns True on successful completion."""
    provider = GroqProvider()
    mock_client = AsyncMock()
    provider._client = mock_client
    
    status = await provider.health_check()
    assert status is True
    assert mock_client.chat.completions.create.called


@pytest.mark.asyncio
async def test_groq_provider_health_check_failure(mock_groq_env) -> None:
    """Test health check returns False on exception."""
    provider = GroqProvider()
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API Key Invalid")
    provider._client = mock_client
    
    status = await provider.health_check()
    assert status is False
