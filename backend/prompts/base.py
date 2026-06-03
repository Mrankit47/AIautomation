"""Versioned prompt template system.

Prompts are stored as YAML files on disk and rendered with Jinja2.
This allows non-engineers to edit prompts independently of code,
and supports A/B testing via version selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jinja2 import BaseLoader, Environment, TemplateSyntaxError


@dataclass
class PromptTemplate:
    """A single versioned prompt template loaded from YAML."""

    name: str
    version: str
    description: str
    system_prompt: str
    user_prompt_template: str
    output_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Jinja2 environment for rendering (created lazily)
    _env: Environment = field(default_factory=lambda: Environment(loader=BaseLoader()), repr=False)

    def render(self, **kwargs: Any) -> str:
        """Render the user prompt template with the given variables.

        Args:
            **kwargs: Template variables to inject.

        Returns:
            The rendered prompt string.

        Raises:
            ValueError: If the template contains syntax errors.
        """
        try:
            template = self._env.from_string(self.user_prompt_template)
            return template.render(**kwargs)
        except TemplateSyntaxError as exc:
            msg = f"Prompt template '{self.name}' v{self.version} has syntax error: {exc}"
            raise ValueError(msg) from exc

    def render_system(self, **kwargs: Any) -> str:
        """Render the system prompt template (if it contains variables)."""
        try:
            template = self._env.from_string(self.system_prompt)
            return template.render(**kwargs)
        except TemplateSyntaxError as exc:
            msg = f"System prompt '{self.name}' v{self.version} has syntax error: {exc}"
            raise ValueError(msg) from exc

    @property
    def full_name(self) -> str:
        """Return the fully qualified name (e.g. 'artwork_analysis/v1')."""
        return f"{self.name}/{self.version}"
