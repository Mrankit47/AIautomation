"""Prompt registry — discovers, loads, caches, and resolves prompt templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.prompts.base import PromptTemplate

logger = get_logger(__name__)


class PromptRegistry:
    """Discovers and caches prompt templates from the filesystem.

    Directory structure expected::

        prompts_dir/
        ├── artwork_analysis/
        │   ├── v1.yaml
        │   └── v2.yaml
        ├── seo/
        │   └── v1.yaml
        └── captions/
            └── v1.yaml

    Usage::

        registry = PromptRegistry()
        prompt = registry.get("artwork_analysis", version="v1")
        rendered = prompt.render(artwork_title="Sunset Over Hills")
    """

    def __init__(
        self,
        prompts_dir: str | None = None,
        default_version: str | None = None,
    ) -> None:
        settings = get_settings()
        self._prompts_dir = Path(prompts_dir or settings.prompts.directory).resolve()
        self._default_version = default_version or settings.prompts.default_version
        self._cache: dict[str, PromptTemplate] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Scan the prompts directory and load all YAML templates."""
        if not self._prompts_dir.exists():
            logger.warning("prompts_dir_not_found", path=str(self._prompts_dir))
            return

        for category_dir in self._prompts_dir.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith(("_", ".")):
                continue
            for yaml_file in category_dir.glob("*.yaml"):
                self._load_template(category_dir.name, yaml_file)

        logger.info(
            "prompts_loaded",
            count=len(self._cache),
            categories=list({k.split("/")[0] for k in self._cache}),
        )

    def _load_template(self, category: str, yaml_path: Path) -> None:
        """Parse a single YAML prompt file and cache it."""
        try:
            with open(yaml_path, encoding="utf-8") as f:
                data: dict[str, Any] = yaml.safe_load(f)

            if not data:
                logger.warning("empty_prompt_file", path=str(yaml_path))
                return

            version = data.get("version", yaml_path.stem)
            template = PromptTemplate(
                name=data.get("name", category),
                version=version,
                description=data.get("description", ""),
                system_prompt=data.get("system_prompt", ""),
                user_prompt_template=data.get("user_prompt_template", ""),
                output_schema=data.get("output_schema"),
                metadata=data.get("metadata", {}),
            )
            cache_key = f"{category}/{version}"
            self._cache[cache_key] = template
            logger.debug("prompt_loaded", key=cache_key)

        except (yaml.YAMLError, KeyError) as exc:
            logger.error(
                "prompt_load_failed",
                path=str(yaml_path),
                error=str(exc),
            )

    def get(
        self,
        category: str,
        version: str | None = None,
    ) -> PromptTemplate:
        """Retrieve a prompt template by category and version.

        Args:
            category: Prompt category (e.g., 'artwork_analysis', 'seo').
            version: Version string (e.g., 'v1'). Defaults to the configured default.

        Returns:
            The matching PromptTemplate.

        Raises:
            KeyError: If the prompt is not found.
        """
        ver = version or self._default_version
        cache_key = f"{category}/{ver}"
        if cache_key not in self._cache:
            msg = (
                f"Prompt '{cache_key}' not found. "
                f"Available: {list(self._cache.keys())}"
            )
            raise KeyError(msg)
        return self._cache[cache_key]

    def list_categories(self) -> list[str]:
        """Return all loaded prompt categories."""
        return sorted({k.split("/")[0] for k in self._cache})

    def list_versions(self, category: str) -> list[str]:
        """Return all available versions for a prompt category."""
        prefix = f"{category}/"
        return sorted(
            k.removeprefix(prefix) for k in self._cache if k.startswith(prefix)
        )

    def reload(self) -> None:
        """Hot-reload all prompts from disk (e.g., after editing YAML)."""
        self._cache.clear()
        self._load_all()
        logger.info("prompts_reloaded", count=len(self._cache))
