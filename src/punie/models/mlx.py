"""MLX model implementation for local, offline AI on Apple Silicon.

This module provides a Pydantic AI Model implementation that uses MLX for
inference on macOS arm64 devices. It supports tool calling through chat
templates and regex parsing of tool call tags.

Tool Calling Format:
    Qwen2.5-Coder models should output tool calls in this format:
        <tool_call>{"name": "function_name", "arguments": {...}}</tool_call>

    The chat template should instruct the model to use this format when
    tools are provided. If the model outputs raw JSON without <tool_call>
    tags, it may indicate:
    - The model variant doesn't support tool calling
    - The chat template is missing or incorrect
    - The model needs fine-tuning with tool calling examples

    Recommended models for tool calling:
    - mlx-community/Qwen2.5-Coder-7B-Instruct-4bit (default, good balance)
    - mlx-community/Qwen2.5-Coder-7B-Instruct (non-quantized, best quality)
    - mlx-community/Qwen2.5-Coder-14B-Instruct-4bit (larger, slower, better)

Troubleshooting:
    If tool calls aren't working (model outputs raw JSON):
    1. Check logs for "⚠️  Tool calling may not work" warnings
    2. Try a non-quantized model (4-bit quantization may affect tool calling)
    3. Verify chat template with: model.tokenizer.chat_template
    4. Check that PyCharm is providing enabled capabilities

Note: This module can be imported on any platform, but requires mlx-lm to
actually run models. Use TYPE_CHECKING guards for imports.
"""

from __future__ import annotations

import json
import logging
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable, Generator, TypedDict

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponsePart,
    ModelResponseStreamEvent,
    PartStartEvent,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import (
    Model,
    ModelRequestParameters,
    ModelSettings,
    RequestUsage,
    StreamedResponse,
)
from pydantic_ai.result import RunContext

if TYPE_CHECKING:
    import mlx.nn as nn
    from mlx_lm.generate import GenerationResponse
    from mlx_lm.tokenizer_utils import TokenizerWrapper
    from transformers import PreTrainedTokenizer

    MLXTokenizer = PreTrainedTokenizer | TokenizerWrapper

logger = logging.getLogger(__name__)


def check_chat_template_tool_support(tokenizer: "MLXTokenizer") -> tuple[bool, str]:
    """Check if tokenizer's chat template supports tool calling.

    Qwen2.5-Coder models should have a chat template that includes:
    - Support for 'tools' parameter in apply_chat_template
    - Formatting that instructs the model to use <tool_call> tags

    Args:
        tokenizer: The tokenizer to check

    Returns:
        Tuple of (supports_tools, diagnostic_message)
    """
    # Check if chat template exists
    if not hasattr(tokenizer, 'chat_template') or not tokenizer.chat_template:
        return False, "Tokenizer has no chat_template attribute"

    template = tokenizer.chat_template

    # For Qwen models, the template should mention tool_call or function
    if isinstance(template, str):
        has_tool_markers = any(
            marker in template.lower()
            for marker in ['tool_call', 'tools', 'function', '<tool_call>']
        )
        if not has_tool_markers:
            return False, (
                "Chat template does not contain tool/function markers. "
                "This model may not support tool calling."
            )

        # Qwen2.5 specifically uses <tool_call> tags
        if '<tool_call>' in template or 'tool_call' in template:
            return True, "Chat template appears to support Qwen-style <tool_call> tags"

        return False, "Chat template mentions tools but may not use expected format"

    # Template is not a string (might be a dict or custom object)
    return False, f"Chat template is type {type(template)}, cannot validate"


class ToolCallDict(TypedDict):
    """A parsed tool call extracted from model output."""

    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class SamplerParams:
    """Parameters for mlx-lm's make_sampler().
    Field names match make_sampler()'s parameter names exactly.
    Frozen so typos raise TypeError at construction time.
    """

    temp: float = 0.0
    top_p: float = 0.0
    repetition_penalty: float = 1.0


