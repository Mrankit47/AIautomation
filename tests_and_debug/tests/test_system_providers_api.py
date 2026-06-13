"""Tests for the system status and providers check API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app


def test_get_system_providers_api_endpoint() -> None:
    """Test GET /api/v1/system/providers returns correct health and default provider."""
    client = TestClient(app)

    with patch("backend.api.v1.system.GeminiProvider") as mock_gemini_class:
        mock_gemini = AsyncMock()
        mock_gemini.health_check.return_value = True
        mock_gemini_class.return_value = mock_gemini

        with patch("backend.api.v1.system.GroqProvider") as mock_groq_class:
            mock_groq = AsyncMock()
            mock_groq.health_check.return_value = False
            mock_groq_class.return_value = mock_groq

            with patch("backend.api.v1.system.get_settings") as mock_settings:
                mock_settings.return_value.ai_provider = "groq"

                response = client.get("/api/v1/system/providers")
                
                assert response.status_code == 200
                data = response.json()
                assert data["gemini"] == "healthy"
                assert data["groq"] == "unhealthy"
                assert data["default_provider"] == "groq"
