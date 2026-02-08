"""ACP RPC method tests.

Tests for agent-side and client-side RPC calls over ACP transport.
"""

import pytest

from punie.acp.schema import InitializeResponse


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
