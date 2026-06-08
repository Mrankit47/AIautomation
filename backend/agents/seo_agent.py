"""SEO generation agent — generates SEO-optimized metadata using Gemini."""

from __future__ import annotations

import json
import time
from typing import Any

from backend.agents.base import AgentResult, BaseAgent
from backend.core.logging import get_logger
from backend.prompts.registry import PromptRegistry
from backend.providers.gemini import GeminiProvider

logger = get_logger(__name__)


class SEOAgent(BaseAgent):
    """Generates SEO-optimized title, description, and keywords."""

    @property
    def name(self) -> str:
        return "seo_agent"

    @property
    def role(self) -> str:
        return "SEO Strategist"

    @property
    def goal(self) -> str:
        return (
            "Generate SEO-optimized titles, descriptions, and keywords "
            "that maximize artwork discoverability across search engines."
        )

    @property
    def backstory(self) -> str:
        return (
            "You are an SEO expert specializing in art and visual content. "
            "You know exactly how to craft metadata that ranks on Google "
            "Images, Pinterest, and art platforms."
        )

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Generate SEO metadata from artwork analysis.

        Expected context keys:
            - analysis: dict — artwork analysis results
            - artwork_id: str — UUID of the artwork
            - artwork_title: str — optional title
        """
        start_time = time.monotonic()
        artwork_id = context.get("artwork_id", "unknown")

        logger.info("seo_agent_execute", artwork_id=artwork_id)

        try:
            registry = PromptRegistry()
            prompt_template = registry.get("seo", version="v1")

            analysis = context.get("analysis", {})
            rendered_prompt = prompt_template.render(
                artwork_title=context.get("artwork_title", ""),
                analysis=json.dumps(analysis) if analysis else "",
            )

            provider = GeminiProvider()
            result = await provider.generate_structured(
                prompt=rendered_prompt,
                output_schema=prompt_template.output_schema or {},
                system_prompt=prompt_template.system_prompt,
                temperature=0.4,
            )

            elapsed = (time.monotonic() - start_time) * 1000
            logger.info(
                "seo_agent_success",
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
                "seo_agent_failed",
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
