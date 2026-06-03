"""Abstract base agent interface for CrewAI integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Structured result from an agent execution."""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    agent_name: str = ""
    execution_time_ms: float = 0.0


class BaseAgent(ABC):
    """Abstract base class for all AI agents in the platform.

    Each agent has a defined role and goal, and executes a specific
    task within the artwork processing pipeline.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent."""
        ...

    @property
    @abstractmethod
    def role(self) -> str:
        """The role this agent plays (e.g., 'Art Analyst')."""
        ...

    @property
    @abstractmethod
    def goal(self) -> str:
        """What this agent is trying to achieve."""
        ...

    @property
    def backstory(self) -> str:
        """Optional backstory for CrewAI agent personality."""
        return f"An AI agent specialized as a {self.role}."

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Execute the agent's task with the given context.

        Args:
            context: Dictionary containing task-specific data
                     (e.g., artwork analysis, image path, etc.).

        Returns:
            AgentResult with the execution outcome.
        """
        ...
