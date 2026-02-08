"""Tests for punie.testing fakes (FakeAgent, FakeClient, LoopbackServer).

These tests verify the test utilities work correctly and provide good coverage.
"""

import pytest

from punie.testing import FakeAgent, FakeClient


def test_fake_agent_default_values():
    """FakeAgent should have sensible defaults."""
    agent = FakeAgent()
    assert agent.session_id == "test-session-123"
    assert agent._protocol_version is None
    assert agent.prompts == []
    assert agent.cancellations == []


def test_fake_agent_custom_session_id():
    """FakeAgent should accept custom session ID."""
    agent = FakeAgent(session_id="custom-session")
    assert agent.session_id == "custom-session"


def test_fake_agent_custom_protocol_version():
    """FakeAgent should accept custom protocol version."""
    agent = FakeAgent(protocol_version=2)
    assert agent._protocol_version == 2


@pytest.mark.asyncio
async def test_fake_agent_initialize_echoes_version():
    """FakeAgent.initialize() should echo protocol version by default."""
    agent = FakeAgent()
    response = await agent.initialize(protocol_version=1)
    assert response.protocol_version == 1


@pytest.mark.asyncio
async def test_fake_agent_initialize_custom_version():
    """FakeAgent.initialize() should return custom version if configured."""
    agent = FakeAgent(protocol_version=3)
    response = await agent.initialize(protocol_version=1)
    assert response.protocol_version == 3  # Uses configured version


@pytest.mark.asyncio
async def test_fake_agent_new_session():
    """FakeAgent.new_session() should return configured session ID."""
    agent = FakeAgent(session_id="my-session")
    response = await agent.new_session(cwd="/test", mcp_servers=[])
    assert response.session_id == "my-session"


@pytest.mark.asyncio
async def test_fake_agent_load_session():
    """FakeAgent.load_session() should return response."""
    agent = FakeAgent()
    response = await agent.load_session(cwd="/test", mcp_servers=[], session_id="sess-1")
    assert response is not None


@pytest.mark.asyncio
async def test_fake_agent_list_sessions():
    """FakeAgent.list_sessions() should return empty list."""
    agent = FakeAgent()
    response = await agent.list_sessions()
    assert response.sessions == []
    assert response.next_cursor is None


@pytest.mark.asyncio
async def test_fake_agent_set_session_mode():
    """FakeAgent.set_session_mode() should return response."""
    agent = FakeAgent()
    response = await agent.set_session_mode(mode_id="chat", session_id="sess-1")
    assert response is not None


@pytest.mark.asyncio
async def test_fake_agent_set_session_model():
    """FakeAgent.set_session_model() should return response."""
    agent = FakeAgent()
    response = await agent.set_session_model(model_id="claude-4", session_id="sess-1")
    assert response is not None


@pytest.mark.asyncio
async def test_fake_agent_fork_session():
    """FakeAgent.fork_session() should return forked session ID."""
    agent = FakeAgent()
    response = await agent.fork_session(cwd="/test", session_id="original", mcp_servers=[])
    assert response.session_id == "original-fork"


@pytest.mark.asyncio
async def test_fake_agent_resume_session():
    """FakeAgent.resume_session() should return response."""
    agent = FakeAgent()
    response = await agent.resume_session(cwd="/test", session_id="sess-1", mcp_servers=[])
    assert response is not None


@pytest.mark.asyncio
async def test_fake_agent_authenticate():
    """FakeAgent.authenticate() should return response."""
    agent = FakeAgent()
    response = await agent.authenticate(method_id="oauth")
    assert response is not None


@pytest.mark.asyncio
async def test_fake_agent_prompt_records_request():
    """FakeAgent.prompt() should record requests and return response."""
    agent = FakeAgent()
    from punie.acp.schema import TextContentBlock

    response = await agent.prompt(
        prompt=[TextContentBlock(type="text", text="Hello")], session_id="sess-1"
    )
    assert response.stop_reason == "end_turn"
    assert len(agent.prompts) == 1
    assert agent.prompts[0].session_id == "sess-1"


