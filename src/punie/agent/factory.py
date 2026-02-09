"""Factory functions for creating Pydantic AI agents.

Provides create_pydantic_agent() for constructing Pydantic AI Agent instances
configured with ACPDeps and toolset (static or dynamic).
"""

import ast
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic_ai import Agent, FunctionToolset, ModelRetry, RunContext
from pydantic_ai.models import KnownModelName, Model, ModelSettings
from pydantic_ai.models.test import TestModel
from pydantic_ai.toolsets import AbstractToolset

from punie.agent.config import PUNIE_LOCAL_INSTRUCTIONS, AgentConfig
from punie.agent.deps import ACPDeps
from punie.agent.toolset import create_toolset

if TYPE_CHECKING:
    from punie.local import LocalClient
    from punie.perf import PerformanceCollector, TimedToolset
else:
    # Import at runtime for wrapping
    from punie.perf import PerformanceCollector, TimedToolset

logger = logging.getLogger(__name__)


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


def _validate_python_code_blocks(text: str) -> None:
    """Validate Python syntax in fenced code blocks.

    Extracts ```python code blocks and validates each with ast.parse().
    Raises ModelRetry if any block has invalid syntax.

    Args:
        text: Output text to validate

    Raises:
        ModelRetry: If any Python code block has invalid syntax
    """
    # Match ```python ... ``` blocks
    pattern = r"```python\n(.*?)```"
    code_blocks = re.findall(pattern, text, re.DOTALL)

    for i, code in enumerate(code_blocks, 1):
        try:
            ast.parse(code)
        except SyntaxError as e:
            logger.warning("Python syntax error in code block %d: %s", i, e)
            raise ModelRetry(
                f"Code block {i} has invalid Python syntax: {e}. "
                "Please fix the syntax and try again."
            ) from e


def _create_local_model(model_name: str | None = None) -> Model:
    """Create a local MLX model for offline inference on Apple Silicon.

    Args:
        model_name: Optional HuggingFace model name.
                   Defaults to mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit

    Returns:
        MLXModel instance

    Raises:
        ImportError: If mlx-lm is not installed or not on macOS arm64
    """
    from punie.models.mlx import MLXModel

    if model_name is None:
        model_name = "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"

    logger.info("Creating local MLX model: %s", model_name)
    return MLXModel.from_pretrained(model_name)


def create_pydantic_agent(
    model: KnownModelName | Model = "test",
    toolset: AbstractToolset[ACPDeps] | None = None,
    config: AgentConfig | None = None,
    perf_collector: PerformanceCollector | None = None,
) -> Agent[ACPDeps, str]:
    """Create a Pydantic AI agent configured for Punie.

    Args:
        model: Model name (default: "test" for enhanced TestModel, no LLM calls).
               Special values:
               - "test": Enhanced TestModel with realistic responses
               - "local": Local MLX model (mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit)
               - "local:model-name": Local MLX model with specific HuggingFace model
               Other options: "openai:gpt-4", "anthropic:claude-3-5-sonnet", etc.
               Can also pass a Model instance directly.
        toolset: Optional toolset to use. If None, uses create_toolset() (all 7 static tools).
                 For dynamic discovery, pass create_toolset_from_catalog() or
                 create_toolset_from_capabilities() result.
        config: Optional AgentConfig. If None, uses AgentConfig() defaults (PyCharm/ACP mode).
        perf_collector: Optional PerformanceCollector for timing measurements. If provided,
                       wraps toolset with TimedToolset to record timing data.

    Returns:
        Pydantic AI Agent configured with ACPDeps and toolset
    """
    if toolset is None:
        toolset = create_toolset()

    if config is None:
        config = AgentConfig()

    # Wrap toolset with performance measurement if requested
    if perf_collector is not None:
        toolset = TimedToolset(wrapped=toolset, collector=perf_collector)

    # Use enhanced test model if "test" string is passed
    if model == "test":
        logger.info("Using enhanced test model for better debugging")
        model = _create_enhanced_test_model()
    elif model == "local":
        model = _create_local_model()
    elif isinstance(model, str) and model.startswith("local:"):
        model = _create_local_model(model.split(":", 1)[1])

    # Build model settings dict dynamically to include optional parameters
    model_settings_dict = {
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "repetition_penalty": config.repetition_penalty,
    }
    if config.max_kv_size is not None:
        model_settings_dict["max_kv_size"] = config.max_kv_size

    agent = Agent[ACPDeps, str](
        model,
        deps_type=ACPDeps,
        instructions=config.instructions,
        model_settings=ModelSettings(**model_settings_dict),
        retries=config.retries,
        output_retries=config.output_retries,
        toolsets=[toolset],
    )

    @agent.output_validator
    def validate_response(ctx: RunContext[ACPDeps], output: str) -> str:
        if not output.strip():
            raise ModelRetry("Response was empty, please provide a substantive answer.")

        # Validate Python syntax in code blocks if enabled
        if config.validate_python_syntax:
            _validate_python_code_blocks(output)

        return output

    return agent


def create_local_agent(
    model: KnownModelName | Model = "local",
    workspace: Path | None = None,
    config: AgentConfig | None = None,
    perf_collector: PerformanceCollector | None = None,
) -> tuple[Agent[ACPDeps, str], LocalClient]:
    """Create a Pydantic AI agent with local filesystem tools.

    This creates an agent that uses LocalClient for filesystem and subprocess
    operations instead of delegating to IDE via ACP. The agent works standalone
    without requiring PyCharm or any IDE connection.

    Args:
        model: Model name (default: "local" for MLX model).
               Can use "test" for enhanced TestModel or any other model.
        workspace: Root directory for file operations. Defaults to current directory.
        config: Optional AgentConfig. If None, defaults to local-mode config with
                PUNIE_LOCAL_INSTRUCTIONS and validate_python_syntax=True.
        perf_collector: Optional PerformanceCollector for timing measurements.

    Returns:
        Tuple of (agent, client). Callers construct ACPDeps per prompt using:
        ACPDeps(client_conn=client, session_id=..., tracker=...)
    """
    from punie.local import LocalClient

    if config is None:
        config = AgentConfig(
            instructions=PUNIE_LOCAL_INSTRUCTIONS,
            validate_python_syntax=True,
        )

    workspace = workspace or Path.cwd()
    client = LocalClient(workspace=workspace)
    agent = create_pydantic_agent(model=model, config=config, perf_collector=perf_collector)

    return agent, client
