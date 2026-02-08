"""Factory functions for creating Pydantic AI agents.

Provides create_pydantic_agent() for constructing Pydantic AI Agent instances
configured with ACPDeps and ACPToolset.
"""

from pydantic_ai import Agent

from .deps import ACPDeps
from .toolset import create_toolset


def create_pydantic_agent(model: str = "test") -> Agent[ACPDeps, str]:
    """Create a Pydantic AI agent configured for Punie.

    Args:
        model: Model name (default: "test" for TestModel, no LLM calls).
               Other options: "openai:gpt-4", "anthropic:claude-3-5-sonnet", etc.

    Returns:
        Pydantic AI Agent configured with ACPDeps and ACPToolset
    """
    return Agent[ACPDeps, str](
        model,
        deps_type=ACPDeps,
        system_prompt="You are Punie, an AI coding assistant.",
        toolsets=[create_toolset()],
    )
