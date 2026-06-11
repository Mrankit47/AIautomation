"""System status and providers check API endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.config.settings import get_settings
from backend.providers.gemini import GeminiProvider
from backend.providers.groq import GroqProvider

router = APIRouter(prefix="/system", tags=["system"])


class ProviderStatusResponse(BaseModel):
    """Response schema representing provider health statuses."""

    gemini: str
    groq: str
    default_provider: str


@router.get("/providers", response_model=ProviderStatusResponse)
async def check_providers() -> ProviderStatusResponse:
    """Check the health check status of registered AI Providers (Gemini, Groq)."""
    gemini_prov = GeminiProvider()
    groq_prov = GroqProvider()

    gemini_healthy = await gemini_prov.health_check()
    groq_healthy = await groq_prov.health_check()

    return ProviderStatusResponse(
        gemini="healthy" if gemini_healthy else "unhealthy",
        groq="healthy" if groq_healthy else "unhealthy",
        default_provider=get_settings().ai_provider,
    )
