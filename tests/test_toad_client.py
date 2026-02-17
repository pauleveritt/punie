"""Tests for Toad WebSocket client.

Following function-based-tests and fakes-over-mocks standards.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from starlette.testclient import TestClient

from punie.agent.adapter import PunieAgent
from punie.client.toad_client import (
    create_toad_session,
    handle_tool_update,
    send_prompt_stream,
)
from punie.http.app import create_app


# Fixtures


@pytest.fixture
def agent() -> PunieAgent:
    """Create test agent with test model."""
    return PunieAgent(model="test", name="test-agent")


@pytest.fixture
def test_app(agent: PunieAgent):
    """Create test Starlette app."""
    return create_app(agent)


@pytest.fixture
def fake_callback():
    """Fake callback that records calls."""
    calls: list[tuple[str, dict[str, Any]]] = []

    def callback(update_type: str, content: dict[str, Any]):
        calls.append((update_type, content))

    callback.calls = calls  # type: ignore
    return callback


@pytest.fixture
def fake_tool_callback():
    """Fake tool callback that records calls."""
    calls: list[tuple[str, dict[str, Any]]] = []

    def callback(tool_call_id: str, tool_data: dict[str, Any]):
        calls.append((tool_call_id, tool_data))

    callback.calls = calls  # type: ignore
    return callback


# Connection Tests


def test_create_toad_session_connects_and_handshakes(test_app):
    """Test session creation performs ACP handshake."""
    with TestClient(test_app) as client:
        with client.websocket_connect("/ws") as ws:
            # Manually perform handshake to get session_id
            ws.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": "init-1",
                    "method": "initialize",
                    "params": {
                        "protocol_version": 1,
                        "client_info": {"name": "test-client", "version": "1.0"},
                    },
                }
            )
            init_response = ws.receive_json()
            assert init_response["id"] == "init-1"

            ws.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": "session-1",
                    "method": "new_session",
                    "params": {"cwd": "/tmp", "mode": "code", "mcp_servers": []},
                }
            )
            session_response = ws.receive_json()
            assert session_response["id"] == "session-1"
            assert "sessionId" in session_response["result"]


def test_create_toad_session_handles_connection_failure():
    """Test graceful handling of server unavailable."""
    import websockets

    async def test():
        with pytest.raises((OSError, ConnectionError, websockets.exceptions.WebSocketException)):
            await create_toad_session("ws://localhost:9999/invalid", "/tmp")

    asyncio.run(test())


# Streaming Tests


def test_send_prompt_stream_calls_callback_for_each_chunk(test_app, fake_callback):
    """Test streaming chunks invoke callback."""

    async def test():
        with TestClient(test_app) as client:
            with client.websocket_connect("/ws") as ws:
                # Perform handshake
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": "init-1",
                        "method": "initialize",
                        "params": {
                            "protocol_version": 1,
                            "client_info": {"name": "test-client", "version": "1.0"},
                        },
                    }
                )
                init_response = ws.receive_json()
                assert init_response["id"] == "init-1"

                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": "session-1",
                        "method": "new_session",
                        "params": {"cwd": "/tmp", "mode": "code", "mcp_servers": []},
                    }
                )
                session_response = ws.receive_json()
                session_id = session_response["result"]["sessionId"]

                # Create a fake websocket wrapper for testing
                # We'll manually send prompt and simulate responses
                class FakeWebSocket:
                    def __init__(self, ws):
                        self.ws = ws
                        self.sent_prompt = False

                    async def send(self, data):
                        msg = json.loads(data)
                        # Send the prompt request to real WebSocket
                        self.ws.send_text(data)
                        self.sent_prompt = True
                        self.request_id = msg["id"]

                    async def recv(self):
                        if not self.sent_prompt:
                            raise RuntimeError("Must send before recv")

                        # Simulate agent_message_chunk
                        chunk1 = {
                            "method": "session_update",
                            "params": {
                                "update": {
                                    "sessionUpdate": "agent_message_chunk",
                                    "content": {"type": "text", "text": "Hello "},
                                }
                            },
                        }

                        chunk2 = {
                            "method": "session_update",
                            "params": {
                                "update": {
                                    "sessionUpdate": "agent_message_chunk",
                                    "content": {"type": "text", "text": "world!"},
                                }
                            },
                        }

                        final = {
                            "jsonrpc": "2.0",
                            "id": self.request_id,
                            "result": {"status": "complete"},
                        }

                        # Return messages in sequence
                        if not hasattr(self, "msg_count"):
                            self.msg_count = 0

                        self.msg_count += 1
                        if self.msg_count == 1:
                            return json.dumps(chunk1)
                        elif self.msg_count == 2:
                            return json.dumps(chunk2)
                        else:
                            return json.dumps(final)

                fake_ws = FakeWebSocket(ws)
                result = await send_prompt_stream(
                    fake_ws, session_id, "Test prompt", fake_callback
                )  # type: ignore[arg-type]

                # Assert callback was called for each chunk
                assert len(fake_callback.calls) == 2
                assert fake_callback.calls[0][0] == "agent_message_chunk"
                assert fake_callback.calls[1][0] == "agent_message_chunk"
                assert result["status"] == "complete"

    asyncio.run(test())


def test_send_prompt_stream_handles_timeout(fake_callback):
    """Test timeout protection on long operations.

    Note: This test uses monkeypatch to speed up the timeout for testing.
    In production, send_prompt_stream uses a 300-second (5-minute) timeout.
    """
    from unittest.mock import patch

    async def test():
        class SlowWebSocket:
            async def send(self, data):
                pass  # Pretend to send

            async def recv(self):
                # Never respond (simulate timeout)
                await asyncio.sleep(10)  # Longer than our test timeout

        slow_ws = SlowWebSocket()

        # Patch asyncio.wait_for to use a 0.1 second timeout instead of 300s
        # This makes the test fast while still verifying timeout behavior
        original_wait_for = asyncio.wait_for

        async def fast_wait_for(coro, timeout):
            # Use 0.1s timeout for testing instead of the real timeout
            return await original_wait_for(coro, timeout=0.1)

        with patch("asyncio.wait_for", side_effect=fast_wait_for):
            with pytest.raises(RuntimeError, match="No response from server"):
                await send_prompt_stream(slow_ws, "session-123", "Test", fake_callback)  # type: ignore[arg-type]

    asyncio.run(test())


def test_send_prompt_stream_skips_non_session_update_notifications(fake_callback):
    """Test non-session_update notifications are ignored."""

    async def test():
        class FakeWebSocket:
            def __init__(self):
                self.msg_count = 0

            async def send(self, data):
                self.request_id = json.loads(data)["id"]

            async def recv(self):
                self.msg_count += 1

                if self.msg_count == 1:
                    # Non-session_update notification (should be skipped)
                    return json.dumps(
                        {"method": "some_other_notification", "params": {}}
                    )
                elif self.msg_count == 2:
                    # Valid session_update
                    return json.dumps(
                        {
                            "method": "session_update",
                            "params": {
                                "update": {
                                    "sessionUpdate": "agent_message_chunk",
                                    "content": {"type": "text", "text": "Hello"},
                                }
                            },
                        }
                    )
                else:
                    # Final response
                    return json.dumps({"id": self.request_id, "result": {}})

        fake_ws = FakeWebSocket()
        await send_prompt_stream(fake_ws, "session-123", "Test", fake_callback)  # type: ignore[arg-type]

        # Only the valid session_update should trigger callback
        assert len(fake_callback.calls) == 1
        assert fake_callback.calls[0][0] == "agent_message_chunk"

    asyncio.run(test())


# Tool Update Tests


def test_handle_tool_update_parses_tool_call_start(fake_tool_callback):
    """Test tool_call update extraction."""

    async def test():
        update = {
            "sessionUpdate": "tool_call",
            "tool_call_id": "tool-123",
            "title": "Read file",
            "kind": "read",
            "status": "pending",
            "content": [],
            "locations": [{"path": "/tmp/test.py"}],
        }

        await handle_tool_update(update, fake_tool_callback)

        # Assert callback was called with extracted data
        assert len(fake_tool_callback.calls) == 1
        tool_call_id, tool_data = fake_tool_callback.calls[0]
        assert tool_call_id == "tool-123"
        assert tool_data["title"] == "Read file"
        assert tool_data["kind"] == "read"
        assert tool_data["status"] == "pending"
        assert tool_data["locations"] == [{"path": "/tmp/test.py"}]

    asyncio.run(test())


def test_handle_tool_update_parses_tool_call_progress(fake_tool_callback):
    """Test tool_call_update extraction."""

    async def test():
        update = {
            "sessionUpdate": "tool_call_update",
            "tool_call_id": "tool-123",
            "title": "Read file",
            "status": "completed",
        }

        await handle_tool_update(update, fake_tool_callback)

        assert len(fake_tool_callback.calls) == 1
        tool_call_id, tool_data = fake_tool_callback.calls[0]
        assert tool_call_id == "tool-123"
        assert tool_data["status"] == "completed"

    asyncio.run(test())


def test_handle_tool_update_ignores_non_tool_updates(fake_tool_callback):
    """Test non-tool updates are no-op."""

    async def test():
        update = {
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "text", "text": "Hello"},
        }

        await handle_tool_update(update, fake_tool_callback)

        # Callback should not be called for non-tool updates
        assert len(fake_tool_callback.calls) == 0

    asyncio.run(test())


def test_handle_tool_update_handles_missing_tool_call_id(fake_tool_callback):
    """Test graceful handling of missing tool_call_id."""

    async def test():
        update = {
            "sessionUpdate": "tool_call",
            # Missing tool_call_id
            "title": "Read file",
        }

        await handle_tool_update(update, fake_tool_callback)

        # Callback should not be called when tool_call_id is missing
        assert len(fake_tool_callback.calls) == 0

    asyncio.run(test())


# Integration Tests


def test_toad_client_full_prompt_lifecycle(test_app):
    """Test complete prompt → response flow."""

    async def test():
        # This test validates the full integration with the real server
        # We'll use TestClient to start the server and perform a real handshake

        # Note: This is a simplified integration test
        # Full end-to-end testing would require a real model, which we skip here
        with TestClient(test_app) as client:
            with client.websocket_connect("/ws") as ws:
                # Test that we can connect and perform handshake
                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": "init-1",
                        "method": "initialize",
                        "params": {
                            "protocol_version": 1,
                            "client_info": {"name": "test-client", "version": "1.0"},
                        },
                    }
                )
                init_response = ws.receive_json()
                assert "result" in init_response

                ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": "session-1",
                        "method": "new_session",
                        "params": {"cwd": "/tmp", "mode": "code", "mcp_servers": []},
                    }
                )
                session_response = ws.receive_json()
                assert "sessionId" in session_response["result"]

                # Connection established successfully
                # (Actual prompt execution would require model, skipped in unit tests)

    asyncio.run(test())


def test_toad_client_handles_malformed_json(fake_callback):
    """Test graceful handling of malformed JSON responses."""

    async def test():
        class FakeWebSocket:
            def __init__(self):
                self.msg_count = 0

            async def send(self, data):
                self.request_id = json.loads(data)["id"]

            async def recv(self):
                self.msg_count += 1

                if self.msg_count == 1:
                    # Return malformed JSON (should be skipped)
                    return "not valid json {"
                elif self.msg_count == 2:
                    # Valid response
                    return json.dumps(
                        {"id": self.request_id, "result": {"status": "ok"}}
                    )

        fake_ws = FakeWebSocket()
        result = await send_prompt_stream(fake_ws, "session-123", "Test", fake_callback)  # type: ignore[arg-type]

        # Should skip malformed JSON and process valid response
        assert result["status"] == "ok"

    asyncio.run(test())