@pytest.mark.asyncio
async def test_fake_agent_cancel_records_session():
    """FakeAgent.cancel() should record session ID."""
    agent = FakeAgent()
    await agent.cancel(session_id="sess-1")
    assert agent.cancellations == ["sess-1"]


@pytest.mark.asyncio
async def test_fake_agent_ext_method():
    """FakeAgent.ext_method() should handle custom methods."""
    agent = FakeAgent()
    result = await agent.ext_method("example.com/echo", {"data": "test"})
    assert result == {"echo": {"data": "test"}}
    assert agent.ext_calls == [("example.com/echo", {"data": "test"})]


@pytest.mark.asyncio
async def test_fake_agent_ext_method_not_found():
    """FakeAgent.ext_method() should raise for unknown methods."""
    agent = FakeAgent()
    from punie.acp import RequestError

    with pytest.raises(RequestError):
        await agent.ext_method("unknown.method", {})


@pytest.mark.asyncio
async def test_fake_agent_ext_notification():
    """FakeAgent.ext_notification() should record notifications."""
    agent = FakeAgent()
    await agent.ext_notification("example.com/notify", {"event": "test"})
    assert agent.ext_notes == [("example.com/notify", {"event": "test"})]


def test_fake_agent_on_connect():
    """FakeAgent.on_connect() should not raise."""
    agent = FakeAgent()
    agent.on_connect(None)  # Should be a no-op


def test_fake_client_default_values():
    """FakeClient should have sensible defaults."""
    client = FakeClient()
    assert client.files == {}
    assert client.default_file_content == "default content"
    assert client.permission_outcomes == []
    assert client.notifications == []


def test_fake_client_custom_files():
    """FakeClient should accept custom files dict."""
    client = FakeClient(files={"/test.txt": "content"})
    assert client.files == {"/test.txt": "content"}


def test_fake_client_custom_default_content():
    """FakeClient should accept custom default file content."""
    client = FakeClient(default_file_content="custom default")
    assert client.default_file_content == "custom default"


@pytest.mark.asyncio
async def test_fake_client_read_existing_file():
    """FakeClient.read_text_file() should return file content."""
    client = FakeClient(files={"/test.txt": "Hello, World!"})
    response = await client.read_text_file(path="/test.txt", session_id="sess-1")
    assert response.content == "Hello, World!"


@pytest.mark.asyncio
async def test_fake_client_read_missing_file():
    """FakeClient.read_text_file() should return default for missing files."""
    client = FakeClient(default_file_content="not found")
    response = await client.read_text_file(path="/missing.txt", session_id="sess-1")
    assert response.content == "not found"


@pytest.mark.asyncio
async def test_fake_client_write_file():
    """FakeClient.write_text_file() should update files dict."""
    client = FakeClient()
    response = await client.write_text_file(
        content="new content", path="/test.txt", session_id="sess-1"
    )
    assert response is not None
    assert client.files["/test.txt"] == "new content"


def test_fake_client_queue_permission_cancelled():
    """FakeClient.queue_permission_cancelled() should add to outcomes."""
    client = FakeClient()
    client.queue_permission_cancelled()
    assert len(client.permission_outcomes) == 1
    assert client.permission_outcomes[0].outcome.outcome == "cancelled"


def test_fake_client_queue_permission_selected():
    """FakeClient.queue_permission_selected() should add to outcomes."""
    client = FakeClient()
    client.queue_permission_selected("allow")
    assert len(client.permission_outcomes) == 1
    assert client.permission_outcomes[0].outcome.outcome == "selected"


@pytest.mark.asyncio
async def test_fake_client_request_permission_with_queue():
    """FakeClient.request_permission() should pop from queue."""
    client = FakeClient()
    client.queue_permission_selected("allow")

    from punie.acp.schema import PermissionOption, ToolCallUpdate

    response = await client.request_permission(
        options=[PermissionOption(kind="allow_once", name="Allow", option_id="allow")],
        session_id="sess-1",
        tool_call=ToolCallUpdate(
            tool_call_id="call-1", title="Test", kind="read", status="pending"
        ),
    )
    assert response.outcome.outcome == "selected"
    assert len(client.permission_outcomes) == 0  # Popped


