"""Google Gemini AI provider implementation.

Production-ready provider with retry logic, timeout support,
and structured JSON output via the google-generativeai SDK.
"""

from __future__ import annotations

import json
import time
from typing import Any

import google.generativeai as genai

from backend.config.settings import get_settings
from backend.core.exceptions import AIProviderException
from backend.core.logging import get_logger
from backend.providers.base import (
    AIImageAnalysisResult,
    AIProvider,
    AIStructuredResult,
    AITextResult,
)

logger = get_logger(__name__)


class GeminiProvider(AIProvider):
    """Gemini API integration using the google-generativeai SDK."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model_name = settings.gemini.model
        self._max_retries = settings.gemini.max_retries
        self._timeout = settings.gemini.timeout

        api_key = settings.gemini.api_key.get_secret_value()
        if not api_key or api_key == "mock-api-key":
            logger.warning("gemini_api_key_missing_or_mock")
        if api_key:
            genai.configure(api_key=api_key)

        self._model = genai.GenerativeModel(self._model_name)

    @property
    def provider_name(self) -> str:
        return "Gemini"

    def _retry_with_backoff(self, func, *args, **kwargs) -> Any:
        """Execute a function with exponential backoff retry."""
        last_exc = None
        for attempt in range(self._max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    wait = min(2 ** attempt, 30)
                    logger.warning(
                        "gemini_retry",
                        attempt=attempt + 1,
                        max_retries=self._max_retries,
                        wait_seconds=wait,
                        error=str(exc),
                    )
                    time.sleep(wait)
        raise last_exc  # type: ignore[misc]

    def _parse_json_from_text(self, text: str) -> dict[str, Any]:
        """Extract JSON from model response text, handling markdown fences."""
        cleaned = text.strip()
        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first line (```json or ```) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()
        return json.loads(cleaned)

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        *,
        mime_type: str = "image/png",
    ) -> AIImageAnalysisResult:
        """Analyze an artwork image via Gemini vision capabilities."""
        try:
            logger.info(
                "gemini_analyze_image",
                model=self._model_name,
                image_size=len(image_data),
                mime_type=mime_type,
            )

            image_part = {
                "mime_type": mime_type,
                "data": image_data,
            }

            generation_config = genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=4096,
                response_mime_type="application/json",
            )

            response = await self._model.generate_content_async(
                [prompt, image_part],
                generation_config=generation_config,
                request_options={"timeout": self._timeout},
            )

            response_text = response.text
            parsed = self._parse_json_from_text(response_text)

            usage = {}
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = {
                    "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                    "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
                }

            logger.info(
                "gemini_analyze_image_success",
                model=self._model_name,
                usage=usage,
            )

            return AIImageAnalysisResult(
                description=parsed.get("description", ""),
                labels=parsed.get("subjects", parsed.get("objects", [])),
                metadata=parsed,
                model=self._model_name,
                usage=usage,
            )

        except Exception as exc:
            logger.error(
                "gemini_analyze_image_failed",
                model=self._model_name,
                error=str(exc),
            )
            raise AIProviderException(
                detail=f"Gemini image analysis failed: {exc}",
                context={"model": self._model_name},
            ) from exc

    async def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AITextResult:
        """Generate text via Gemini."""
        try:
            logger.info(
                "gemini_generate_text",
                model=self._model_name,
                prompt_length=len(prompt),
            )

            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Build content parts
            contents = []
            if system_prompt:
                contents.append(f"System: {system_prompt}\n\n")
            contents.append(prompt)
            full_prompt = "".join(contents)

            response = await self._model.generate_content_async(
                full_prompt,
                generation_config=generation_config,
                request_options={"timeout": self._timeout},
            )

            usage = {}
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = {
                    "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                    "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
                }

            logger.info(
                "gemini_generate_text_success",
                model=self._model_name,
                usage=usage,
            )

            return AITextResult(
                text=response.text,
                model=self._model_name,
                usage=usage,
            )

        except Exception as exc:
            logger.error(
                "gemini_generate_text_failed",
                model=self._model_name,
                error=str(exc),
            )
            raise AIProviderException(
                detail=f"Gemini text generation failed: {exc}",
                context={"model": self._model_name},
            ) from exc

    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> AIStructuredResult:
        """Generate structured JSON output via Gemini."""
        try:
            logger.info(
                "gemini_generate_structured",
                model=self._model_name,
                prompt_length=len(prompt),
            )

            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=4096,
                response_mime_type="application/json",
            )

            # Build full prompt with schema instructions
            schema_str = json.dumps(output_schema, indent=2)
            full_prompt_parts = []
            if system_prompt:
                full_prompt_parts.append(f"System: {system_prompt}\n\n")
            full_prompt_parts.append(prompt)
            full_prompt_parts.append(
                f"\n\nRespond with valid JSON matching this schema:\n{schema_str}"
            )
            full_prompt = "".join(full_prompt_parts)

            response = await self._model.generate_content_async(
                full_prompt,
                generation_config=generation_config,
                request_options={"timeout": self._timeout},
            )

            parsed = self._parse_json_from_text(response.text)

            usage = {}
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = {
                    "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                    "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
                }

            logger.info(
                "gemini_generate_structured_success",
                model=self._model_name,
                usage=usage,
            )

            return AIStructuredResult(
                data=parsed,
                model=self._model_name,
                usage=usage,
            )

        except json.JSONDecodeError as exc:
            logger.error(
                "gemini_json_parse_failed",
                model=self._model_name,
                error=str(exc),
            )
            raise AIProviderException(
                detail=f"Gemini returned invalid JSON: {exc}",
                context={"model": self._model_name},
            ) from exc
        except Exception as exc:
            logger.error(
                "gemini_generate_structured_failed",
                model=self._model_name,
                error=str(exc),
            )
            raise AIProviderException(
                detail=f"Gemini structured generation failed: {exc}",
                context={"model": self._model_name},
            ) from exc

    async def health_check(self) -> bool:
        """Verify the Gemini API is reachable."""
        try:
            models = genai.list_models()
            return any(True for _ in models)
        except Exception as exc:
            logger.warning("gemini_health_check_failed", error=str(exc))
            return False
