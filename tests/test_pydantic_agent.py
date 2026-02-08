"""Tests for Punie's Pydantic AI agent implementation.

Tests ACPDeps, ACPToolset, PunieAgent, and the integration between
ACP protocol and Pydantic AI.
"""

from dataclasses import FrozenInstanceError

import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import UsageLimits

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
    """Pydantic AI agent should have toolsets configured."""
    pydantic_agent = create_pydantic_agent(model="test")

    # Agent should have at least our custom toolset attached
    assert len(pydantic_agent.toolsets) >= 1


async def test_fake_client_terminal_methods():
    """FakeClient should implement terminal methods with in-memory state."""
    fake_client = FakeClient()

    # Test create_terminal
    response = await fake_client.create_terminal(
        command="echo", session_id="test", args=["hello"]
    )
    assert response.terminal_id == "term-0"
    assert "term-0" in fake_client.terminals

    # Test terminal_output (default empty)
    output = await fake_client.terminal_output(session_id="test", terminal_id="term-0")
    assert output.output == ""

    # Test wait_for_terminal_exit (default 0)
    exit_response = await fake_client.wait_for_terminal_exit(
        session_id="test", terminal_id="term-0"
    )
    assert exit_response.exit_code == 0

    # Test release_terminal
    await fake_client.release_terminal(session_id="test", terminal_id="term-0")
    assert "term-0" not in fake_client.terminals


async def test_fake_client_queue_terminal():
    """FakeClient.queue_terminal should pre-configure terminal output."""
    fake_client = FakeClient()

    # Queue a terminal with specific output and exit code
    terminal_id = fake_client.queue_terminal(
        command="pytest", output="All tests passed", exit_code=0, args=["--verbose"]
    )

    assert terminal_id == "term-0"
    assert terminal_id in fake_client.terminals

    # Verify we can retrieve the configured values
    output = await fake_client.terminal_output(
        session_id="test", terminal_id=terminal_id
    )
    assert output.output == "All tests passed"

    exit_response = await fake_client.wait_for_terminal_exit(
        session_id="test", terminal_id=terminal_id
    )
    assert exit_response.exit_code == 0


async def test_fake_client_kill_terminal():
    """FakeClient.kill_terminal should remove terminal from state."""
    fake_client = FakeClient()

    # Create terminal
    response = await fake_client.create_terminal(
        command="long-running", session_id="test"
    )
    terminal_id = response.terminal_id
    assert terminal_id in fake_client.terminals

    # Kill it
    await fake_client.kill_terminal(session_id="test", terminal_id=terminal_id)
    assert terminal_id not in fake_client.terminals


def test_toolset_has_all_seven_tools():
    """create_toolset() should return toolset with all 7 tools."""
    toolset = create_toolset()

    # toolset.tools is a dict mapping tool names to Tool objects
    tool_names = set(toolset.tools.keys())

    # Verify all 7 tools are present
    expected_tools = {
        "read_file",
        "write_file",
        "run_command",
        "get_terminal_output",
        "release_terminal",
        "wait_for_terminal_exit",
        "kill_terminal",
    }
    assert tool_names == expected_tools


def test_factory_uses_instructions():
    """create_pydantic_agent should use instructions= instead of system_prompt=."""
    agent = create_pydantic_agent(model="test")

    # Agent._instructions is a list[str] internally
    assert agent._instructions
    assert len(agent._instructions) > 0
    # Instructions should mention "Punie"
    instructions_text = "".join(str(i) for i in agent._instructions)
    assert "Punie" in instructions_text


def test_factory_sets_model_settings():
    """create_pydantic_agent should set ModelSettings for deterministic coding."""
    agent = create_pydantic_agent(model="test")

    # agent.model_settings is a property that returns dict
    settings = agent.model_settings
    assert settings is not None
    assert settings["temperature"] == 0.0
    assert settings["max_tokens"] == 4096


def test_factory_sets_retries():
    """create_pydantic_agent should configure retry policies."""
    agent = create_pydantic_agent(model="test")

    # These are internal attributes, tested with awareness they may change
    assert agent._max_tool_retries == 3
    assert agent._max_result_retries == 2


def test_factory_has_output_validator():
    """create_pydantic_agent should register an output validator."""
    agent = create_pydantic_agent(model="test")

    # _output_validators is a list of OutputValidator
    assert len(agent._output_validators) == 1


async def test_output_validator_accepts_valid():
    """Output validator should accept non-empty responses."""
    # Create agent with TestModel that returns valid output
    agent = create_pydantic_agent(model=TestModel(custom_output_text="Valid response"))

    # Create fake dependencies
    fake_client = FakeClient()
    deps = ACPDeps(
        client_conn=fake_client,
        session_id="test-session",
        tracker=ToolCallTracker(),
    )

    # Should succeed without raising
    result = await agent.run("test prompt", deps=deps)
    assert result.output == "Valid response"


async def test_output_validator_rejects_empty():
    """Output validator should reject empty responses and exhaust retries."""
    # Create agent with TestModel that returns empty output
    agent = create_pydantic_agent(model=TestModel(custom_output_text=""))

    # Create fake dependencies
    fake_client = FakeClient()
    deps = ACPDeps(
        client_conn=fake_client,
        session_id="test-session",
        tracker=ToolCallTracker(),
    )

    # Should exhaust retries and raise UnexpectedModelBehavior
    with pytest.raises(UnexpectedModelBehavior):
        await agent.run("test prompt", deps=deps)


async def test_adapter_handles_agent_error():
    """PunieAgent should catch agent errors and send via session_update."""
    # Create agent that will fail validation (empty output)
    pydantic_agent = create_pydantic_agent(model=TestModel(custom_output_text=""))
    adapter = PunieAgent(pydantic_agent, name="test-agent")

    # Connect to fake client
    fake_client = FakeClient()
    adapter.on_connect(fake_client)

    # Prompt should not raise, should return PromptResponse
    response = await adapter.prompt(
        prompt=[text_block("test")],
        session_id="test-session",
    )

    assert response.stop_reason == "end_turn"

    # Should have sent error message via session_update
    assert len(fake_client.notifications) > 0
    # Last notification should contain error text
    last_notification = fake_client.notifications[-1]
    assert last_notification.update.session_update == "agent_message_chunk"


def test_adapter_accepts_usage_limits():
    """PunieAgent should accept usage_limits parameter."""
    pydantic_agent = create_pydantic_agent(model="test")

    # Should accept usage_limits without error
    limits = UsageLimits(request_limit=10, total_tokens_limit=1000)
    adapter = PunieAgent(pydantic_agent, name="test-agent", usage_limits=limits)

    # Should store limits
    assert adapter._usage_limits is limits
