"""Integration tests for Phase 28 server/client separation.

Tests the full server/client architecture:
- run_http() runs server without stdio
- WebSocket clients can connect
- punie_session() performs handshake
- Multiple clients work simultaneously
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from punie.agent.adapter import PunieAgent
from punie.client.connection import connect_to_server, initialize_session, punie_session
from punie.http.app import create_app
from punie.http.runner import run_http


async def test_server_only_mode():
    """Test that server runs without stdio component."""
    # Create agent and app
    agent = PunieAgent(model="test", name="test-agent")
    app = create_app(agent)

    # Start server in background
    server_task = asyncio.create_task(
        run_http(agent, app, host="127.0.0.1", port=8001, log_level="critical"),
        name="test-server",
    )

    # Give server time to start
    await asyncio.sleep(0.5)

    try:
        # Connect and verify
        async with punie_session(
            "ws://127.0.0.1:8001/ws", str(Path.cwd())
        ) as (ws, session_id):
            assert session_id.startswith("punie-session-")
            assert ws is not None

    finally:
        # Clean up
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


async def test_connection_utilities():
    """Test low-level connection and handshake utilities."""
    # Create agent and app
    agent = PunieAgent(model="test", name="test-agent")
    app = create_app(agent)

    # Start server
    server_task = asyncio.create_task(
        run_http(agent, app, host="127.0.0.1", port=8002, log_level="critical"),
        name="test-server",
    )
    await asyncio.sleep(0.5)

    try:
        # Test connect_to_server
        websocket = await connect_to_server("ws://127.0.0.1:8002/ws")
        assert websocket is not None

        # Test initialize_session
        session_id = await initialize_session(websocket, str(Path.cwd()))
        assert session_id.startswith("punie-session-")

        # Clean up
        await websocket.close()

    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


async def test_multiple_concurrent_clients():
    """Test multiple clients connect simultaneously."""
    # Create agent and app
    agent = PunieAgent(model="test", name="test-agent")
    app = create_app(agent)

    # Start server
    server_task = asyncio.create_task(
        run_http(agent, app, host="127.0.0.1", port=8003, log_level="critical"),
        name="test-server",
    )
    await asyncio.sleep(0.5)

    try:
        # Create 3 concurrent clients
        async def client_session(client_id: int) -> str:
            async with punie_session(
                "ws://127.0.0.1:8003/ws", str(Path.cwd())
            ) as (ws, session_id):
                assert session_id.startswith("punie-session-")
                return f"client-{client_id}: {session_id}"

        # Run all clients concurrently
        results = await asyncio.gather(
            client_session(1), client_session(2), client_session(3)
        )

        # Verify all succeeded
        assert len(results) == 3
        assert all("punie-session-" in result for result in results)

    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    # Allow running tests directly for debugging
    pytest.main([__file__, "-v"])
