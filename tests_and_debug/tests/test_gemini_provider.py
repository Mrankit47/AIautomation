"""Unit tests for the upgraded Gemini provider using the new google-genai SDK."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.exceptions import AIProviderException
from backend.providers.base import (
    AIImageAnalysisResult,
    AIStructuredResult,
    AITextResult,
)
from backend.providers.gemini import GeminiProvider


@pytest.fixture
def mock_gemini_env():
    with patch.dict(os.environ, {
        "GEMINI__API_KEY": "test-gemini-key",
        "GEMINI__MODEL": "gemini-2.5-flash",
    }):
        yield


@pytest.mark.asyncio
async def test_gemini_provider_init_and_name(mock_gemini_env) -> None:
    """Test GeminiProvider initialization and basic properties."""
    provider = GeminiProvider()
    assert provider.provider_name == "Gemini"
    assert provider._model_name == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_gemini_provider_analyze_image_success(mock_gemini_env) -> None:
    """Test successful image analysis with mocked Client."""
    provider = GeminiProvider()

    # Mock response object from Client
    mock_response = MagicMock()
    mock_response.text = '{"description": "A beautiful painting", "subjects": ["landscape"]}'
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.candidates_token_count = 50
    mock_response.usage_metadata.total_token_count = 150

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    provider._client = mock_client

    result = await provider.analyze_image(
        image_data=b"fake-image-bytes",
        prompt="Analyze this artwork",
        mime_type="image/jpeg",
    )

    assert isinstance(result, AIImageAnalysisResult)
    assert result.description == "A beautiful painting"
    assert result.labels == ["landscape"]
    assert result.usage["total_tokens"] == 150
    assert mock_client.aio.models.generate_content.called


@pytest.mark.asyncio
async def test_gemini_provider_generate_text_success(mock_gemini_env) -> None:
    """Test successful text generation with mocked Client."""
    provider = GeminiProvider()

    mock_response = MagicMock()
    mock_response.text = "This is a generated social caption."
    mock_response.usage_metadata.prompt_token_count = 20
    mock_response.usage_metadata.candidates_token_count = 30
    mock_response.usage_metadata.total_token_count = 50

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    provider._client = mock_client

    result = await provider.generate_text(
        prompt="Write a caption",
        system_prompt="You are a helpful assistant",
        temperature=0.7,
        max_tokens=100,
    )

    assert isinstance(result, AITextResult)
    assert result.text == "This is a generated social caption."
    assert result.usage["total_tokens"] == 50
    assert mock_client.aio.models.generate_content.called


@pytest.mark.asyncio
async def test_gemini_provider_generate_structured_success(mock_gemini_env) -> None:
    """Test successful structured JSON output generation."""
    provider = GeminiProvider()

    mock_response = MagicMock()
    mock_response.text = '{"seo_title": "Cool Title", "seo_description": "Cool Desc", "seo_keywords": ["art"]}'
    mock_response.usage_metadata.prompt_token_count = 40
    mock_response.usage_metadata.candidates_token_count = 40
    mock_response.usage_metadata.total_token_count = 80

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
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
        prompt="Generate SEO details",
        output_schema=output_schema,
        system_prompt="You are a data assistant",
        temperature=0.3,
    )

    assert isinstance(result, AIStructuredResult)
    assert result.data["seo_title"] == "Cool Title"
    assert result.data["seo_keywords"] == ["art"]
    assert result.usage["total_tokens"] == 80


@pytest.mark.asyncio
async def test_gemini_provider_health_check_success(mock_gemini_env) -> None:
    """Test health check returns True on successful list call."""
    provider = GeminiProvider()
    mock_client = MagicMock()
    mock_client.aio.models.list = AsyncMock(return_value=["model1", "model2"])
    provider._client = mock_client

    status = await provider.health_check()
    assert status is True
    assert mock_client.aio.models.list.called


@pytest.mark.asyncio
async def test_gemini_provider_health_check_failure(mock_gemini_env) -> None:
    """Test health check returns False when list call fails."""
    provider = GeminiProvider()
    mock_client = MagicMock()
    mock_client.aio.models.list = AsyncMock(side_effect=Exception("API Error"))
    provider._client = mock_client

    status = await provider.health_check()
    assert status is False
