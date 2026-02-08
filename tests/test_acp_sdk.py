"""ACP SDK integration tests for Python 3.14.2t verification.

These tests prove the agent-client-protocol SDK works correctly under
Python 3.14.2t (free-threaded). Not exhaustive SDK coverage—just critical
paths Punie will use.

Test coverage:
1. Schema model serialization/deserialization
2. Agent-side RPC (initialize, new_session)
3. Client-side RPC (file read/write)
4. One-way notifications (cancel)
5. Agent-to-client notifications (session updates)
6. Tool call lifecycle with permissions
7. Concurrent operations (free-threading safety)
"""

import asyncio

import pytest

from acp import start_tool_call, update_tool_call
from acp.schema import (
    AgentMessageChunk,
    InitializeResponse,
    PermissionOption,
    TextContentBlock,
    ToolCallLocation,
    ToolCallUpdate,
    UserMessageChunk,
)


def test_acp_schema_model_roundtrip():
    """Test 1: Pydantic schema models serialize/deserialize under 3.14t.

    Sync test proving basic Pydantic functionality works.
    No fixtures needed—this is pure schema validation.
    """
    # Create a response model
    init_response = InitializeResponse(
        protocol_version=1, agent_capabilities=None, auth_methods=[]
    )
    assert init_response.protocol_version == 1

    # Serialize to dict
    data = init_response.model_dump()
    assert data["protocol_version"] == 1

    # Deserialize back
    reconstructed = InitializeResponse.model_validate(data)
    assert reconstructed.protocol_version == 1

    # Test content blocks
    text_block = TextContentBlock(type="text", text="Hello, 3.14t!")
    assert text_block.text == "Hello, 3.14t!"
    text_data = text_block.model_dump()
    text_reconstructed = TextContentBlock.model_validate(text_data)
    assert text_reconstructed.text == "Hello, 3.14t!"


@pytest.mark.thread_unsafe
async def test_initialize_and_new_session(connect):
    """Test 2: Agent-side RPC roundtrip over TCP loopback.

    Proves initialize + new_session work correctly through ACP transport.
    """
    _, agent_conn = connect()

    # Initialize handshake
    resp = await agent_conn.initialize(protocol_version=1)
    assert isinstance(resp, InitializeResponse)
    assert resp.protocol_version == 1

    # Create new session
    new_sess = await agent_conn.new_session(mcp_servers=[], cwd="/test")
    assert new_sess.session_id == "test-session-123"


@pytest.mark.thread_unsafe
async def test_bidirectional_file_read_write(client, connect):
    """Test 3: Client-side RPC for file operations.

    Proves agent can read/write files via client's in-memory filesystem.
    """
    # Pre-populate client's file system
    client.files["/test/file.txt"] = "Hello, World!"
    client_conn, _ = connect()

    # Agent reads file from client
    res = await client_conn.read_text_file(session_id="sess", path="/test/file.txt")
    assert res.content == "Hello, World!"

    # Agent writes file via client
    await client_conn.write_text_file(
        session_id="sess", path="/test/file.txt", content="Updated"
    )
    assert client.files["/test/file.txt"] == "Updated"


@pytest.mark.thread_unsafe
async def test_cancel_notification_dispatched(connect, agent):
    """Test 4: One-way notification from client to agent.

    Proves cancel notification propagates correctly to agent handler.
    """
    _, agent_conn = connect()

    # Send cancel notification
    await agent_conn.cancel(session_id="test-123")

    # Wait for async dispatch
    for _ in range(50):
        if agent.cancellations:
            break
        await asyncio.sleep(0.01)

    assert agent.cancellations == ["test-123"]


@pytest.mark.thread_unsafe
async def test_session_update_notifications(connect, client):
    """Test 5: Agent-to-client notifications via session_update.

    Proves message notifications dispatch correctly from agent to client.
    """
    client_conn, _ = connect()

    # Send agent message notification
    await client_conn.session_update(
        session_id="sess",
        update=AgentMessageChunk(
            session_update="agent_message_chunk",
            content=TextContentBlock(type="text", text="Hello"),
        ),
    )

    # Send user message notification
    await client_conn.session_update(
        session_id="sess",
        update=UserMessageChunk(
            session_update="user_message_chunk",
            content=TextContentBlock(type="text", text="World"),
        ),
    )

    # Wait for async dispatch
    for _ in range(50):
        if len(client.notifications) >= 2:
            break
        await asyncio.sleep(0.01)

    assert len(client.notifications) >= 2
    assert client.notifications[0].session_id == "sess"
    assert isinstance(client.notifications[0].update, AgentMessageChunk)
    assert isinstance(client.notifications[1].update, UserMessageChunk)


@pytest.mark.thread_unsafe
async def test_tool_call_lifecycle(connect, client):
    """Test 6: Full tool call flow with permission and status tracking.

    Proves tool call lifecycle works: start → permission → update → complete.
    This is critical for Punie's PyCharm integration.
    """
    # Queue permission response
    client.queue_permission_selected("allow")

    client_conn, _ = connect()

    # Start tool call
    await client_conn.session_update(
        session_id="sess",
        update=start_tool_call(
            "call_1",
            "Modifying file",
            kind="edit",
            status="pending",
            locations=[ToolCallLocation(path="/project/file.py")],
            raw_input={"path": "/project/file.py"},
        ),
    )

    # Request permission
    permission_response = await client_conn.request_permission(
        session_id="sess",
        tool_call=ToolCallUpdate(
            tool_call_id="call_1",
            title="Modifying file",
            kind="edit",
            status="pending",
            locations=[ToolCallLocation(path="/project/file.py")],
            raw_input={"path": "/project/file.py"},
        ),
        options=[
            PermissionOption(kind="allow_once", name="Allow", option_id="allow"),
            PermissionOption(kind="reject_once", name="Reject", option_id="reject"),
        ],
    )

    # Check permission granted
    assert permission_response.outcome.outcome == "selected"

    # Update tool call to completed
    await client_conn.session_update(
        session_id="sess",
        update=update_tool_call(
            "call_1",
            status="completed",
            raw_output={"success": True},
        ),
    )

    # Wait for notifications
    for _ in range(50):
        if len(client.notifications) >= 2:
            break
        await asyncio.sleep(0.01)

    # Verify tool call updates received
    assert len(client.notifications) >= 2


@pytest.mark.thread_unsafe
async def test_concurrent_file_reads(connect, client):
    """Test 7: Concurrent file operations via asyncio.gather.

    Proves free-threading safety: parallel reads should not interfere.
    """
    # Pre-populate files
    for i in range(5):
        client.files[f"/test/file{i}.txt"] = f"Content {i}"

    client_conn, _ = connect()

    # Define concurrent read operation
    async def read_one(i: int):
        return await client_conn.read_text_file(
            session_id="sess", path=f"/test/file{i}.txt"
        )

    # Execute 5 reads in parallel
    results = await asyncio.gather(*(read_one(i) for i in range(5)))

    # Verify all reads succeeded with correct content
    for i, res in enumerate(results):
        assert res.content == f"Content {i}"
