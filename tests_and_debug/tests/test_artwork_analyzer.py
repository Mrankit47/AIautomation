"""Unit tests for ArtworkAnalyzerAgent, including Gemini-to-Groq fallback."""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agents.artwork_analyzer import ArtworkAnalyzerAgent
from backend.agents.base import AgentResult
from backend.providers.base import AIImageAnalysisResult


@pytest.mark.asyncio
async def test_artwork_analyzer_gemini_success() -> None:
    """Test successful image analysis via Gemini."""
    agent = ArtworkAnalyzerAgent()
    context = {
        "image_path": "fake/path/art.png",
        "artwork_id": str(uuid.uuid4()),
        "artwork_title": "Test Artwork",
        "mime_type": "image/png",
    }

    mock_analysis_result = AIImageAnalysisResult(
        description="A beautiful digital artwork",
        labels=["nature", "digital"],
        metadata={"style": "digital", "mood": "calm", "primary_colors": ["blue"]},
        model="gemini-2.5-flash",
        usage={"total_tokens": 100},
        raw_response={}
    )

    with patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "read_bytes", return_value=b"fake-bytes"), \
         patch("backend.agents.artwork_analyzer.GeminiProvider") as mock_gemini_provider_cls:
        
        mock_gemini_inst = MagicMock()
        mock_gemini_inst.analyze_image = AsyncMock(return_value=mock_analysis_result)
        mock_gemini_provider_cls.return_value = mock_gemini_inst

        result = await agent.execute(context)

        assert result.success is True
        assert result.data["style"] == "digital"
        assert mock_gemini_inst.analyze_image.called


@pytest.mark.asyncio
async def test_artwork_analyzer_gemini_fails_groq_fallback_success() -> None:
    """Test that agent falls back to Groq when Gemini fails."""
    agent = ArtworkAnalyzerAgent()
    context = {
        "image_path": "fake/path/art.png",
        "artwork_id": str(uuid.uuid4()),
        "artwork_title": "Test Artwork",
        "mime_type": "image/png",
    }

    mock_groq_result = AIImageAnalysisResult(
        description="Plausible art fallback description",
        labels=["digital", "fallback"],
        metadata={"style": "illustration", "mood": "vibrant", "primary_colors": ["green"]},
        model="llama-3.3-70b-versatile",
        usage={"total_tokens": 80},
        raw_response={}
    )

    with patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "read_bytes", return_value=b"fake-bytes"), \
         patch("backend.agents.artwork_analyzer.GeminiProvider") as mock_gemini_provider_cls, \
         patch("backend.providers.groq.GroqProvider") as mock_groq_provider_cls:
        
        # Gemini fails
        mock_gemini_inst = MagicMock()
        mock_gemini_inst.analyze_image = AsyncMock(side_effect=RuntimeError("Gemini rate limit"))
        mock_gemini_provider_cls.return_value = mock_gemini_inst

        # Groq succeeds
        mock_groq_inst = MagicMock()
        mock_groq_inst.analyze_image = AsyncMock(return_value=mock_groq_result)
        mock_groq_provider_cls.return_value = mock_groq_inst

        result = await agent.execute(context)

        assert result.success is True
        assert result.data["style"] == "illustration"
        assert result.data["mood"] == "vibrant"
        assert mock_gemini_inst.analyze_image.called
        assert mock_groq_inst.analyze_image.called


@pytest.mark.asyncio
async def test_artwork_analyzer_both_fail() -> None:
    """Test that agent returns success=False when both providers fail."""
    agent = ArtworkAnalyzerAgent()
    context = {
        "image_path": "fake/path/art.png",
        "artwork_id": str(uuid.uuid4()),
        "artwork_title": "Test Artwork",
        "mime_type": "image/png",
    }

    with patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "read_bytes", return_value=b"fake-bytes"), \
         patch("backend.agents.artwork_analyzer.GeminiProvider") as mock_gemini_provider_cls, \
         patch("backend.providers.groq.GroqProvider") as mock_groq_provider_cls:
        
        # Gemini fails
        mock_gemini_inst = MagicMock()
        mock_gemini_inst.analyze_image = AsyncMock(side_effect=RuntimeError("Gemini error"))
        mock_gemini_provider_cls.return_value = mock_gemini_inst

        # Groq fails
        mock_groq_inst = MagicMock()
        mock_groq_inst.analyze_image = AsyncMock(side_effect=RuntimeError("Groq error"))
        mock_groq_provider_cls.return_value = mock_groq_inst

        result = await agent.execute(context)

        assert result.success is False
        assert "Both Gemini and Groq fallback failed" in result.error
