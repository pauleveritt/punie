"""MLX model implementation for local, offline AI on Apple Silicon.

This module provides a Pydantic AI Model implementation that uses MLX for
inference on macOS arm64 devices. It supports tool calling through chat
templates and regex parsing of tool call tags.

Note: This module can be imported on any platform, but requires mlx-lm to
actually run models. Use TYPE_CHECKING guards for imports.
"""

from __future__ import annotations

import json
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, AsyncIterator

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
    pass


def parse_tool_calls(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Extract tool calls from model output.

    MLX models output tool calls as:
    <tool_call>{"name": "function_name", "arguments": {...}}</tool_call>

    Args:
        text: Model output possibly containing <tool_call>...</tool_call> blocks

    Returns:
        Tuple of (remaining_text, list of tool call dicts)
    """
    pattern = r"<tool_call>(.*?)</tool_call>"
    matches = re.findall(pattern, text, re.DOTALL)

    calls = []
    for match in matches:
        try:
            call = json.loads(match.strip())
            if "name" in call:
                calls.append(call)
        except json.JSONDecodeError:
            # Skip invalid JSON
            continue

    # Remove tool call tags from text
    clean_text = re.sub(pattern, "", text, flags=re.DOTALL).strip()

    return clean_text, calls


class AsyncStream:
    """Wraps a synchronous iterator in an async interface."""

    def __init__(self, sync_iterator: Any) -> None:
        """Initialize with a sync iterator.

        Args:
            sync_iterator: Synchronous iterator to wrap
        """
        self.sync_iterator = sync_iterator

    def __aiter__(self) -> AsyncStream:
        """Return self as async iterator."""
        return self

    async def __anext__(self) -> Any:
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
    _stream_iterator: Any = field(repr=False)
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
        async for token_dict in AsyncStream(self._stream_iterator):
            if isinstance(token_dict, dict) and "text" in token_dict:
                token = token_dict["text"]
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
        model_data: Any | None = None,
        tokenizer: Any | None = None,
        settings: ModelSettings | None = None,
        profile: Any = None,
    ) -> None:
        """Initialize MLX model with pre-loaded components.

        For production use, use the `from_pretrained()` class method instead.

        Args:
            model_name: HuggingFace model name
            model_data: Pre-loaded MLX model data (for testing)
            tokenizer: Pre-loaded tokenizer (for testing)
            settings: Optional model settings
            profile: Optional model profile (not used for MLX)
        """
        super().__init__(settings=settings, profile=profile)
        self._model_name = model_name
        self.model_data = model_data
        self.tokenizer = tokenizer

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

        model_data, tokenizer = mlx_load(model_name)
        return cls(
            model_name,
            model_data=model_data,
            tokenizer=tokenizer,
            settings=settings,
            profile=profile,
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

        # Generate response
        output = self._generate(
            messages=chat_messages,
            tools=tools,
            settings=model_settings,
            stream=False,
        )

        # Parse for tool calls
        text, tool_calls = parse_tool_calls(output)

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
                        tool_calls.append(
                            {
                                "id": part.tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": part.tool_name,
                                    "arguments": json.dumps(part.args_as_dict()),
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

    def _generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        settings: ModelSettings | None,
        stream: bool,
    ) -> Any:
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

        # Apply chat template
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tools=tools,
            tokenize=False,
            add_generation_prompt=True,
        )

        # Prepare generation kwargs
        gen_kwargs: dict[str, Any] = {}
        if settings:
            if "temperature" in settings:
                gen_kwargs["temp"] = settings["temperature"]
            if "max_tokens" in settings:
                gen_kwargs["max_tokens"] = settings["max_tokens"]
            if "top_p" in settings:
                gen_kwargs["top_p"] = settings["top_p"]

        # Generate
        if stream:
            return stream_generate(
                self.model_data,
                self.tokenizer,
                prompt,
                **gen_kwargs,
            )
        else:
            return generate(
                self.model_data,
                self.tokenizer,
                prompt,
                **gen_kwargs,
            )
