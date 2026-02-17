"""Integration tests for real-world scenarios.

Consolidates:
- test_stdio_integration.py (3 tests) - STDIO integration scenarios
- test_concurrency.py (1 test) - Concurrency edge cases

Total: 4 tests
"""

import asyncio
import sys
from pathlib import Path

import pytest

from punie.acp import PROTOCOL_VERSION, connect_to_agent, text_block
from punie.acp.schema import ClientCapabilities, Implementation
from punie.testing import FakeClient


# ============================================================================
# STDIO Integration Tests (3 tests)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_stdio_connection_to_agent():
    """Prove an ACP editor can connect to an agent over stdio.

    This test:
    1. Spawns a minimal agent as a subprocess (like PyCharm would)
    2. Connects a client to it via stdio pipes
    3. Performs the full ACP protocol handshake
    4. Verifies all protocol methods work over real stdio transport

    This is NOT an in-process TCP loopback - it's a real subprocess with stdio.
    """
    # Path to our minimal test agent
    agent_script = Path(__file__).parent / "fixtures" / "minimal_agent.py"
    assert agent_script.exists(), f"Test agent not found: {agent_script}"

    # Spawn agent subprocess with stdio pipes (like PyCharm would do)
    proc = await asyncio.create_subprocess_exec(
        sys.executable,  # Use same Python interpreter
        str(agent_script),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,  # Capture errors for debugging
    )

    assert proc.stdin is not None, "Agent subprocess stdin is None"
    assert proc.stdout is not None, "Agent subprocess stdout is None"

    try:
        # Connect client to agent via stdio (simulating PyCharm)
        client = FakeClient()
        conn = connect_to_agent(client, proc.stdin, proc.stdout)

        # Step 1: Initialize connection
        init_response = await conn.initialize(
            protocol_version=PROTOCOL_VERSION,
            client_capabilities=ClientCapabilities(),
            client_info=Implementation(
                name="test-editor",
                title="Test Editor",
                version="1.0.0",
            ),
        )

        assert init_response.protocol_version == PROTOCOL_VERSION
        assert init_response.agent_info is not None
        assert init_response.agent_info.name == "minimal-test-agent"

        # Step 2: Create a new session
        session = await conn.new_session(
            mcp_servers=[],
            cwd=".",
        )

        assert session.session_id is not None
        assert session.session_id.startswith("punie-session-")

        # Step 3: Send a prompt and get response
        response = await conn.prompt(
            session_id=session.session_id,
            prompt=[text_block("Hello, agent!")],
        )

        assert response.stop_reason == "end_turn"

        # Step 4: Clean shutdown
        await conn.close()

    finally:
        # Cleanup: terminate subprocess if still running
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()

        # Check for stderr output (useful for debugging failures)
        if proc.stderr:
            stderr_output = await proc.stderr.read()
            if stderr_output:
                print(f"Agent stderr: {stderr_output.decode()}", file=sys.stderr)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_stdio_connection_lifecycle():
    """Test complete connection lifecycle over stdio.

    This verifies:
    - Multiple sessions can be created
    - Session operations work over stdio
    - Connection cleanup is clean
    """
    agent_script = Path(__file__).parent / "fixtures" / "minimal_agent.py"

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(agent_script),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    assert proc.stdin is not None
    assert proc.stdout is not None

    try:
        client = FakeClient()
        conn = connect_to_agent(client, proc.stdin, proc.stdout)

        # Initialize
        await conn.initialize(
            protocol_version=PROTOCOL_VERSION,
            client_capabilities=ClientCapabilities(),
        )

        # Create first session
        session1 = await conn.new_session(mcp_servers=[], cwd=".")
        assert "punie-session-0" in session1.session_id

        # Create second session (proves subprocess maintains state)
        session2 = await conn.new_session(mcp_servers=[], cwd=".")
        assert "punie-session-1" in session2.session_id
        assert session1.session_id != session2.session_id

        # Test prompting both sessions to prove they work independently
        response1 = await conn.prompt(
            session_id=session1.session_id,
            prompt=[text_block("Test session 1")],
        )
        assert response1.stop_reason == "end_turn"

        response2 = await conn.prompt(
            session_id=session2.session_id,
            prompt=[text_block("Test session 2")],
        )
        assert response2.stop_reason == "end_turn"

        await conn.close()

    finally:
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_stdio_connection_notification_flow():
    """Test that notifications work over stdio transport.

    This verifies the agent can send notifications back to the client
    during prompt processing.
    """
    agent_script = Path(__file__).parent / "fixtures" / "minimal_agent.py"

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(agent_script),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    assert proc.stdin is not None
    assert proc.stdout is not None

    try:
        client = FakeClient()
        conn = connect_to_agent(client, proc.stdin, proc.stdout)

        await conn.initialize(
            protocol_version=PROTOCOL_VERSION,
            client_capabilities=ClientCapabilities(),
        )

        session = await conn.new_session(mcp_servers=[], cwd=".")

        # Send prompt - agent will send session_update notifications
        response = await conn.prompt(
            session_id=session.session_id,
            prompt=[text_block("Test prompt")],
        )

        assert response.stop_reason == "end_turn"

        # Verify client received notifications
        assert len(client.notifications) > 0
        assert client.notifications[0].session_id == session.session_id

        await conn.close()

    finally:
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()


# ============================================================================
# Concurrency Tests (1 test)
# ============================================================================


@pytest.mark.thread_unsafe
async def test_concurrent_file_reads(connect, client):
    """Test concurrent file operations via asyncio.gather.

    Tests async concurrency: parallel reads should not interfere.
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
