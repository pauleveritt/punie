"""Factory functions for creating Pydantic AI agents.

Provides create_pydantic_agent() for constructing Pydantic AI Agent instances
configured with ACPDeps and toolset (static or dynamic).
"""

import ast
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models import KnownModelName, Model, ModelSettings
from pydantic_ai.models.test import TestModel
from pydantic_ai.toolsets import AbstractToolset

from punie.agent.config import PUNIE_LOCAL_INSTRUCTIONS, AgentConfig
from punie.agent.deps import ACPDeps
from punie.agent.toolset import create_toolset

if TYPE_CHECKING:
    from punie.local import LocalClient
    from punie.perf import PerformanceCollector, TimedToolset
    from punie.training.server_config import ServerConfig
else:
    # Import at runtime for wrapping
    from punie.perf import PerformanceCollector, TimedToolset

logger = logging.getLogger(__name__)

# Local model defaults for OpenAI-compatible servers (LM Studio, mlx-lm.server)
DEFAULT_LOCAL_BASE_URL = "http://localhost:1234/v1"
DEFAULT_LOCAL_MODEL = "default"


@dataclass(frozen=True)
class LocalModelSpec:
    """Parsed local model specification."""

    base_url: str
    model_name: str


def _parse_local_spec(spec: str = "") -> LocalModelSpec:
    """Parse local model specification string.

    Supports three formats:
    1. "" (empty) → default URL + default model
    2. "model-name" → default URL + given model
    3. "http://host:port/v1/model" → custom URL + model

    Args:
        spec: Model specification string

    Returns:
        LocalModelSpec with base_url and model_name

    Examples:
        >>> _parse_local_spec("")
        LocalModelSpec(base_url='http://localhost:1234/v1', model_name='default')

        >>> _parse_local_spec("my-model")
        LocalModelSpec(base_url='http://localhost:1234/v1', model_name='my-model')

        >>> _parse_local_spec("http://localhost:8080/v1/custom-model")
        LocalModelSpec(base_url='http://localhost:8080/v1', model_name='custom-model')
    """
    if not spec:
        return LocalModelSpec(base_url=DEFAULT_LOCAL_BASE_URL, model_name=DEFAULT_LOCAL_MODEL)

    # Check if it's a URL (starts with http:// or https://)
    if spec.startswith(("http://", "https://")):
        # Split URL to extract base_url and model_name
        # Expected format: http://host:port/v1/model-name
        parts = spec.rsplit("/", 1)
        if len(parts) == 2:
            base_url, model_name = parts
        else:
            # URL without model name, use default model
            base_url = spec.rstrip("/")
            model_name = DEFAULT_LOCAL_MODEL
        return LocalModelSpec(base_url=base_url, model_name=model_name)

    # Otherwise, it's just a model name
    return LocalModelSpec(base_url=DEFAULT_LOCAL_BASE_URL, model_name=spec)


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


def _create_local_model(spec: str = "") -> Model:
    """Create a local model via OpenAI-compatible API.

    Connects to LM Studio or mlx-lm.server via OpenAI-compatible API.
    Supports three specification formats:
    1. "" (empty) → http://localhost:1234/v1 + "default"
    2. "model-name" → http://localhost:1234/v1 + model-name
    3. "http://host:port/v1/model" → custom URL + model

    Args:
        spec: Model specification string (see formats above)

    Returns:
        OpenAIChatModel configured to connect to local server

    Examples:
        >>> model = _create_local_model()  # Default LM Studio
        >>> model = _create_local_model("my-model")  # LM Studio with specific model
        >>> model = _create_local_model("http://localhost:8080/v1/qwen")  # Custom server
    """
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    parsed = _parse_local_spec(spec)
    logger.info("Creating local model: %s at %s", parsed.model_name, parsed.base_url)

    provider = OpenAIProvider(base_url=parsed.base_url)
    return OpenAIChatModel(parsed.model_name, provider=provider)


def create_server_model(config: "ServerConfig") -> Model:
    """Create a model for mlx_lm.server based on ServerConfig.

    Thin wrapper using OpenAIProvider + OpenAIChatModel pattern.
    Used by evaluation and training infrastructure.

    Args:
        config: ServerConfig with base_url and model configuration

    Returns:
        OpenAIChatModel configured to connect to mlx_lm.server

    Examples:
        >>> from punie.training.server_config import ServerConfig
        >>> config = ServerConfig(model_path="mlx-community/Qwen3-Coder-30B")
        >>> model = create_server_model(config)
    """
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    logger.info("Creating server model at %s", config.base_url)

    provider = OpenAIProvider(base_url=config.base_url)
    # mlx_lm.server requires the actual model path in API requests
    return OpenAIChatModel(config.model_path, provider=provider)


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
               - "local": Local model via OpenAI-compatible API (default: http://localhost:1234/v1)
               - "local:model-name": Local model with specific model name
               - "local:http://host:port/v1/model": Custom local server URL + model
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
        model = _create_local_model("")
    elif isinstance(model, str) and model.startswith("local:"):
        model = _create_local_model(model.split(":", 1)[1])

    # Build model settings dict with standard parameters
    model_settings_dict = {
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }

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
        model: Model name (default: "local" for local OpenAI-compatible server).
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
