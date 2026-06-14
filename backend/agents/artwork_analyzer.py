"""Artwork analysis agent — analyzes visual properties using Gemini vision."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from backend.agents.base import AgentResult, BaseAgent
from backend.core.logging import get_logger
from backend.prompts.registry import PromptRegistry
from backend.providers.gemini import GeminiProvider

logger = get_logger(__name__)


class ArtworkAnalyzerAgent(BaseAgent):
    """Analyzes an artwork image for style, medium, mood, and subjects."""

    @property
    def name(self) -> str:
        return "artwork_analyzer"

    @property
    def role(self) -> str:
        return "Art Analyst"

    @property
    def goal(self) -> str:
        return (
            "Analyze artwork images to extract style, medium, mood, "
            "subject matter, color palette, and composition details."
        )

    @property
    def backstory(self) -> str:
        return (
            "You are an expert art critic and analyst with decades of "
            "experience studying art across all periods and styles. You can "
            "identify techniques, influences, and emotional undertones in "
            "any artwork with remarkable precision."
        )

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Analyze the artwork image using Gemini vision.

        Expected context keys:
            - image_path: str — path to the artwork image file
            - artwork_id: str — UUID of the artwork
            - artwork_title: str — optional title
        """
        start_time = time.monotonic()
        artwork_id = context.get("artwork_id", "unknown")

        logger.info(
            "artwork_analyzer_execute",
            artwork_id=artwork_id,
        )

        try:
            # Load prompt template
            registry = PromptRegistry()
            prompt_template = registry.get("artwork_analysis", version="v1")

            # Render the user prompt
            rendered_prompt = prompt_template.render(
                artwork_title=context.get("artwork_title", ""),
            )

            # Read image file
            image_path = Path(context["image_path"])
            if not image_path.exists():
                return AgentResult(
                    success=False,
                    error=f"Image file not found: {image_path}",
                    agent_name=self.name,
                    execution_time_ms=(time.monotonic() - start_time) * 1000,
                )

            image_data = image_path.read_bytes()
            mime_type = context.get("mime_type", "image/png")

            # Build full prompt with system instructions
            full_prompt = (
                f"{prompt_template.system_prompt}\n\n{rendered_prompt}"
            )

            # Call Gemini vision API with fallback to Groq on failure
            analysis_data = None
            try:
                provider = GeminiProvider()
                result = await provider.analyze_image(
                    image_data=image_data,
                    prompt=full_prompt,
                    mime_type=mime_type,
                )
                analysis_data = result.metadata
            except Exception as gemini_exc:
                logger.warning(
                    "gemini_analysis_failed_falling_back_to_groq",
                    artwork_id=artwork_id,
                    error=str(gemini_exc),
                )
                try:
                    from backend.providers.groq import GroqProvider
                    groq_provider = GroqProvider()
                    result = await groq_provider.analyze_image(
                        image_data=image_data,
                        prompt=full_prompt,
                        mime_type=mime_type,
                    )
                    analysis_data = result.metadata
                except Exception as groq_exc:
                    logger.error(
                        "groq_fallback_failed",
                        artwork_id=artwork_id,
                        error=str(groq_exc),
                    )
                    return AgentResult(
                        success=False,
                        error=f"Both Gemini and Groq fallback failed. Gemini error: {gemini_exc}. Groq error: {groq_exc}",
                        agent_name=self.name,
                        execution_time_ms=(time.monotonic() - start_time) * 1000,
                    )

            elapsed = (time.monotonic() - start_time) * 1000
            logger.info(
                "artwork_analyzer_success",
                artwork_id=artwork_id,
                execution_time_ms=elapsed,
            )

            return AgentResult(
                success=True,
                data=analysis_data,  # The full parsed JSON
                agent_name=self.name,
                execution_time_ms=elapsed,
            )

        except Exception as exc:
            elapsed = (time.monotonic() - start_time) * 1000
            logger.error(
                "artwork_analyzer_failed",
                artwork_id=artwork_id,
                error=str(exc),
                execution_time_ms=elapsed,
            )
            return AgentResult(
                success=False,
                error=str(exc),
                agent_name=self.name,
                execution_time_ms=elapsed,
            )