@pytest.mark.asyncio
async def test_fake_client_request_permission_empty_queue():
    """FakeClient.request_permission() should return cancelled if queue empty."""
    client = FakeClient()

    from punie.acp.schema import PermissionOption, ToolCallUpdate

    response = await client.request_permission(
        options=[PermissionOption(kind="allow_once", name="Allow", option_id="allow")],
        session_id="sess-1",
        tool_call=ToolCallUpdate(
            tool_call_id="call-1", title="Test", kind="read", status="pending"
        ),
    )
    assert response.outcome.outcome == "cancelled"


@pytest.mark.asyncio
async def test_fake_client_session_update():
    """FakeClient.session_update() should record notifications."""
    client = FakeClient()
    from punie.acp.schema import AgentMessageChunk, TextContentBlock

    await client.session_update(
        session_id="sess-1",
        update=AgentMessageChunk(
            session_update="agent_message_chunk",
            content=TextContentBlock(type="text", text="Hello"),
        ),
    )
    assert len(client.notifications) == 1
    assert client.notifications[0].session_id == "sess-1"


@pytest.mark.asyncio
async def test_fake_client_ext_method():
    """FakeClient.ext_method() should handle custom methods."""
    client = FakeClient()
    result = await client.ext_method("example.com/ping", {"data": "test"})
    assert result == {"response": "pong", "params": {"data": "test"}}
    assert client.ext_calls == [("example.com/ping", {"data": "test"})]


@pytest.mark.asyncio
async def test_fake_client_ext_method_not_found():
    """FakeClient.ext_method() should raise for unknown methods."""
    client = FakeClient()
    from punie.acp import RequestError

    with pytest.raises(RequestError):
        await client.ext_method("unknown.method", {})


@pytest.mark.asyncio
async def test_fake_client_ext_notification():
    """FakeClient.ext_notification() should record notifications."""
    client = FakeClient()
    await client.ext_notification("example.com/notify", {"event": "test"})
    assert client.ext_notes == [("example.com/notify", {"event": "test"})]


def test_fake_client_on_connect():
    """FakeClient.on_connect() should store connection."""
    client = FakeClient()
    fake_conn = object()
    client.on_connect(fake_conn)
    assert client._agent_conn is fake_conn


@pytest.mark.asyncio
async def test_fake_client_create_terminal_not_implemented():
    """FakeClient.create_terminal() should raise NotImplementedError."""
    client = FakeClient()
    with pytest.raises(NotImplementedError):
        await client.create_terminal(command="ls", session_id="sess-1")


@pytest.mark.asyncio
async def test_fake_client_terminal_output_not_implemented():
    """FakeClient.terminal_output() should raise NotImplementedError."""
    client = FakeClient()
    with pytest.raises(NotImplementedError):
        await client.terminal_output(session_id="sess-1", terminal_id="term-1")


@pytest.mark.asyncio
async def test_fake_client_release_terminal_not_implemented():
    """FakeClient.release_terminal() should raise NotImplementedError."""
    client = FakeClient()
    with pytest.raises(NotImplementedError):
        await client.release_terminal(session_id="sess-1", terminal_id="term-1")


@pytest.mark.asyncio
async def test_fake_client_wait_for_terminal_exit_not_implemented():
    """FakeClient.wait_for_terminal_exit() should raise NotImplementedError."""
    client = FakeClient()
    with pytest.raises(NotImplementedError):
        await client.wait_for_terminal_exit(session_id="sess-1", terminal_id="term-1")


@pytest.mark.asyncio
async def test_fake_client_kill_terminal_not_implemented():
    """FakeClient.kill_terminal() should raise NotImplementedError."""
    client = FakeClient()
    with pytest.raises(NotImplementedError):
        await client.kill_terminal(session_id="sess-1", terminal_id="term-1")