@dataclass(frozen=True)
class GenerateParams:
    """Parameters for mlx-lm's generate/stream_generate.
    Field names match generate_step()'s keyword arguments.
    """

    max_tokens: int = 2048
    sampler: Callable | None = None
    max_kv_size: int | None = None

    def to_kwargs(self) -> dict[str, Any]:
        """Convert to kwargs dict for mlx-lm functions."""
        d: dict[str, Any] = {"max_tokens": self.max_tokens}
        if self.sampler is not None:
            d["sampler"] = self.sampler
        if self.max_kv_size is not None:
            d["max_kv_size"] = self.max_kv_size
        return d


def parse_tool_calls(text: str) -> tuple[str, list[ToolCallDict]]:
    """Extract tool calls from model output.

    Supports two formats:
    1. JSON: <tool_call>{"name": "function_name", "arguments": {...}}</tool_call>
    2. XML: <tool_call><function=name><parameter=key>value</parameter></function></tool_call>

    Args:
        text: Model output possibly containing tool call blocks

    Returns:
        Tuple of (remaining_text, list of tool call dicts)
    """
    calls = []
    clean_text = text
    patterns_to_remove = []

    # Pattern 1: Standard <tool_call>...</tool_call> blocks
    pattern = r"<tool_call>(.*?)</tool_call>"
    matches = re.finditer(pattern, text, re.DOTALL)

    for match in matches:
        match_stripped = match.group(1).strip()
        parsed_successfully = False

        # Try JSON format first
        if match_stripped.startswith("{"):
            try:
                call = json.loads(match_stripped)
                if "name" in call:
                    calls.append(call)
                    parsed_successfully = True
            except json.JSONDecodeError:
                pass

        # Try XML format if JSON failed: <function=name><parameter=key>value</parameter></function>
        if not parsed_successfully:
            xml_call = _parse_xml_tool_call(match_stripped)
            if xml_call:
                calls.append(xml_call)
                parsed_successfully = True

        # Always remove the tool_call tags, even if parsing failed
        patterns_to_remove.append((match.start(), match.end()))

    # Pattern 2: Broken format without opening <tool_call> tag
    # Some models output: <function=name>...</function></tool_call>
    broken_pattern = r"<function=([^>]+)>(.*?)</function>\s*</tool_call>"
    broken_matches = re.finditer(broken_pattern, text, re.DOTALL)

    for match in broken_matches:
        # Check if this match overlaps with any already-found matches
        start, end = match.start(), match.end()
        overlaps = any(s <= start < e or s < end <= e for s, e in patterns_to_remove)
        if overlaps:
            continue

        func_name = match.group(1)
        params_block = match.group(2)
        xml_call = _parse_xml_function_block(func_name, params_block)
        if xml_call:
            calls.append(xml_call)
            patterns_to_remove.append((start, end))

    # Remove matched patterns from text (in reverse order to preserve indices)
    patterns_to_remove.sort(reverse=True)
    for start, end in patterns_to_remove:
        clean_text = clean_text[:start] + clean_text[end:]

    clean_text = clean_text.strip()

    return clean_text, calls


def _parse_xml_tool_call(xml_content: str) -> ToolCallDict | None:
    """Parse XML-format tool call.

    Expected format: <function=name><parameter=key>value</parameter></function>

    Args:
        xml_content: XML content inside <tool_call> tags

    Returns:
        Tool call dict or None if parsing fails
    """
    # Extract function name
    func_match = re.search(r"<function=([^>]+)>", xml_content)
    if not func_match:
        return None

    func_name = func_match.group(1).strip()

    # Extract parameters
    param_pattern = r"<parameter=([^>]+)>(.*?)</parameter>"
    param_matches = re.findall(param_pattern, xml_content, re.DOTALL)

    arguments = {}
    for param_name, param_value in param_matches:
        arguments[param_name.strip()] = param_value.strip()

    return {"name": func_name, "arguments": arguments}


def _parse_xml_function_block(func_name: str, params_block: str) -> ToolCallDict | None:
    """Parse XML function block (broken format without <tool_call> opening tag).

    Args:
        func_name: Function name extracted from <function=name>
        params_block: Content between <function> and </function> tags

    Returns:
        Tool call dict or None if parsing fails
    """
    # Extract parameters
    param_pattern = r"<parameter=([^>]+)>(.*?)</parameter>"
    param_matches = re.findall(param_pattern, params_block, re.DOTALL)

    arguments = {}
    for param_name, param_value in param_matches:
        arguments[param_name.strip()] = param_value.strip()

    if not arguments:
        return None

    return {"name": func_name.strip(), "arguments": arguments}


