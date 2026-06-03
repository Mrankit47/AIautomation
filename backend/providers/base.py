"""Abstract AI provider interface.

Concrete implementations (Gemini, OpenAI, Anthropic) must implement all
methods.  The active provider is selected via configuration and injected
into services through the dependency injection layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AITextResult:
    """Result of a text generation call."""

    text: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIStructuredResult:
    """Result of a structured (JSON) generation call."""

    data: dict[str, Any]
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIImageAnalysisResult:
    """Result of an image analysis call."""

    description: str
    labels: list[str]
    metadata: dict[str, Any]
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)


class AIProvider(ABC):
    """Abstract interface for AI model providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of this provider (e.g., 'Gemini')."""
        ...

    @abstractmethod
    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        *,
        mime_type: str = "image/png",
    ) -> AIImageAnalysisResult:
        """Analyze an image and return structured analysis."""
        ...

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AITextResult:
        """Generate free-form text from a prompt."""
        ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> AIStructuredResult:
        """Generate structured JSON output conforming to the given schema."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the provider is reachable and the API key is valid."""
        ...
