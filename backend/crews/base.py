"""Abstract base crew interface for CrewAI integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from backend.agents.base import BaseAgent


@dataclass
class CrewResult:
    """Structured result from a crew execution."""

    success: bool
    outputs: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    crew_name: str = ""
    execution_time_ms: float = 0.0


class BaseCrew(ABC):
    """Abstract base class for multi-agent crews."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this crew."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this crew accomplishes."""
        ...

    @abstractmethod
    def get_agents(self) -> list[BaseAgent]:
        """Return the ordered list of agents in this crew."""
        ...

    @abstractmethod
    async def kickoff(self, inputs: dict[str, Any]) -> CrewResult:
        """Execute the crew's workflow with the given inputs.

        Args:
            inputs: Data to be processed by the crew (e.g., artwork info).

        Returns:
            CrewResult with aggregated outputs from all agents.
        """
        ...