class AsyncStream:
    """Wraps a synchronous iterator in an async interface."""

    def __init__(
        self, sync_iterator: "Generator[GenerationResponse, None, None]"
    ) -> None:
        """Initialize with a sync iterator.

        Args:
            sync_iterator: Synchronous iterator to wrap
        """
        self.sync_iterator = sync_iterator

    def __aiter__(self) -> AsyncStream:
        """Return self as async iterator."""
        return self

    async def __anext__(self) -> "GenerationResponse":
        """Get next item from sync iterator asynchronously."""
        try:
            return next(self.sync_iterator)
        except StopIteration as e:
            raise StopAsyncIteration from e


@dataclass
class MLXStreamedResponse(StreamedResponse):
    """Streamed response from MLX model.

    Note: Streaming does NOT parse tool calls. Tool calling requires the full
    response text to detect closing tags reliably.
    """

    _model_name: str = field(repr=False)
    _stream_iterator: "Generator[GenerationResponse, None, None]" = field(repr=False)
    _timestamp: datetime = field(default_factory=datetime.now, repr=False)

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model_name

    @property
    def provider_name(self) -> str | None:
        """Get the provider name."""
        return "mlx"

    @property
    def provider_url(self) -> str | None:
        """Get the provider base URL."""
        return None

    @property
    def timestamp(self) -> datetime:
        """Get the timestamp of the response."""
        return self._timestamp

    async def _get_event_iterator(self) -> AsyncIterator[ModelResponseStreamEvent]:
        """Stream text tokens from MLX model.

        Yields:
            ModelResponseStreamEvent: Stream events with text deltas
        """
        # Start the text part
        text_part = TextPart(content="")
        yield PartStartEvent(index=0, part=text_part)

        # Stream text tokens
        async for response in AsyncStream(self._stream_iterator):
            token = response.text
            if token:
                for event in self._parts_manager.handle_text_delta(
                    vendor_part_id=0, content=token
                ):
                    yield event

        # Usage is not tracked during streaming
        # Could be implemented by counting tokens if needed


