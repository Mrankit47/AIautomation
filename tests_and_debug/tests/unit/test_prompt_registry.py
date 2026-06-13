"""Unit tests for PromptRegistry loading and rendering."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from backend.prompts.registry import PromptRegistry


@pytest.fixture
def temp_prompts_dir() -> Path:
    """Create a temporary directory with prompt files for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create category folder and yaml template
        analysis_dir = tmp_path / "artwork_analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)

        prompt_data = {
            "name": "artwork_analysis",
            "version": "v1",
            "description": "Test analysis prompt",
            "system_prompt": "You are a test analyst.",
            "user_prompt_template": "Analyze this title: {{ title }}",
            "metadata": {"author": "tester"},
        }

        with open(analysis_dir / "v1.yaml", "w", encoding="utf-8") as f:
            yaml.dump(prompt_data, f)

        yield tmp_path


def test_prompt_registry_load_and_get(temp_prompts_dir: Path) -> None:
    """Test that prompt registry correctly scans, loads, and retrieves prompts."""
    registry = PromptRegistry(prompts_dir=str(temp_prompts_dir), default_version="v1")
    prompt = registry.get("artwork_analysis", version="v1")

    assert prompt.name == "artwork_analysis"
    assert prompt.version == "v1"
    assert prompt.system_prompt == "You are a test analyst."


def test_prompt_registry_rendering(temp_prompts_dir: Path) -> None:
    """Test template rendering with variables."""
    registry = PromptRegistry(prompts_dir=str(temp_prompts_dir), default_version="v1")
    prompt = registry.get("artwork_analysis", version="v1")

    rendered = prompt.render(title="My Masterpiece")
    assert rendered == "Analyze this title: My Masterpiece"


def test_prompt_registry_missing_prompt(temp_prompts_dir: Path) -> None:
    """Test that requesting a missing prompt raises KeyError."""
    registry = PromptRegistry(prompts_dir=str(temp_prompts_dir), default_version="v1")

    with pytest.raises(KeyError):
        registry.get("seo", version="v1")
