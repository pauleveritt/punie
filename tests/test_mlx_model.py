"""Tests for MLX model implementation.

These tests verify the MLX model integration WITHOUT requiring mlx-lm to be
installed. They use fakes and monkeypatching to test the logic in isolation.

Test groups:
- Pure function tests: parse_tool_calls()
- Message mapping tests: _map_request() conversion
- Model property tests: model_name, system, _build_tools()
- Request integration tests: request() with mocked _generate()
- Factory integration tests: model='local' handling
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from punie.models.mlx import AsyncStream, parse_tool_calls


# ============================================================================
# Pure function tests
# ============================================================================


def test_parse_single_tool_call():
    """Parse a single tool call from model output."""
    text = 'Some text<tool_call>{"name": "read", "arguments": {"path": "foo.py"}}</tool_call>'
    content, calls = parse_tool_calls(text)

    assert content == "Some text"
    assert len(calls) == 1
    assert calls[0]["name"] == "read"
    assert calls[0]["arguments"] == {"path": "foo.py"}


def test_parse_multiple_tool_calls():
    """Parse multiple tool calls from model output."""
    text = (
        'Let me help<tool_call>{"name": "read", "arguments": {"path": "a.py"}}</tool_call>'
        ' and <tool_call>{"name": "write", "arguments": {"path": "b.py", "content": "x"}}</tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert content == "Let me help and"
    assert len(calls) == 2
    assert calls[0]["name"] == "read"
    assert calls[1]["name"] == "write"


def test_parse_no_tool_calls():
    """Parse text with no tool calls returns empty list."""
    text = "Just plain text with no tool calls."
    content, calls = parse_tool_calls(text)

    assert content == "Just plain text with no tool calls."
    assert calls == []


def test_parse_invalid_json_tool_call():
    """Invalid JSON in tool call is skipped."""
    text = 'Text<tool_call>{"name": "read", invalid json}</tool_call> more text'
    content, calls = parse_tool_calls(text)

    # Invalid JSON should be stripped but not added to calls
    assert "invalid json" not in content
    assert calls == []


def test_parse_tool_call_missing_name():
    """Tool call without 'name' field is skipped."""
    text = 'Text<tool_call>{"arguments": {"path": "foo.py"}}</tool_call>'
    content, calls = parse_tool_calls(text)

    assert calls == []  # Missing name means invalid tool call


# ============================================================================
# AsyncStream tests
# ============================================================================


@pytest.mark.asyncio
async def test_async_stream_wraps_sync_iterator():
    """AsyncStream correctly wraps a sync iterator."""
    sync_iter = iter([1, 2, 3])
    async_stream = AsyncStream(sync_iter)

    results = []
    async for item in async_stream:
        results.append(item)

    assert results == [1, 2, 3]


@pytest.mark.asyncio
async def test_async_stream_raises_stop_async_iteration():
    """AsyncStream raises StopAsyncIteration when sync iterator is exhausted."""
    sync_iter = iter([])
    async_stream = AsyncStream(sync_iter)

    with pytest.raises(StopAsyncIteration):
        await async_stream.__anext__()


# ============================================================================
# Model property tests
# ============================================================================


def test_mlx_model_import_without_mlx_lm(monkeypatch):
    """MLX model module can be imported without mlx-lm installed."""
    # This test verifies TYPE_CHECKING guards work correctly
    from punie.models.mlx import MLXModel, parse_tool_calls

    # Should not raise ImportError
    assert MLXModel is not None
    assert parse_tool_calls is not None


def test_mlx_model_from_pretrained_without_mlx_lm():
    """MLXModel.from_pretrained() raises ImportError without mlx-lm."""
    from punie.models.mlx import MLXModel

    with pytest.raises(ImportError, match="mlx-lm is required"):
        MLXModel.from_pretrained("test-model")


def test_mlx_model_properties():
    """Test MLXModel properties with dependency injection."""
    from punie.models.mlx import MLXModel

    # Create model with injected mock dependencies (no mlx-lm needed!)
    model = MLXModel(
        "test-model-name",
        model_data=MagicMock(),
        tokenizer=MagicMock(),
    )

    assert model.model_name == "test-model-name"
    assert model.system == "mlx"


def test_build_tools_converts_function_tools():
    """Test _build_tools converts ToolDefinition to OpenAI format."""
    from punie.models.mlx import MLXModel
    from pydantic_ai.models import ModelRequestParameters
    from pydantic_ai.tools import ToolDefinition

    # Create model with dependency injection (no mlx-lm needed!)
    model = MLXModel("fake", model_data=MagicMock(), tokenizer=MagicMock())

    # Create tool definitions
    tool_def = ToolDefinition(
        name="test_tool",
        description="A test tool",
        parameters_json_schema={"type": "object", "properties": {}},
    )

    params = ModelRequestParameters(function_tools=[tool_def])
    tools = model._build_tools(params)

    assert tools is not None
    assert len(tools) == 1
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "test_tool"
    assert tools[0]["function"]["description"] == "A test tool"


def test_build_tools_returns_none_for_empty():
    """Test _build_tools returns None when no tools provided."""
    from punie.models.mlx import MLXModel
    from pydantic_ai.models import ModelRequestParameters

    # Create model with dependency injection (no mlx-lm needed!)
    model = MLXModel("fake", model_data=MagicMock(), tokenizer=MagicMock())

    params = ModelRequestParameters(function_tools=[])
    tools = model._build_tools(params)

    assert tools is None


# ============================================================================
# Message mapping tests
# ============================================================================


def test_map_request_with_system_and_user():
    """Test _map_request converts system and user messages correctly."""
    from punie.models.mlx import MLXModel
    from pydantic_ai.messages import (
        ModelRequest,
        SystemPromptPart,
        UserPromptPart,
    )

    # Create model with dependency injection (no mlx-lm needed!)
    model = MLXModel("fake", model_data=MagicMock(), tokenizer=MagicMock())

    messages = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="You are a helpful assistant."),
                UserPromptPart(content="Hello!"),
            ],
            kind="request",
        )
    ]

    chat_messages = model._map_request(messages)

    assert len(chat_messages) == 2
    assert chat_messages[0] == {"role": "system", "content": "You are a helpful assistant."}
    assert chat_messages[1] == {"role": "user", "content": "Hello!"}


def test_map_request_with_tool_return():
    """Test _map_request converts tool return messages correctly."""
    from punie.models.mlx import MLXModel
    from pydantic_ai.messages import (
        ModelRequest,
        ToolReturnPart,
        UserPromptPart,
    )

    # Create model with dependency injection (no mlx-lm needed!)
    model = MLXModel("fake", model_data=MagicMock(), tokenizer=MagicMock())

    messages = [
        ModelRequest(
            parts=[
                UserPromptPart(content="Read the file"),
                ToolReturnPart(
                    tool_name="read",
                    content="file contents",
                    tool_call_id="call_123",
                ),
            ],
            kind="request",
        )
    ]

    chat_messages = model._map_request(messages)

    # Should have tool message first (processed in loop order), then user message
    assert len(chat_messages) == 2
    assert chat_messages[0]["role"] == "tool"
    assert chat_messages[0]["tool_call_id"] == "call_123"
    assert "file contents" in chat_messages[0]["content"]
    assert chat_messages[1] == {"role": "user", "content": "Read the file"}


def test_map_request_with_model_response():
    """Test _map_request converts ModelResponse with text and tool calls."""
    from punie.models.mlx import MLXModel
    from pydantic_ai.messages import (
        ModelResponse,
        TextPart,
        ToolCallPart,
    )

    # Create model with dependency injection (no mlx-lm needed!)
    model = MLXModel("fake", model_data=MagicMock(), tokenizer=MagicMock())

    tool_call = ToolCallPart(
        tool_name="read",
        args={"path": "foo.py"},
        tool_call_id="call_123",
    )

    messages = [
        ModelResponse(
            parts=[
                TextPart(content="Let me read that file."),
                tool_call,
            ],
            model_name="test",
            timestamp=datetime.now(),
        )
    ]

    chat_messages = model._map_request(messages)

    assert len(chat_messages) == 1
    assert chat_messages[0]["role"] == "assistant"
    assert chat_messages[0]["content"] == "Let me read that file."
    assert len(chat_messages[0]["tool_calls"]) == 1
    assert chat_messages[0]["tool_calls"][0]["function"]["name"] == "read"


# ============================================================================
# Request integration tests
# ============================================================================


@pytest.mark.asyncio
async def test_request_with_text_response():
    """Test request() with text-only response."""
    from punie.models.mlx import MLXModel
    from pydantic_ai.messages import ModelRequest, TextPart, UserPromptPart
    from pydantic_ai.models import ModelRequestParameters

    # Create model with dependency injection and override _generate
    model = MLXModel("fake-model", model_data=MagicMock(), tokenizer=MagicMock())
    model._generate = lambda messages, tools, settings, stream: "This is a text response."

    messages = [ModelRequest(parts=[UserPromptPart(content="Hello")], kind="request")]
    params = ModelRequestParameters()

    response = await model.request(messages, None, params)

    assert len(response.parts) == 1
    assert isinstance(response.parts[0], TextPart)
    assert response.parts[0].content == "This is a text response."


@pytest.mark.asyncio
async def test_request_with_tool_calls():
    """Test request() with tool call response."""
    from punie.models.mlx import MLXModel
    from pydantic_ai.messages import (
        ModelRequest,
        ToolCallPart,
        UserPromptPart,
    )
    from pydantic_ai.models import ModelRequestParameters

    # Create model with dependency injection and override _generate
    model = MLXModel("fake-model", model_data=MagicMock(), tokenizer=MagicMock())
    model._generate = lambda messages, tools, settings, stream: '<tool_call>{"name": "read", "arguments": {"path": "test.py"}}</tool_call>'

    messages = [ModelRequest(parts=[UserPromptPart(content="Read test.py")], kind="request")]
    params = ModelRequestParameters()

    response = await model.request(messages, None, params)

    assert len(response.parts) == 1
    assert isinstance(response.parts[0], ToolCallPart)
    assert response.parts[0].tool_name == "read"


@pytest.mark.asyncio
async def test_request_with_mixed_text_and_tools():
    """Test request() with both text and tool calls."""
    from punie.models.mlx import MLXModel
    from pydantic_ai.messages import (
        ModelRequest,
        TextPart,
        ToolCallPart,
        UserPromptPart,
    )
    from pydantic_ai.models import ModelRequestParameters

    # Create model with dependency injection and override _generate
    model = MLXModel("fake-model", model_data=MagicMock(), tokenizer=MagicMock())
    model._generate = lambda messages, tools, settings, stream: 'Let me read that<tool_call>{"name": "read", "arguments": {"path": "x.py"}}</tool_call>'

    messages = [ModelRequest(parts=[UserPromptPart(content="Help")], kind="request")]
    params = ModelRequestParameters()

    response = await model.request(messages, None, params)

    # Should have text part first, then tool call
    assert len(response.parts) == 2
    assert isinstance(response.parts[0], TextPart)
    assert response.parts[0].content == "Let me read that"
    assert isinstance(response.parts[1], ToolCallPart)
    assert response.parts[1].tool_name == "read"


# ============================================================================
# Factory integration tests
# ============================================================================


def test_factory_local_model_raises_import_error():
    """Test create_pydantic_agent(model='local') raises ImportError without mlx-lm."""
    from punie.agent.factory import create_pydantic_agent

    with pytest.raises(ImportError, match="mlx-lm is required"):
        create_pydantic_agent(model="local")


def test_factory_local_with_model_name_raises_import_error():
    """Test create_pydantic_agent(model='local:name') raises ImportError without mlx-lm."""
    from punie.agent.factory import create_pydantic_agent

    with pytest.raises(ImportError, match="mlx-lm is required"):
        create_pydantic_agent(model="local:custom-model-name")


def test_factory_local_model_name_parsing(monkeypatch):
    """Test that 'local:model-name' correctly extracts model name."""
    from punie.agent import factory
    from punie.models.mlx import MLXModel

    # Track what model name was passed to from_pretrained
    created_model_name = None

    def fake_from_pretrained(model_name, **kwargs):
        nonlocal created_model_name
        created_model_name = model_name
        # Return a real instance with dependency injection (no mlx-lm needed!)
        return MLXModel(model_name, model_data=MagicMock(), tokenizer=MagicMock())

    # Patch from_pretrained classmethod
    monkeypatch.setattr(MLXModel, "from_pretrained", fake_from_pretrained)

    _ = factory._create_local_model("custom-model-name")
    assert created_model_name == "custom-model-name"


def test_factory_local_default_model_name(monkeypatch):
    """Test that 'local' uses default Qwen model."""
    from punie.agent import factory
    from punie.models.mlx import MLXModel

    # Track what model name was passed to from_pretrained
    created_model_name = None

    def fake_from_pretrained(model_name, **kwargs):
        nonlocal created_model_name
        created_model_name = model_name
        # Return a real instance with dependency injection (no mlx-lm needed!)
        return MLXModel(model_name, model_data=MagicMock(), tokenizer=MagicMock())

    # Patch from_pretrained classmethod
    monkeypatch.setattr(MLXModel, "from_pretrained", fake_from_pretrained)

    _ = factory._create_local_model()
    assert created_model_name == "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
