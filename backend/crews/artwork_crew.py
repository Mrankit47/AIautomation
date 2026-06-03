"""Artwork processing crew — orchestrates analysis, metadata, and content agents."""

from __future__ import annotations

import time
from typing import Any

from backend.agents.artwork_analyzer import ArtworkAnalyzerAgent
from backend.agents.base import BaseAgent
from backend.agents.content_generator import ContentGeneratorAgent
from backend.agents.metadata_generator import MetadataGeneratorAgent
from backend.core.logging import get_logger
from backend.crews.base import BaseCrew, CrewResult

logger = get_logger(__name__)


class ArtworkProcessingCrew(BaseCrew):
    """Crew that processes an artwork through analysis, metadata, and content generation."""

    def __init__(self) -> None:
        self._analyzer = ArtworkAnalyzerAgent()
        self._metadata_gen = MetadataGeneratorAgent()
        self._content_gen = ContentGeneratorAgent()

    @property
    def name(self) -> str:
        return "artwork_processing"

    @property
    def description(self) -> str:
        return (
            "Processes an artwork image through analysis, metadata generation, "
            "and content generation (SEO, captions, hashtags)."
        )

    def get_agents(self) -> list[BaseAgent]:
        return [self._analyzer, self._metadata_gen, self._content_gen]

    async def kickoff(self, inputs: dict[str, Any]) -> CrewResult:
        """Execute the artwork processing pipeline.

        Expected inputs:
            - artwork_id: str
            - image_path: str

        Note: Full implementation deferred to AI prompts phase.
              This stub demonstrates the crew orchestration pattern.
        """
        start = time.perf_counter()
        errors: list[str] = []
        outputs: dict[str, Any] = {}

        logger.info(
            "crew_kickoff",
            crew=self.name,
            artwork_id=inputs.get("artwork_id"),
        )

        # Step 1: Analyze artwork
        analysis_result = await self._analyzer.execute(inputs)
        if not analysis_result.success:
            errors.append(f"Analysis failed: {analysis_result.error}")
        else:
            outputs["analysis"] = analysis_result.data
            inputs["analysis"] = analysis_result.data

        # Step 2: Generate metadata
        metadata_result = await self._metadata_gen.execute(inputs)
        if not metadata_result.success:
            errors.append(f"Metadata generation failed: {metadata_result.error}")
        else:
            outputs["metadata"] = metadata_result.data
            inputs["metadata"] = metadata_result.data

        # Step 3: Generate content
        content_result = await self._content_gen.execute(inputs)
        if not content_result.success:
            errors.append(f"Content generation failed: {content_result.error}")
        else:
            outputs["content"] = content_result.data

        elapsed = (time.perf_counter() - start) * 1000

        logger.info(
            "crew_completed",
            crew=self.name,
            success=len(errors) == 0,
            duration_ms=round(elapsed, 2),
        )

        return CrewResult(
            success=len(errors) == 0,
            outputs=outputs,
            errors=errors,
            crew_name=self.name,
            execution_time_ms=elapsed,
        )
