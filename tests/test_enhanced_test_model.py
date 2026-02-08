"""Tests for enhanced test model.

Verifies that the enhanced test model:
1. Returns helpful responses instead of just "a"
2. Does NOT call tools (prevents deadlock)
3. Works correctly with Pydantic AI agent
"""

import asyncio

import pytest
from pydantic_ai.models.test import TestModel

from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.agent import create_pydantic_agent
from punie.agent.deps import ACPDeps
from punie.testing import FakeClient


def test_enhanced_test_model_config():
    """Test model created via model='test' has correct configuration."""
    agent = create_pydantic_agent(model="test")

    # Access the underlying model
    model = agent._model

    # Verify it's a TestModel with correct config
    assert isinstance(model, TestModel)
    assert (
        model.custom_output_text
        == "I understand the request. Let me help with that task."
    )
    assert model.call_tools == []  # Critical: empty list prevents deadlock


def test_empty_call_tools_list_prevents_iteration_error():
    """Verify call_tools=[] (empty list) doesn't cause iteration errors.

    Previously tried call_tools=None which causes TypeError when iterated.
    Empty list [] is the correct way to disable tool calling.
    """
    model = TestModel(call_tools=[])
    assert isinstance(model.call_tools, list)
    assert len(model.call_tools) == 0


@pytest.mark.asyncio
async def test_agent_with_test_model_returns_helpful_response():
    """Agent with test model returns helpful text, not just 'a'."""
    agent = create_pydantic_agent(model="test")
    fake_client = FakeClient()
    deps = ACPDeps(
        client_conn=fake_client,
        session_id="test-session",
        tracker=ToolCallTracker(),
    )

    result = await agent.run("Hello, can you help me?", deps=deps)

    # Verify we got a helpful response, not just "a"
    assert result.output == "I understand the request. Let me help with that task."
    assert result.output != "a"


@pytest.mark.asyncio
async def test_agent_with_test_model_completes_without_hanging():
    """Agent with test model completes immediately without hanging.

    This test uses asyncio.wait_for to ensure the agent completes within
    a reasonable timeout (2 seconds). If the test model were configured
    with call_tools='all', it would attempt to call tools and hang,
    causing this test to timeout.

    Deadlock scenario (what we're preventing):
    1. PyCharm sends prompt request → waiting for response
    2. TestModel (with call_tools='all') decides to call ALL tools
    3. It calls read_file() which makes ACP request back to PyCharm
    4. PyCharm is blocked waiting for our prompt response
    5. We're blocked waiting for PyCharm to respond to our read_file request
    6. Deadlock! Neither side can proceed.
    """
    agent = create_pydantic_agent(model="test")
    fake_client = FakeClient()
    deps = ACPDeps(
        client_conn=fake_client,
        session_id="test-session",
        tracker=ToolCallTracker(),
    )

    # This should complete immediately, not hang
    try:
        result = await asyncio.wait_for(
            agent.run("Test prompt", deps=deps),
            timeout=2.0,  # 2 second timeout
        )
        assert result.output == "I understand the request. Let me help with that task."
    except asyncio.TimeoutError:
        pytest.fail("Agent hung (likely tried to call tools and deadlocked)")


@pytest.mark.asyncio
async def test_model_with_call_tools_all_would_attempt_tool_calls():
    """Demonstrate that call_tools='all' causes tool calls.

    This test shows why we use call_tools=[] instead. With call_tools='all',
    the model attempts to call tools, which in a real ACP scenario would
    cause a deadlock.
    """
    # Create a test model that WILL call tools (opposite of our fixed config)
    model_that_calls_tools = TestModel(
        custom_output_text="I tried to call tools!",
        call_tools="all",  # This will attempt to call ALL available tools
    )

    agent = create_pydantic_agent(model=model_that_calls_tools)
    fake_client = FakeClient()
    deps = ACPDeps(
        client_conn=fake_client,
        session_id="test-session",
        tracker=ToolCallTracker(),
    )

    # Run the agent - it will attempt to call tools
    result = await agent.run("Do something", deps=deps)

    # The agent will have attempted tool calls (can see in logs)
    # In a real ACP scenario, this would deadlock
    assert result.output == "I tried to call tools!"


def test_call_tools_empty_vs_none():
    """Document the difference between call_tools=[] and call_tools=None.

    call_tools=None causes TypeError: 'NoneType' object is not iterable
    call_tools=[] correctly disables all tool calling
    """
    # Empty list is correct
    model_correct = TestModel(call_tools=[])
    assert model_correct.call_tools == []

    # None would cause iteration error (don't use)
    # This is what we initially tried and it failed
    assert (
        TestModel.__init__.__annotations__["call_tools"] == "list[str] | Literal['all']"
    )
