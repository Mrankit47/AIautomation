"""Provider factory for instantiating the active AI Provider."""

from __future__ import annotations

from backend.config.settings import get_settings
from backend.providers.base import AIProvider
from backend.providers.gemini import GeminiProvider
from backend.providers.groq import GroqProvider


def get_provider(provider_name: str | None = None) -> AIProvider:
    """Return the requested provider instance or fallback to default settings.

    Args:
        provider_name: Optional name (e.g., 'gemini', 'groq'). If not provided,
                       loaded from app settings.

    Returns:
        An instance of AIProvider.
    """
    if not provider_name:
        provider_name = get_settings().ai_provider

    provider_name = provider_name.strip().lower()

    if provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "groq":
        return GroqProvider()
    else:
        raise ValueError(f"Unknown AI Provider: {provider_name}")
