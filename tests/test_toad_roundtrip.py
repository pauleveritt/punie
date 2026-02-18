"""Integration round-trip test for Punie WebSocket server.

Starts a real Punie server, connects a WebSocket client, sends a prompt,
and verifies that a streamed response arrives.

Requires a running model server (or test model).
Run with:
    uv run pytest -m integration tests/test_toad_roundtrip.py

These tests are excluded from the default `uv run pytest tests/` run.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

import pytest
import uvicorn

from punie.agent.adapter import PunieAgent
from punie.client.toad_client import create_toad_session, send_prompt_stream
from punie.http.app import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def punie_server():
    """Start a real Punie server on a random port.

    Yields the base WebSocket URL.
    """
    agent = PunieAgent(model="test", name="integration-test-agent")
    app = create_app(agent)

    config = uvicorn.Config(app, host="127.0.0.1", port=0, loop="asyncio", log_level="warning")
    server = uvicorn.Server(config)

    # Start server in background task
    server_task = asyncio.create_task(server.serve())
    # Wait for server to start
    for _ in range(50):
        if server.started:
            break
        await asyncio.sleep(0.1)
    else:
        server_task.cancel()
        pytest.fail("Server failed to start")

    # Get actual port
    port = server.servers[0].sockets[0].getsockname()[1]
    url = f"ws://127.0.0.1:{port}/ws"

    yield url

    # Shutdown
    server.should_exit = True
    await server_task


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_roundtrip_connect_and_prompt(punie_server: str):
    """Full round-trip: connect → handshake → prompt → streamed response.

    Verifies:
    - WebSocket connection and ACP handshake succeed
    - Prompt request is processed
    - At least one session_update notification arrives
    - Final response result dict is returned
    """
    server_url = punie_server
    received_updates: list[str] = []

    def on_chunk(update_type: str, update: dict) -> None:
        received_updates.append(update_type)

    # Connect
    websocket, session_id = await create_toad_session(server_url, str(Path.cwd()))

    try:
        # Send prompt
        result = await send_prompt_stream(
            websocket, session_id, "Say hello", on_chunk
        )

        # Verify we got a result (test model returns immediately)
        assert isinstance(result, dict)

        # Verify at least one update notification was dispatched
        assert len(received_updates) > 0, "Expected at least one session_update notification"

    finally:
        await websocket.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_roundtrip_session_id_in_response(punie_server: str):
    """Session ID should be a non-empty string."""
    websocket, session_id = await create_toad_session(punie_server, "/tmp")
    try:
        assert session_id
        assert isinstance(session_id, str)
        assert "session" in session_id.lower()
    finally:
        await websocket.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_roundtrip_multiple_prompts(punie_server: str):
    """Should handle multiple sequential prompts on same session."""
    websocket, session_id = await create_toad_session(punie_server, "/tmp")

    try:
        for i in range(3):
            received = []
            result = await send_prompt_stream(
                websocket, session_id, f"Prompt {i}", lambda t, u: received.append(t)
            )
            assert isinstance(result, dict)
    finally:
        await websocket.close()
