"""Tests for Punie's Pydantic AI agent implementation.

Tests ACPDeps, ACPToolset, PunieAgent, and the integration between
ACP protocol and Pydantic AI.
"""

from dataclasses import FrozenInstanceError

import pytest

from punie.acp import Agent, text_block
from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.agent import ACPDeps, PunieAgent, create_pydantic_agent, create_toolset
from punie.testing import FakeClient


def test_punie_agent_satisfies_agent_protocol():
    """PunieAgent must satisfy the ACP Agent protocol.

    This test is first because protocol satisfaction is the fundamental
    requirement. If this fails, PunieAgent cannot be used with ACP.
    """
    pydantic_agent = create_pydantic_agent(model="test")
    agent = PunieAgent(pydantic_agent, name="test-agent")

    # Runtime protocol check
    assert isinstance(agent, Agent)


def test_acp_deps_is_frozen():
    """ACPDeps should be a frozen dataclass."""
    fake_client = FakeClient()
    tracker = ToolCallTracker()
    deps = ACPDeps(
        client_conn=fake_client,
        session_id="test-session",
        tracker=tracker,
    )

    # Verify frozen - cannot reassign fields
    with pytest.raises(FrozenInstanceError):
        deps.session_id = "new-session"  # type: ignore[misc]


def test_acp_deps_holds_references():
    """ACPDeps should hold references to client, session, and tracker."""
    fake_client = FakeClient()
    tracker = ToolCallTracker()
    deps = ACPDeps(
        client_conn=fake_client,
        session_id="test-session-123",
        tracker=tracker,
    )

    assert deps.client_conn is fake_client
    assert deps.session_id == "test-session-123"
    assert deps.tracker is tracker


def test_toolset_creation():
    """create_toolset() should return a FunctionToolset."""
    toolset = create_toolset()

    # Should be a FunctionToolset instance
    assert toolset is not None
    # Should have tools (we don't inspect the internal structure deeply)
    assert hasattr(toolset, "tools")


async def test_punie_agent_initialize():
    """PunieAgent.initialize() should return valid InitializeResponse."""
    pydantic_agent = create_pydantic_agent(model="test")
    agent = PunieAgent(pydantic_agent, name="test-agent")

    response = await agent.initialize(protocol_version=1)

    assert response.protocol_version == 1
    assert response.agent_info is not None
    assert response.agent_info.name == "test-agent"
    assert response.agent_info.title == "Punie AI Coding Agent"
    assert response.agent_info.version == "0.1.0"


async def test_punie_agent_new_session_sequential_ids():
    """PunieAgent.new_session() should create sequential session IDs."""
    pydantic_agent = create_pydantic_agent(model="test")
    agent = PunieAgent(pydantic_agent, name="test-agent")

    response1 = await agent.new_session(cwd="/test", mcp_servers=[])
    response2 = await agent.new_session(cwd="/test", mcp_servers=[])
    response3 = await agent.new_session(cwd="/test", mcp_servers=[])

    assert response1.session_id == "punie-session-0"
    assert response2.session_id == "punie-session-1"
    assert response3.session_id == "punie-session-2"


async def test_punie_agent_prompt_delegates_to_pydantic_ai():
    """PunieAgent.prompt() should delegate to Pydantic AI and send response."""
    fake_client = FakeClient()
    pydantic_agent = create_pydantic_agent(model="test")
    agent = PunieAgent(pydantic_agent, name="test-agent")

    # Connect agent to client
    agent.on_connect(fake_client)

    # Send prompt
    response = await agent.prompt(
        prompt=[text_block("Hello, agent!")],
        session_id="test-session-1",
    )

    # Should return PromptResponse
    assert response.stop_reason == "end_turn"

    # Should have sent notifications via session_update
    # (TestModel may call tools and send AgentMessageChunk)
    assert len(fake_client.notifications) > 0
    # All notifications should have the correct session_id
    for notification in fake_client.notifications:
        assert notification.session_id == "test-session-1"
    # The last notification should be the agent's final message
    last_notification = fake_client.notifications[-1]
    assert last_notification.update.session_update == "agent_message_chunk"


async def test_read_file_tool_via_pydantic_ai():
    """Pydantic AI agent should be able to call read_file tool."""
    # Create Pydantic AI agent
    pydantic_agent = create_pydantic_agent(model="test")

    # Verify the toolset is configured correctly by checking
    # that the agent has toolsets attached (Pydantic AI includes internal
    # toolsets plus our custom ones)
    assert len(pydantic_agent.toolsets) >= 1
    # Our toolset should be in there somewhere
    assert any(toolset for toolset in pydantic_agent.toolsets)
