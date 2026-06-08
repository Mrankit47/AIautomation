"""Hashtag generation agent — generates optimized hashtags using Gemini."""

from __future__ import annotations

import json
import time
from typing import Any

from backend.agents.base import AgentResult, BaseAgent
from backend.core.logging import get_logger
from backend.prompts.registry import PromptRegistry
from backend.providers.gemini import GeminiProvider

logger = get_logger(__name__)


class HashtagAgent(BaseAgent):
    """Generates 20 optimized hashtags for social media."""

    @property
    def name(self) -> str:
        return "hashtag_agent"

    @property
    def role(self) -> str:
        return "Hashtag Strategist"

    @property
    def goal(self) -> str:
        return (
            "Generate 20 optimized hashtags with a mix of high-volume "
            "and niche tags to maximize artwork discoverability."
        )

    @property
    def backstory(self) -> str:
        return (
            "You are a social media hashtag strategist who understands "
            "hashtag algorithms across Instagram, TikTok, and Twitter. "
            "You know which tags drive engagement and which are oversaturated."
        )

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Generate optimized hashtags.

        Expected context keys:
            - analysis: dict — artwork analysis results
            - seo: dict — SEO data
            - artwork_id: str — UUID of the artwork
            - artwork_title: str — optional title
        """
        start_time = time.monotonic()
        artwork_id = context.get("artwork_id", "unknown")

        logger.info("hashtag_agent_execute", artwork_id=artwork_id)

        try:
            registry = PromptRegistry()
            prompt_template = registry.get("hashtags", version="v1")

            analysis = context.get("analysis", {})
            seo = context.get("seo", {})

            rendered_prompt = prompt_template.render(
                artwork_title=context.get("artwork_title", ""),
                analysis=json.dumps(analysis) if analysis else "",
                seo=json.dumps(seo) if seo else "",
            )

            provider = GeminiProvider()
            result = await provider.generate_structured(
                prompt=rendered_prompt,
                output_schema=prompt_template.output_schema or {},
                system_prompt=prompt_template.system_prompt,
                temperature=0.5,
            )

            elapsed = (time.monotonic() - start_time) * 1000
            logger.info(
                "hashtag_agent_success",
                artwork_id=artwork_id,
                execution_time_ms=elapsed,
            )

            return AgentResult(
                success=True,
                data=result.data,
                agent_name=self.name,
                execution_time_ms=elapsed,
            )

        except Exception as exc:
            elapsed = (time.monotonic() - start_time) * 1000
            logger.error(
                "hashtag_agent_failed",
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
