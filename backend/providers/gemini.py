"""Google Gemini AI provider implementation.

Production-ready provider with retry logic, timeout support,
and structured JSON output via the google-genai SDK.
"""

from __future__ import annotations

import json
import time
import asyncio
import traceback
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError

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
    """Gemini API integration using the google-genai SDK."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model_name = settings.gemini.model
        self._max_retries = settings.gemini.max_retries
        self._timeout = settings.gemini.timeout

        api_key = settings.gemini.api_key.get_secret_value()
        if not api_key or api_key == "mock-api-key":
            logger.warning("gemini_api_key_missing_or_mock")
            api_key = api_key or "mock-key"

        self._client = genai.Client(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "Gemini"

    async def _retry_with_backoff(self, func, *args, **kwargs) -> Any:
        """Execute an async function with exponential backoff retry."""
        last_exc = None
        for attempt in range(self._max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except APIError as exc:
                last_exc = exc
                status_code = getattr(exc, "code", None)
                # Client errors (4xx) except 429 are typically non-transient
                if status_code and status_code in (400, 401, 403, 404) and status_code != 429:
                    logger.error(
                        "gemini_non_transient_error",
                        attempt=attempt + 1,
                        code=status_code,
                        error=str(exc),
                    )
                    raise
                
                if attempt < self._max_retries:
                    wait = min(2 ** attempt, 30)
                    logger.warning(
                        "gemini_retry",
                        attempt=attempt + 1,
                        max_retries=self._max_retries,
                        wait_seconds=wait,
                        error=str(exc),
                    )
                    await asyncio.sleep(wait)
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
                    await asyncio.sleep(wait)
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
        start_time = time.perf_counter()
        try:
            logger.info(
                "gemini_analyze_image",
                model=self._model_name,
                image_size=len(image_data),
                mime_type=mime_type,
            )

            image_part = types.Part.from_bytes(data=image_data, mime_type=mime_type)

            config = types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=4096,
                response_mime_type="application/json",
                http_options=types.HttpOptions(timeout=self._timeout),
            )

            async def _call():
                return await self._client.aio.models.generate_content(
                    model=self._model_name,
                    contents=[prompt, image_part],
                    config=config,
                )

            response = await self._retry_with_backoff(_call)
            response_text = response.text
            parsed = self._parse_json_from_text(response_text)

            usage = {}
            if response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                    "total_tokens": response.usage_metadata.total_token_count or 0,
                }

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "gemini_analyze_image_success",
                model=self._model_name,
                usage=usage,
                execution_time_ms=elapsed_ms,
            )

            return AIImageAnalysisResult(
                description=parsed.get("description", ""),
                labels=parsed.get("subjects", parsed.get("objects", [])),
                metadata=parsed,
                model=self._model_name,
                usage=usage,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else {},
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            stack_trace = traceback.format_exc()
            http_status = getattr(exc, "code", None)
            response_body = getattr(exc, "message", None)
            logger.error(
                "gemini_analyze_image_failed",
                model=self._model_name,
                error=str(exc),
                stack_trace=stack_trace,
                http_status=http_status,
                response_body=response_body,
                execution_time_ms=elapsed_ms,
            )
            raise AIProviderException(
                detail=f"Gemini image analysis failed: {exc}",
                context={
                    "model": self._model_name,
                    "http_status": http_status,
                    "response_body": response_body,
                },
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
        start_time = time.perf_counter()
        try:
            logger.info(
                "gemini_generate_text",
                model=self._model_name,
                prompt_length=len(prompt),
            )

            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_prompt,
                http_options=types.HttpOptions(timeout=self._timeout),
            )

            async def _call():
                return await self._client.aio.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                    config=config,
                )

            response = await self._retry_with_backoff(_call)

            usage = {}
            if response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                    "total_tokens": response.usage_metadata.total_token_count or 0,
                }

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "gemini_generate_text_success",
                model=self._model_name,
                usage=usage,
                execution_time_ms=elapsed_ms,
            )

            return AITextResult(
                text=response.text,
                model=self._model_name,
                usage=usage,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else {},
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            stack_trace = traceback.format_exc()
            http_status = getattr(exc, "code", None)
            response_body = getattr(exc, "message", None)
            logger.error(
                "gemini_generate_text_failed",
                model=self._model_name,
                error=str(exc),
                stack_trace=stack_trace,
                http_status=http_status,
                response_body=response_body,
                execution_time_ms=elapsed_ms,
            )
            raise AIProviderException(
                detail=f"Gemini text generation failed: {exc}",
                context={
                    "model": self._model_name,
                    "http_status": http_status,
                    "response_body": response_body,
                },
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
        start_time = time.perf_counter()
        try:
            logger.info(
                "gemini_generate_structured",
                model=self._model_name,
                prompt_length=len(prompt),
            )

            schema_str = json.dumps(output_schema, indent=2)
            full_prompt = (
                f"{prompt}\n\n"
                f"Respond with valid JSON matching this schema:\n{schema_str}"
            )

            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=4096,
                response_mime_type="application/json",
                system_instruction=system_prompt,
                http_options=types.HttpOptions(timeout=self._timeout),
            )

            async def _call():
                return await self._client.aio.models.generate_content(
                    model=self._model_name,
                    contents=full_prompt,
                    config=config,
                )

            response = await self._retry_with_backoff(_call)
            parsed = self._parse_json_from_text(response.text)

            usage = {}
            if response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                    "total_tokens": response.usage_metadata.total_token_count or 0,
                }

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "gemini_generate_structured_success",
                model=self._model_name,
                usage=usage,
                execution_time_ms=elapsed_ms,
            )

            return AIStructuredResult(
                data=parsed,
                model=self._model_name,
                usage=usage,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else {},
            )

        except json.JSONDecodeError as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            stack_trace = traceback.format_exc()
            logger.error(
                "gemini_json_parse_failed",
                model=self._model_name,
                error=str(exc),
                stack_trace=stack_trace,
                execution_time_ms=elapsed_ms,
            )
            raise AIProviderException(
                detail=f"Gemini returned invalid JSON: {exc}",
                context={"model": self._model_name},
            ) from exc
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            stack_trace = traceback.format_exc()
            http_status = getattr(exc, "code", None)
            response_body = getattr(exc, "message", None)
            logger.error(
                "gemini_generate_structured_failed",
                model=self._model_name,
                error=str(exc),
                stack_trace=stack_trace,
                http_status=http_status,
                response_body=response_body,
                execution_time_ms=elapsed_ms,
            )
            raise AIProviderException(
                detail=f"Gemini structured generation failed: {exc}",
                context={
                    "model": self._model_name,
                    "http_status": http_status,
                    "response_body": response_body,
                },
            ) from exc

    async def health_check(self) -> bool:
        """Verify the Gemini API is reachable."""
        try:
            await self._client.aio.models.list()
            return True
        except Exception as exc:
            logger.warning("gemini_health_check_failed", error=str(exc))
            return False
