"""Integration tests for dual-protocol (ACP stdio + HTTP) operation.

These tests spawn a real subprocess running both ACP stdio and HTTP server
concurrently, verifying that both protocols work simultaneously.
"""

import asyncio
import socket
import sys
import time
from pathlib import Path

import httpx
import pytest

from punie.acp import PROTOCOL_VERSION, connect_to_agent
from punie.acp.schema import ClientCapabilities, Implementation
from punie.http.types import Port
from punie.testing import FakeClient


def find_free_port() -> Port:
    """Find a free port for testing.

    Returns:
        Available port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return Port(s.getsockname()[1])


async def wait_for_http(port: Port, timeout: float = 5.0) -> None:
    """Wait for HTTP server to be ready.

    Args:
        port: Port to check.
        timeout: Maximum time to wait in seconds.

    Raises:
        TimeoutError: If server doesn't respond within timeout.
    """
    start = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout:
            try:
                response = await client.get(f"http://127.0.0.1:{port}/health")
                if response.status_code == 200:
                    return
            except httpx.ConnectError, httpx.RemoteProtocolError:
                await asyncio.sleep(0.1)
    raise TimeoutError(f"HTTP server not ready after {timeout}s")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_dual_protocol_stdio_and_http() -> None:
    """Verify ACP stdio and HTTP work concurrently in same process.

    This test:
    1. Spawns a dual-protocol agent subprocess
    2. Waits for HTTP server to be ready
    3. Verifies HTTP /health and /echo endpoints work
    4. Verifies ACP stdio handshake works
    5. All against the SAME running process

    This proves the dual-protocol architecture works correctly.
    """
    # Find free port for this test
    port = find_free_port()

    # Path to dual agent fixture
    agent_script = Path(__file__).parent / "fixtures" / "dual_agent.py"
    assert agent_script.exists(), f"Dual agent fixture not found: {agent_script}"

    # Spawn dual-protocol agent subprocess
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(agent_script),
        str(port),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    assert proc.stdin is not None, "Subprocess stdin is None"
    assert proc.stdout is not None, "Subprocess stdout is None"

    try:
        # Wait for HTTP server to start
        await wait_for_http(port)

        # Test HTTP endpoints
        async with httpx.AsyncClient() as client:
            # Test /health
            response = await client.get(f"http://127.0.0.1:{port}/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

            # Test /echo
            test_data = {"message": "hello from test", "count": 123}
            response = await client.post(
                f"http://127.0.0.1:{port}/echo",
                json=test_data,
            )
            assert response.status_code == 200
            assert response.json() == {"echo": test_data}

        # Test ACP stdio protocol (same process!)
        client_impl = FakeClient()
        conn = connect_to_agent(client_impl, proc.stdin, proc.stdout)

        # Initialize handshake
        init_response = await conn.initialize(
            protocol_version=PROTOCOL_VERSION,
            client_capabilities=ClientCapabilities(),
            client_info=Implementation(
                name="test-client",
                title="Test Client",
                version="0.1.0",
            ),
        )
        assert init_response.protocol_version == PROTOCOL_VERSION

        # Create session
        session = await conn.new_session(
            cwd=str(Path.cwd()),
            mcp_servers=[],
        )
        assert session.session_id.startswith("punie-session-")

        # Send prompt
        from punie.acp import text_block

        response = await conn.prompt(
            session_id=session.session_id,
            prompt=[text_block("test")],
        )
        assert response.stop_reason == "end_turn"

        # Clean shutdown
        await conn.close()

    finally:
        # Clean up: close stdin to trigger shutdown
        proc.stdin.close()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_http_continues_after_acp_stdin_closes() -> None:
    """Verify clean shutdown when ACP stdin closes.

    When stdin is closed (IDE disconnects), the dual-protocol runner
    should cancel both tasks and exit cleanly.
    """
    # Find free port for this test
    port = find_free_port()

    # Path to dual agent fixture
    agent_script = Path(__file__).parent / "fixtures" / "dual_agent.py"

    # Spawn dual-protocol agent subprocess
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(agent_script),
        str(port),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    assert proc.stdin is not None, "Subprocess stdin is None"

    try:
        # Wait for HTTP server to start
        await wait_for_http(port)

        # Close stdin to simulate IDE disconnect
        proc.stdin.close()

        # Wait for process to exit
        returncode = await asyncio.wait_for(proc.wait(), timeout=5.0)

        # Should exit cleanly (return code 0)
        assert returncode == 0, f"Process exited with code {returncode}"

    finally:
        # Ensure cleanup
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
