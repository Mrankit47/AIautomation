"""Groq AI provider implementation.

Resilient provider with exponential backoff, JSON mode support,
and structured parsing via the official groq SDK.
"""

from __future__ import annotations

import json
import time
import asyncio
import traceback
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
        from groq import APIStatusError
        last_exc = None
        for attempt in range(self._max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except APIStatusError as exc:
                last_exc = exc
                status_code = getattr(exc, "status_code", None)
                if status_code and status_code in (400, 401, 403, 404) and status_code != 429:
                    logger.error(
                        "groq_non_transient_error",
                        attempt=attempt + 1,
                        code=status_code,
                        error=str(exc),
                    )
                    raise
                
                if attempt < self._max_retries:
                    wait = min(2 ** attempt, 30)
                    logger.warning(
                        "groq_retry",
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
                        "groq_retry",
                        attempt=attempt + 1,
                        max_retries=self._max_retries,
                        wait_seconds=wait,
                        error=str(exc),
                    )
                    await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        *,
        mime_type: str = "image/png",
    ) -> AIImageAnalysisResult:
        """Analyze image via Groq, with fallback to text-only generation if model has no vision."""
        import base64
        start_time = time.perf_counter()
        
        is_vision_model = "vision" in self._model_name.lower()
        parsed = {}
        response = None
        
        # Output schema for the artwork analysis structured result
        output_schema = {
            "type": "object",
            "required": ["style", "mood", "primary_colors", "objects", "category"],
            "properties": {
                "style": {"type": "string"},
                "medium": {"type": "string"},
                "mood": {"type": "string"},
                "emotional_tone": {"type": "string"},
                "primary_colors": {"type": "array", "items": {"type": "string"}},
                "objects": {"type": "array", "items": {"type": "string"}},
                "scene": {"type": "string"},
                "category": {
                    "type": "string",
                    "enum": ["digital_art", "traditional_art", "photography", "anime", "illustration", "mixed_media"]
                },
                "composition": {"type": "string"},
                "subjects": {"type": "array", "items": {"type": "string"}},
                "description": {"type": "string"}
            }
        }

        try:
            if is_vision_model:
                logger.info(
                    "groq_analyze_image_vision",
                    model=self._model_name,
                    image_size=len(image_data),
                    mime_type=mime_type,
                )
                base64_image = base64.b64encode(image_data).decode("utf-8")
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
                
                async def _call():
                    return await self._client.chat.completions.create(
                        model=self._model_name,
                        messages=messages,
                        temperature=0.3,
                        response_format={"type": "json_object"},
                    )
                
                response_obj = await self._retry_with_backoff(_call)
                response = response_obj.model_dump() if hasattr(response_obj, "model_dump") else response_obj
                text = response_obj.choices[0].message.content or ""
                parsed = json.loads(text.strip())
            else:
                logger.info(
                    "groq_analyze_image_text_fallback",
                    model=self._model_name,
                    reason="Model is not vision-capable",
                )
                result = await self.generate_structured(
                    prompt=prompt + "\n\nNote: As a text fallback, analyze the artwork details based on the title, description and contextual info.",
                    output_schema=output_schema,
                    temperature=0.3
                )
                parsed = result.data
                response = result.raw_response

            usage = {}
            if response and "usage" in response:
                usage = response["usage"]

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "groq_analyze_image_success",
                model=self._model_name,
                execution_time_ms=elapsed_ms,
            )

            return AIImageAnalysisResult(
                description=parsed.get("description", "A beautiful artwork description fallback."),
                labels=parsed.get("subjects", parsed.get("objects", ["artwork"])),
                metadata=parsed,
                model=self._model_name,
                usage=usage,
                raw_response=response,
            )

        except Exception as exc:
            if is_vision_model:
                logger.warning(
                    "groq_vision_failed_trying_text_fallback",
                    model=self._model_name,
                    error=str(exc),
                )
                try:
                    result = await self.generate_structured(
                        prompt=prompt + "\n\nNote: Analyze the artwork based on textual metadata.",
                        output_schema=output_schema,
                        temperature=0.3
                    )
                    parsed = result.data
                    response = result.raw_response
                    
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    return AIImageAnalysisResult(
                        description=parsed.get("description", "A beautiful artwork description fallback."),
                        labels=parsed.get("subjects", parsed.get("objects", ["artwork"])),
                        metadata=parsed,
                        model=self._model_name,
                        usage=result.usage,
                        raw_response=response,
                    )
                except Exception as inner_exc:
                    raise AIProviderException(
                        detail=f"Groq fallback image analysis failed: {inner_exc}",
                        context={"model": self._model_name},
                    ) from inner_exc

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "groq_analyze_image_failed",
                model=self._model_name,
                error=str(exc),
                execution_time_ms=elapsed_ms,
            )
            raise AIProviderException(
                detail=f"Groq image analysis failed: {exc}",
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