class MLXModel(Model):
    """Pydantic AI model implementation using MLX for local inference.

    This model runs entirely locally on Apple Silicon Macs using the MLX
    framework. It supports tool calling through chat templates and regex
    parsing of tool call tags in the output.

    Example:
        ```python
        from punie.models.mlx import MLXModel

        model = MLXModel("mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")
        agent = Agent(model=model, tools=[...])
        result = agent.run_sync("Hello!")
        ```

    Note:
        Requires mlx-lm to be installed. Install with:
        ```bash
        uv pip install 'punie[local]'
        ```
    """

    def __init__(
        self,
        model_name: str,
        *,
        model_data: "nn.Module | None" = None,
        tokenizer: "MLXTokenizer | None" = None,
        settings: ModelSettings | None = None,
        profile: Any = None,
        prompt_cache: Any = None,
        supports_repetition_penalty: bool = False,
    ) -> None:
        """Initialize MLX model with pre-loaded components.

        For production use, use the `from_pretrained()` class method instead.

        Args:
            model_name: HuggingFace model name
            model_data: Pre-loaded MLX model data (for testing)
            tokenizer: Pre-loaded tokenizer (for testing)
            settings: Optional model settings
            profile: Optional model profile (not used for MLX)
            prompt_cache: Optional prompt cache for reusing prefix tokens
            supports_repetition_penalty: Whether mlx-lm supports repetition_penalty
        """
        super().__init__(settings=settings, profile=profile)
        self._model_name = model_name
        self.model_data = model_data
        self.tokenizer = tokenizer
        self._prompt_cache = prompt_cache
        self._supports_repetition_penalty = supports_repetition_penalty

    @classmethod
    def from_pretrained(
        cls,
        model_name: str,
        *,
        settings: ModelSettings | None = None,
        profile: Any = None,
    ) -> "MLXModel":
        """Load an MLX model from HuggingFace.

        Args:
            model_name: HuggingFace model name (e.g., "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")
            settings: Optional model settings
            profile: Optional model profile (not used for MLX)

        Returns:
            Initialized MLXModel with loaded model and tokenizer

        Raises:
            ImportError: If mlx-lm is not installed
        """
        try:
            from mlx_lm.utils import load as mlx_load
        except ImportError as e:
            msg = (
                "mlx-lm is required for local model support. "
                "Install with: uv pip install 'punie[local]'\n"
                "Note: mlx-lm only works on macOS with Apple Silicon (arm64)."
            )
            raise ImportError(msg) from e

        # Check memory before loading
        from punie.models.memory import (
            check_memory_available,
            estimate_model_size,
            get_memory_snapshot,
        )

        model_size_mb = estimate_model_size(model_name)
        available, snapshot = check_memory_available(model_size_mb)

        logger.info(
            "Memory check before loading %s (estimated %d MB): current RSS = %.1f MB",
            model_name,
            model_size_mb,
            snapshot.rss_mb,
        )

        if not available:
            logger.warning(
                "Insufficient memory for model %s (estimated %d MB, current RSS %.1f MB). "
                "Loading anyway — user may know their system can handle it.",
                model_name,
                model_size_mb,
                snapshot.rss_mb,
            )

        try:
            logger.info(
                "Loading model %s (will use HuggingFace cache if available)...",
                model_name,
            )
            result = mlx_load(model_name)
            # mlx_load returns (model, tokenizer) by default
            model_data, tokenizer = result[0], result[1]
            logger.info("Model %s loaded from mlx_load()", model_name)
        except Exception as e:
            # Check if error indicates model not downloaded
            error_msg = str(e).lower()
            if (
                "not found" in error_msg
                or "does not exist" in error_msg
                or "no such file" in error_msg
            ):
                msg = (
                    f"Model '{model_name}' is not downloaded.\n"
                    f"Download it with: punie download-model {model_name}"
                )
                raise RuntimeError(msg) from e
            raise

        # Log actual memory usage after loading
        snapshot_after = get_memory_snapshot()
        logger.info(
            "Model loaded successfully. RSS after load: %.1f MB (delta: %.1f MB)",
            snapshot_after.rss_mb,
            snapshot_after.rss_mb - snapshot.rss_mb,
        )

        # Check for repetition_penalty support (once at load time)
        from mlx_lm.sample_utils import make_sampler
        supports_repetition_penalty = False
        try:
            # Test if repetition_penalty is accepted
            make_sampler(temp=0.0, top_p=0.0, repetition_penalty=1.0)  # type: ignore[call-arg]
            supports_repetition_penalty = True
            logger.debug("mlx-lm supports repetition_penalty")
        except TypeError:
            logger.debug("mlx-lm does not support repetition_penalty yet")

        # Create prompt cache for reusing system prompt + tool definitions
        # Note: prompt caching not yet available in mlx-lm 0.30.x
        prompt_cache = None
        try:
            from mlx_lm.utils import make_prompt_cache  # type: ignore[attr-defined]
            prompt_cache = make_prompt_cache(model_data)  # type: ignore[operator]
            logger.info("Created prompt cache for prefix token reuse")
        except (ImportError, AttributeError):
            # Prompt caching not yet available in current mlx-lm version
            # Infrastructure is in place and will activate when mlx-lm adds support
            logger.debug(
                "Prompt caching not available in mlx-lm %s - will activate when feature is added",
                getattr(__import__('mlx_lm'), '__version__', 'unknown'),
            )

        return cls(
            model_name,
            model_data=model_data,
            tokenizer=tokenizer,
            settings=settings,
            profile=profile,
            prompt_cache=prompt_cache,
            supports_repetition_penalty=supports_repetition_penalty,
        )

    @property
    def model_name(self) -> str:
        """The model name."""
        return self._model_name

    @property
    def system(self) -> str:
        """The model provider system name."""
        return "mlx"

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        """Make a request to the MLX model.

        Args:
            messages: List of messages in the conversation
            model_settings: Optional model-specific settings
            model_request_parameters: Request parameters including tools

        Returns:
            ModelResponse with text and/or tool call parts
        """
        model_settings, model_request_parameters = self.prepare_request(
            model_settings, model_request_parameters
        )

        # Build messages and tools
        chat_messages = self._map_request(messages)
        tools = self._build_tools(model_request_parameters)

        logger.info("=== MLX request() starting ===")
        logger.info(f"Chat messages: {len(chat_messages)} messages")
        logger.info(f"Tools available: {len(tools) if tools else 0}")

        # Generate response
        output = self._generate(
            messages=chat_messages,
            tools=tools,
            settings=model_settings,
            stream=False,
        )
        # Type narrowing: stream=False returns str
        assert isinstance(output, str)

        # Parse for tool calls
        logger.info("Parsing output for tool calls...")
        text, tool_calls = parse_tool_calls(output)

        logger.info(f"Parsed result: {len(tool_calls)} tool calls, {len(text)} chars of text")
        if tool_calls:
            logger.info(f"Tool calls parsed: {[tc['name'] for tc in tool_calls]}")

        # Build response parts
        parts: list[ModelResponsePart] = []

        if text:
            parts.append(TextPart(content=text))

        for tool_call in tool_calls:
            parts.append(
                ToolCallPart(
                    tool_name=tool_call["name"],
                    args=tool_call.get("arguments", {}),
                )
            )

        logger.info(f"=== MLX request() complete: {len(parts)} response parts ===")

        return ModelResponse(
            parts=parts,
            model_name=self._model_name,
            timestamp=datetime.now(),
            usage=RequestUsage(),  # TODO: Implement token counting
        )

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: RunContext[Any] | None = None,
    ) -> AsyncIterator[StreamedResponse]:
        """Stream a response from the MLX model.

        Note: Streaming does NOT parse tool calls. Use request() for tool calling.

        Args:
            messages: List of messages in the conversation
            model_settings: Optional model-specific settings
            model_request_parameters: Request parameters
            run_context: Optional run context

        Yields:
            MLXStreamedResponse: Streamed response object
        """
        model_settings, model_request_parameters = self.prepare_request(
            model_settings, model_request_parameters
        )

        # Build messages and tools
        chat_messages = self._map_request(messages)
        tools = self._build_tools(model_request_parameters)

        # Generate streaming response
        stream_iterator = self._generate(
            messages=chat_messages,
            tools=tools,
            settings=model_settings,
            stream=True,
        )
        # Type narrowing: stream=True returns Generator
        assert not isinstance(stream_iterator, str)

        yield MLXStreamedResponse(
            model_request_parameters=model_request_parameters,
            _model_name=self._model_name,
            _stream_iterator=stream_iterator,
        )

    def _build_tools(
        self, params: ModelRequestParameters
    ) -> list[dict[str, Any]] | None:
        """Convert Pydantic AI tool definitions to OpenAI chat format.

        Args:
            params: Model request parameters containing tool definitions

        Returns:
            List of tool dicts in OpenAI format, or None if no tools
        """
        if not params.function_tools:
            return None

        tools = []
        for tool_def in params.function_tools:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool_def.name,
                        "description": tool_def.description or "",
                        "parameters": tool_def.parameters_json_schema,
                    },
                }
            )

        return tools

    def _map_request(self, messages: list[ModelMessage]) -> list[dict[str, Any]]:
        """Convert Pydantic AI messages to MLX chat format.

        Args:
            messages: List of Pydantic AI messages

        Returns:
            List of message dicts in OpenAI chat format
        """
        chat_messages = []

        for msg in messages:
            if isinstance(msg, ModelRequest):
                # System prompt
                for part in msg.parts:
                    if isinstance(part, SystemPromptPart):
                        chat_messages.append(
                            {"role": "system", "content": part.content}
                        )

                # User message
                user_content = ""
                for part in msg.parts:
                    if isinstance(part, UserPromptPart):
                        if isinstance(part.content, str):
                            user_content += part.content
                        else:
                            # Handle sequence of UserContent (images, etc.)
                            for item in part.content:
                                if hasattr(item, "content") and isinstance(
                                    item.content, str
                                ):
                                    user_content += item.content
                    elif isinstance(part, ToolReturnPart):
                        # Add tool result as user message
                        chat_messages.append(
                            {
                                "role": "tool",
                                "content": part.model_response_str(),
                                "tool_call_id": part.tool_call_id,
                            }
                        )

                if user_content:
                    chat_messages.append({"role": "user", "content": user_content})

            elif isinstance(msg, ModelResponse):
                # Assistant message
                assistant_content = ""
                tool_calls = []

                for part in msg.parts:
                    if isinstance(part, TextPart):
                        assistant_content += part.content
                    elif isinstance(part, ToolCallPart):
                        # Keep arguments as dict for Qwen3 template compatibility
                        # (Qwen3 template expects dict, not JSON string)
                        tool_calls.append(
                            {
                                "id": part.tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": part.tool_name,
                                    "arguments": part.args_as_dict(),
                                },
                            }
                        )

                msg_dict: dict[str, Any] = {"role": "assistant"}
                if assistant_content:
                    msg_dict["content"] = assistant_content
                if tool_calls:
                    msg_dict["tool_calls"] = tool_calls

                chat_messages.append(msg_dict)

        return chat_messages

    @staticmethod
    def _build_generate_params(
        settings: ModelSettings | None,
    ) -> tuple[SamplerParams, GenerateParams]:
        """Extract typed generation parameters from ModelSettings."""
        sampler_params = SamplerParams(
            temp=settings.get("temperature", 0.0) if settings else 0.0,
            top_p=settings.get("top_p", 0.0) if settings else 0.0,
            repetition_penalty=settings.get("repetition_penalty", 1.0) if settings else 1.0,  # type: ignore[typeddict-item]
        )
        max_tokens = 2048
        if settings and "max_tokens" in settings:
            max_tokens = settings["max_tokens"]
        max_kv_size = None
        if settings and "max_kv_size" in settings:
            max_kv_size = settings["max_kv_size"]  # type: ignore[typeddict-item]
        return sampler_params, GenerateParams(max_tokens=max_tokens, max_kv_size=max_kv_size)

    def _generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        settings: ModelSettings | None,
        stream: bool,
    ) -> "str | Generator[GenerationResponse, None, None]":
        """Generate response using MLX.

        Args:
            messages: Chat messages in OpenAI format
            tools: Optional tool definitions in OpenAI format
            settings: Optional model settings
            stream: Whether to stream the response

        Returns:
            Generated text string (if stream=False) or iterator (if stream=True)
        """
        # Import at runtime to avoid issues on non-macOS platforms
        from mlx_lm import generate, stream_generate
        from mlx_lm.sample_utils import make_sampler

        # Verify model and tokenizer are loaded
        if self.model_data is None or self.tokenizer is None:
            msg = "Model not loaded. Use from_pretrained() to load the model."
            raise RuntimeError(msg)

        # Log diagnostic info about tool calling setup
        logger.info("=== MLX Generation Diagnostics ===")
        logger.info(f"Model: {self._model_name}")
        logger.info(f"Number of messages: {len(messages)}")
        logger.info(f"Number of tools: {len(tools) if tools else 0}")

        if tools:
            logger.info(f"Tool names: {[t['function']['name'] for t in tools]}")
            # Log first tool definition for inspection
            logger.debug(f"First tool definition: {tools[0]}")

            # Check ALL tools for properties format issues
            for idx, tool_def in enumerate(tools):
                func = tool_def['function']
                tool_name = func.get('name', f'tool_{idx}')
                if 'parameters' in func:
                    params = func['parameters']
                    if 'properties' in params:
                        props = params['properties']
                        if not isinstance(props, dict):
                            logger.error(
                                f"Tool '{tool_name}' has properties that's not a dict: "
                                f"type={type(props)}, value={props}"
                            )
                    else:
                        logger.warning(f"Tool '{tool_name}' parameters has no 'properties' key")
                else:
                    logger.warning(f"Tool '{tool_name}' has no 'parameters' key")

        # Check if tokenizer has chat template and if it supports tools
        has_chat_template = hasattr(self.tokenizer, 'chat_template') and self.tokenizer.chat_template
        logger.info(f"Tokenizer has chat_template: {has_chat_template}")

        if has_chat_template:
            # Log a snippet of the chat template
            template = self.tokenizer.chat_template
            if isinstance(template, str):
                logger.debug(f"Chat template (first 200 chars): {template[:200]}")
            else:
                logger.debug(f"Chat template type: {type(template)}")

            # Check tool support if tools are provided
            if tools:
                supports_tools, message = check_chat_template_tool_support(self.tokenizer)
                if supports_tools:
                    logger.info(f"✓ {message}")
                else:
                    logger.warning(
                        f"⚠️  Tool calling may not work: {message}\n"
                        f"   Consider using a model explicitly trained for tool calling, such as:\n"
                        f"   - mlx-community/Qwen2.5-Coder-7B-Instruct (non-quantized)\n"
                        f"   - mlx-community/Qwen2.5-Coder-14B-Instruct-4bit"
                    )

        # Apply chat template
        try:
            prompt = self.tokenizer.apply_chat_template(
                messages,
                tools=tools,
                tokenize=False,
                add_generation_prompt=True,
            )

            # Log the formatted prompt
            logger.info(f"Chat template produced prompt length: {len(prompt)} chars")
            logger.debug(f"Full prompt:\n{'='*80}\n{prompt}\n{'='*80}")

            # Look for tool-related markers in the prompt
            if tools:
                tool_markers = ['<tool_call>', '<function', '"name":', '"arguments":', 'function_call']
                found_markers = [m for m in tool_markers if m in prompt]
                if found_markers:
                    logger.info(f"Tool markers found in prompt: {found_markers}")
                else:
                    logger.warning(
                        "⚠️  NO tool markers found in prompt! "
                        "Chat template may not support tool calling properly."
                    )

        except Exception as e:
            logger.error(f"Failed to apply chat template: {e}")
            raise

        # Build typed generation parameters
        sampler_params, gen_params = self._build_generate_params(settings)

        # Use repetition_penalty if supported (checked once at model load)
        if self._supports_repetition_penalty:
            sampler = make_sampler(
                temp=sampler_params.temp,
                top_p=sampler_params.top_p,
                repetition_penalty=sampler_params.repetition_penalty,  # type: ignore[call-arg]
            )
        else:
            # Use basic sampler without repetition_penalty
            if sampler_params.repetition_penalty != 1.0:
                logger.debug(
                    "repetition_penalty=%.1f configured but not supported in this mlx-lm version",
                    sampler_params.repetition_penalty,
                )
            sampler = make_sampler(
                temp=sampler_params.temp,
                top_p=sampler_params.top_p,
            )
        gen_kwargs = gen_params.to_kwargs()
        gen_kwargs["sampler"] = sampler

        # Add prompt cache to kwargs if available
        if self._prompt_cache is not None:
            gen_kwargs["prompt_cache"] = self._prompt_cache

        # Generate
        if stream:
            return stream_generate(
                self.model_data,
                self.tokenizer,
                prompt,
                **gen_kwargs,
            )
        else:
            output = generate(
                self.model_data,
                self.tokenizer,
                prompt,
                **gen_kwargs,
            )

            # Log raw output before processing
            logger.info(f"Raw model output length: {len(output)} chars")
            logger.debug(f"Raw output:\n{'='*80}\n{output}\n{'='*80}")

            # Check for tool call markers in output
            if tools:
                if "<tool_call>" in output:
                    logger.info("✓ Model output contains <tool_call> tags")
                elif "function_call" in output or '"name":' in output:
                    logger.warning(
                        "⚠️  Model output looks like tool call JSON but missing <tool_call> tags! "
                        "This suggests the model doesn't understand the expected format."
                    )
                else:
                    logger.info("Model output does not appear to contain tool calls")

            # Strip special tokens that may leak into output
            # Common patterns: <|im_end|>, <[im_end]>, </s>, <|endoftext|>
            special_tokens = [
                "<|im_end|>",
                "<[im_end]>",
                "<|im_start|>",
                "<[im_start]>",
                "</s>",
                "<|endoftext|>",
            ]
            for token in special_tokens:
                output = output.replace(token, "")

            cleaned_output = output.strip()
            if cleaned_output != output:
                logger.debug(f"Stripped {len(output) - len(cleaned_output)} chars of special tokens/whitespace")

            logger.info("=== MLX Generation Complete ===")
            return cleaned_output
