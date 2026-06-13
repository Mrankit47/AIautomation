"""Unit tests for the AI provider factory."""

from unittest.mock import patch

import pytest

from backend.config.settings import get_settings
from backend.providers.factory import get_provider
from backend.providers.gemini import GeminiProvider
from backend.providers.groq import GroqProvider


def test_provider_factory_get_gemini() -> None:
    """Test get_provider('gemini') returns GeminiProvider."""
    provider = get_provider("gemini")
    assert isinstance(provider, GeminiProvider)


def test_provider_factory_get_groq() -> None:
    """Test get_provider('groq') returns GroqProvider."""
    provider = get_provider("groq")
    assert isinstance(provider, GroqProvider)


def test_provider_factory_invalid_provider_raises() -> None:
    """Test get_provider with invalid provider name raises ValueError."""
    with pytest.raises(ValueError) as excinfo:
        get_provider("invalid-provider-name")
    assert "Unknown AI Provider" in str(excinfo.value)


def test_provider_factory_default_fallback() -> None:
    """Test get_provider() falls back to configured default setting."""
    with patch("backend.providers.factory.get_settings") as mock_settings:
        mock_settings.return_value.ai_provider = "groq"
        provider = get_provider()
        assert isinstance(provider, GroqProvider)

        mock_settings.return_value.ai_provider = "gemini"
        provider = get_provider()
        assert isinstance(provider, GeminiProvider)
