"""Unit tests for the Google Gemini provider."""

import os
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from backend.config.settings import get_settings
from backend.core.exceptions import AIProviderException
from backend.providers.base import AIImageAnalysisResult, AITextResult, AIStructuredResult
from backend.providers.gemini import GeminiProvider


@pytest.fixture
def mock_gemini_env():
    # Clear settings cache to ensure env dict changes are picked up
    get_settings.cache_clear()
    with patch.dict(os.environ, {
        "GEMINI__API_KEY": "test-gemini-key",
        "GEMINI__MODEL": "gemini-2.5-flash",
        "GEMINI__TIMEOUT": "60",
    }):
        yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_gemini_provider_init_and_timeout(mock_gemini_env) -> None:
    """Test GeminiProvider initialization and timeout conversion (seconds to milliseconds)."""
    with patch("google.genai.Client") as mock_client:
        provider = GeminiProvider()
        assert provider.provider_name == "Gemini"
        assert provider._model_name == "gemini-2.5-flash"
        # 60 seconds should be converted to 60000 milliseconds
        assert provider._timeout == 60000
        mock_client.assert_called_once_with(api_key="test-gemini-key")


@pytest.mark.asyncio
async def test_gemini_provider_analyze_image_compression(mock_gemini_env) -> None:
    """Test that analyze_image compresses large images before sending them to Gemini."""
    with patch("google.genai.Client") as mock_client:
        # Create a large mock image (2000x2000 pixels) in memory
        large_img = Image.new("RGB", (2000, 2000), color="blue")
        out_buf = BytesIO()
        large_img.save(out_buf, format="JPEG")
        large_image_bytes = out_buf.getvalue()
        original_size = len(large_image_bytes)

        # Mock generating content response
        mock_response = MagicMock()
        mock_response.text = '{"style": "abstract", "mood": "calm", "subjects": ["sky"], "category": "digital_art", "description": "test description"}'
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50
        mock_response.usage_metadata.total_token_count = 150

        # Set up mock client structures
        mock_generate = AsyncMock(return_value=mock_response)
        mock_client.return_value.aio.models.generate_content = mock_generate

        provider = GeminiProvider()

        # Patch types.Part.from_bytes to inspect the compressed size
        with patch("google.genai.types.Part.from_bytes") as mock_from_bytes:
            mock_from_bytes.return_value = MagicMock()

            result = await provider.analyze_image(
                image_data=large_image_bytes,
                prompt="Analyze this image",
                mime_type="image/jpeg"
            )

            # Assert that types.Part.from_bytes was called with a compressed byte payload
            assert mock_from_bytes.called
            args, kwargs = mock_from_bytes.call_args
            compressed_data = kwargs.get("data") or args[0]
            
            # The compressed data size must be significantly smaller than the original 2000x2000 uncompressed size
            assert len(compressed_data) < original_size
            assert kwargs.get("mime_type") == "image/jpeg"

            assert isinstance(result, AIImageAnalysisResult)
            assert result.metadata["style"] == "abstract"
            assert result.metadata["description"] == "test description"
