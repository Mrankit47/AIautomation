"""Reel script generation agent — creates short-form video scripts using Gemini."""

from __future__ import annotations

import json
import time
from typing import Any

from backend.agents.base import AgentResult, BaseAgent
from backend.core.logging import get_logger
from backend.prompts.registry import PromptRegistry
from backend.providers.factory import get_provider

logger = get_logger(__name__)


class ReelScriptAgent(BaseAgent):
    """Generates short-form video scripts for Reels/Shorts/TikTok."""

    @property
    def name(self) -> str:
        return "reel_script_agent"

    @property
    def role(self) -> str:
        return "Video Script Writer"

    @property
    def goal(self) -> str:
        return (
            "Generate viral short-form video scripts with hooks, narration, "
            "and calls-to-action optimized for Instagram Reels and TikTok."
        )

    @property
    def backstory(self) -> str:
        return (
            "You are a viral content creator who specializes in art content. "
            "You know how to write scripts that hook viewers in the first "
            "3 seconds and keep them watching until the end."
        )

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Generate a reel/short video script.

        Expected context keys:
            - analysis: dict — artwork analysis results
            - caption: str — generated caption
            - artwork_id: str — UUID of the artwork
            - artwork_title: str — optional title
        """
        start_time = time.monotonic()
        artwork_id = context.get("artwork_id", "unknown")

        logger.info("reel_script_agent_execute", artwork_id=artwork_id)

        try:
            registry = PromptRegistry()
            prompt_template = registry.get("reel_script", version="v1")

            analysis = context.get("analysis", {})
            rendered_prompt = prompt_template.render(
                artwork_title=context.get("artwork_title", ""),
                analysis=json.dumps(analysis) if analysis else "",
                caption=context.get("caption", ""),
            )

            provider = get_provider()
            result = await provider.generate_structured(
                prompt=rendered_prompt,
                output_schema=prompt_template.output_schema or {},
                system_prompt=prompt_template.system_prompt,
                temperature=0.7,
            )

            elapsed = (time.monotonic() - start_time) * 1000
            logger.info(
                "reel_script_agent_success",
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
                "reel_script_agent_failed",
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
