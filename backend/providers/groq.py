"""Groq AI provider implementation.

Resilient provider with exponential backoff, JSON mode support,
and structured parsing via the official groq SDK.
"""

from __future__ import annotations

import json
import time
from typing import Any

from groq import AsyncGroq
from groq.types.chat import ChatCompletion

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


class GroqProvider(AIProvider):
    """Groq API integration using the async groq SDK."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model_name = settings.groq_model
        # We allow fallback to settings.gemini.max_retries/timeout if we want uniformity
        self._max_retries = getattr(settings.gemini, "max_retries", 3)
        self._timeout = getattr(settings.gemini, "timeout", 60)

        api_key = settings.groq_api_key.get_secret_value()
        if not api_key or api_key == "mock-api-key":
            logger.warning("groq_api_key_missing_or_mock")

        self._client = AsyncGroq(api_key=api_key, timeout=self._timeout)

    @property
    def provider_name(self) -> str:
        return "Groq"

    async def _retry_with_backoff(self, func, *args, **kwargs) -> Any:
        """Execute an async function with exponential backoff retry."""
        last_exc = None
        for attempt in range(self._max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    wait = min(2 ** attempt, 30)
                    logger.warning(
                        "groq_retry",
                        attempt=attempt + 1,
                        max_retries=self._max_retries,
                        wait_seconds=wait,
                        error=str(exc),
                    )
                    time.sleep(wait)
        raise last_exc  # type: ignore[misc]

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        *,
        mime_type: str = "image/png",
    ) -> AIImageAnalysisResult:
        """Analyze image is not supported by Groq in this architecture."""
        logger.error("groq_analyze_image_unsupported")
        raise NotImplementedError("Groq provider does not support image analysis vision tasks.")

    async def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AITextResult:
        """Generate free-form text via Groq."""
        start_time = time.perf_counter()
        try:
            logger.info(
                "groq_generate_text",
                model=self._model_name,
                prompt_length=len(prompt),
            )

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            async def _call():
                return await self._client.chat.completions.create(
                    model=self._model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            response: ChatCompletion = await self._retry_with_backoff(_call)
            text = response.choices[0].message.content or ""

            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "groq_generate_text_success",
                provider="groq",
                model=self._model_name,
                execution_time_ms=elapsed_ms,
                token_usage=usage,
            )

            return AITextResult(
                text=text,
                model=self._model_name,
                usage=usage,
                raw_response=response.model_dump(),
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "groq_generate_text_failed",
                provider="groq",
                model=self._model_name,
                error=str(exc),
                execution_time_ms=elapsed_ms,
            )
            raise AIProviderException(
                detail=f"Groq text generation failed: {exc}",
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
        """Generate structured JSON output via Groq using JSON Mode."""
        start_time = time.perf_counter()
        try:
            logger.info(
                "groq_generate_structured",
                model=self._model_name,
                prompt_length=len(prompt),
            )

            schema_str = json.dumps(output_schema, indent=2)
            full_prompt = (
                f"{prompt}\n\n"
                f"You MUST respond ONLY with a raw JSON object matching this schema:\n"
                f"{schema_str}\n"
                f"Do not wrap your response in markdown code blocks. Return direct valid JSON."
            )

            messages = []
            sys_msg = system_prompt or "You are a helpful assistant that always outputs valid JSON."
            if "JSON" not in sys_msg:
                sys_msg += " You must respond ONLY with a valid JSON object."
            messages.append({"role": "system", "content": sys_msg})
            messages.append({"role": "user", "content": full_prompt})

            async def _call():
                return await self._client.chat.completions.create(
                    model=self._model_name,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )

            response: ChatCompletion = await self._retry_with_backoff(_call)
            text = response.choices[0].message.content or ""
            parsed = json.loads(text.strip())

            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "groq_generate_structured_success",
                provider="groq",
                model=self._model_name,
                execution_time_ms=elapsed_ms,
                token_usage=usage,
            )

            return AIStructuredResult(
                data=parsed,
                model=self._model_name,
                usage=usage,
                raw_response=response.model_dump(),
            )

        except json.JSONDecodeError as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "groq_json_parse_failed",
                provider="groq",
                model=self._model_name,
                error=str(exc),
                execution_time_ms=elapsed_ms,
            )
            raise AIProviderException(
                detail=f"Groq returned invalid JSON: {exc}",
                context={"model": self._model_name},
            ) from exc
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "groq_generate_structured_failed",
                provider="groq",
                model=self._model_name,
                error=str(exc),
                execution_time_ms=elapsed_ms,
            )
            raise AIProviderException(
                detail=f"Groq structured generation failed: {exc}",
                context={"model": self._model_name},
            ) from exc

    async def health_check(self) -> bool:
        """Verify the Groq API is reachable."""
        try:
            # Execute a tiny completion query to verify API key and connectivity
            await self._client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception as exc:
            logger.warning("groq_health_check_failed", error=str(exc))
            return False
