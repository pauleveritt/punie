"""Factory functions for creating Pydantic AI agents.

Provides create_pydantic_agent() for constructing Pydantic AI Agent instances
configured with ACPDeps and toolset (static or dynamic).
"""

import logging

from pydantic_ai import Agent, FunctionToolset, ModelRetry, RunContext
from pydantic_ai.models import KnownModelName, Model, ModelSettings
from pydantic_ai.models.test import TestModel

from punie.agent.deps import ACPDeps
from punie.agent.toolset import create_toolset

logger = logging.getLogger(__name__)

PUNIE_INSTRUCTIONS = """\
You are Punie, an AI coding assistant that works inside PyCharm.

You have access to the user's workspace through the IDE. You can read files,
write files (with permission), and run commands (with permission) in the
user's project.

Guidelines:
- Read files before modifying them to understand context.
- Explain what you plan to do before making changes.
- When writing files, provide complete file contents.
- When running commands, prefer standard tools (pytest, ruff, git).
- If a tool call fails, explain the error and suggest alternatives.
- Keep responses focused and actionable.
"""


def _create_enhanced_test_model() -> TestModel:
    """Create a TestModel with realistic responses for testing.

    Returns a TestModel that provides helpful, realistic responses instead of just "a".
    Does NOT call tools (would cause deadlock with ACP request-response cycle).
    """
    logger.info("Creating enhanced test model with realistic responses (no tool calls)")
    return TestModel(
        custom_output_text="I understand the request. Let me help with that task.",
        call_tools=[],  # Don't call tools - would cause deadlock in ACP request-response
    )


def create_pydantic_agent(
    model: KnownModelName | Model = "test",
    toolset: FunctionToolset[ACPDeps] | None = None,
) -> Agent[ACPDeps, str]:
    """Create a Pydantic AI agent configured for Punie.

    Args:
        model: Model name (default: "test" for enhanced TestModel, no LLM calls).
               Other options: "openai:gpt-4", "anthropic:claude-3-5-sonnet", etc.
               Can also pass a Model instance directly.
        toolset: Optional toolset to use. If None, uses create_toolset() (all 7 static tools).
                 For dynamic discovery, pass create_toolset_from_catalog() or
                 create_toolset_from_capabilities() result.

    Returns:
        Pydantic AI Agent configured with ACPDeps and toolset
    """
    if toolset is None:
        toolset = create_toolset()

    # Use enhanced test model if "test" string is passed
    if model == "test":
        logger.info("Using enhanced test model for better debugging")
        model = _create_enhanced_test_model()

    agent = Agent[ACPDeps, str](
        model,
        deps_type=ACPDeps,
        instructions=PUNIE_INSTRUCTIONS,
        model_settings=ModelSettings(temperature=0.0, max_tokens=4096),
        retries=3,
        output_retries=2,
        toolsets=[toolset],
    )

    @agent.output_validator
    def validate_response(ctx: RunContext[ACPDeps], output: str) -> str:
        if not output.strip():
            raise ModelRetry("Response was empty, please provide a substantive answer.")
        return output

    return agent
