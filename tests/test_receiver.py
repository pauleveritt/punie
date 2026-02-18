"""Tests for punie.client.receiver — shared message receive loop."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from punie.client.receiver import receive_messages
from punie.testing.fakes import FakeWebSocket


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_session_update(update_type: str, content: dict[str, Any] | None = None) -> dict:
    """Build a session/update notification."""
    return {
        "method": "session/update",
        "params": {
            "update": {
                "sessionUpdate": update_type,
                **(content or {}),
            }
        },
    }


def make_response(request_id: str, result: dict | None = None) -> dict:
    """Build a final JSON-RPC response."""
    return {"id": request_id, "result": result or {}}


def make_error_response(request_id: str, message: str, code: int = -32603) -> dict:
    """Build an error JSON-RPC response."""
    return {"id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# Normal flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_receive_messages_normal_flow():
    """Should return result dict when matching response arrives."""
    fake = FakeWebSocket(responses=[
        make_session_update("agent_message_chunk", {"content": {"type": "text", "text": "Hi"}}),
        make_response("req-1", {"status": "done"}),
    ])

    callbacks: list[tuple[str, dict]] = []

    def on_notification(update_type: str, update: dict) -> None:
        callbacks.append((update_type, update))

    result = await receive_messages(fake, request_id="req-1", on_notification=on_notification)

    assert result == {"status": "done"}
    assert len(callbacks) == 1
    assert callbacks[0][0] == "agent_message_chunk"


@pytest.mark.asyncio
async def test_receive_messages_multiple_notifications():
    """Should dispatch all notifications before final response."""
    fake = FakeWebSocket(responses=[
        make_session_update("agent_message_chunk", {"content": {"type": "text", "text": "Hello "}}),
        make_session_update("agent_message_chunk", {"content": {"type": "text", "text": "world"}}),
        make_session_update("tool_call", {"tool_call_id": "tc-1", "title": "Read"}),
        make_response("req-2", {}),
    ])

    notifications: list[str] = []

    def on_notification(update_type: str, update: dict) -> None:
        notifications.append(update_type)

    result = await receive_messages(fake, request_id="req-2", on_notification=on_notification)

    assert result == {}
    assert notifications == ["agent_message_chunk", "agent_message_chunk", "tool_call"]


@pytest.mark.asyncio
async def test_receive_messages_no_callback():
    """Should work without a notification callback (notifications silently ignored)."""
    fake = FakeWebSocket(responses=[
        make_session_update("agent_message_chunk"),
        make_response("req-3", {"done": True}),
    ])

    result = await receive_messages(fake, request_id="req-3")
    assert result == {"done": True}


@pytest.mark.asyncio
async def test_receive_messages_ignores_other_notifications():
    """Should ignore non-session_update notifications."""
    fake = FakeWebSocket(responses=[
        {"method": "some_other_notification", "params": {}},
        make_response("req-4", {}),
    ])

    callbacks: list[str] = []

    def on_notification(update_type: str, update: dict) -> None:
        callbacks.append(update_type)

    result = await receive_messages(fake, request_id="req-4", on_notification=on_notification)

    assert result == {}
    assert callbacks == []  # other notifications not dispatched


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_receive_messages_server_error():
    """Should raise RuntimeError when server returns error response."""
    fake = FakeWebSocket(responses=[
        make_error_response("req-5", "Internal error"),
    ])

    with pytest.raises(RuntimeError, match="failed"):
        await receive_messages(fake, request_id="req-5")


@pytest.mark.asyncio
async def test_receive_messages_connection_close():
    """Should raise ConnectionError when WebSocket closes unexpectedly."""
    fake = FakeWebSocket(responses=[{"__close__": True}])

    with pytest.raises(ConnectionError, match="Server disconnected"):
        await receive_messages(fake, request_id="req-6")


@pytest.mark.asyncio
async def test_receive_messages_exhausted_responses():
    """Should raise ConnectionError when no more responses available."""
    fake = FakeWebSocket(responses=[])

    with pytest.raises(ConnectionError, match="Server disconnected"):
        await receive_messages(fake, request_id="req-7")


@pytest.mark.asyncio
async def test_receive_messages_malformed_json_skipped():
    """Should skip malformed JSON and continue processing."""
    # FakeWebSocket returns valid JSON, but we can test by overriding recv
    class BadJsonWebSocket:
        def __init__(self):
            self._count = 0

        async def send(self, data):
            pass

        async def recv(self):
            self._count += 1
            if self._count == 1:
                return "not valid json {"
            return json.dumps(make_response("req-8", {"ok": True}))

    result = await receive_messages(BadJsonWebSocket(), request_id="req-8")
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_receive_messages_missing_params_update():
    """Should skip session_update notifications missing params.update field."""
    fake = FakeWebSocket(responses=[
        {"method": "session/update", "params": {}},  # missing update
        make_response("req-9", {}),
    ])

    callbacks: list[str] = []

    def on_notification(update_type: str, update: dict) -> None:
        callbacks.append(update_type)

    result = await receive_messages(fake, request_id="req-9", on_notification=on_notification)
    assert result == {}
    assert callbacks == []  # notification without update skipped


@pytest.mark.asyncio
async def test_receive_messages_callback_exception_does_not_crash():
    """Exceptions in notification callback should be caught, not propagated."""
    fake = FakeWebSocket(responses=[
        make_session_update("agent_message_chunk"),
        make_response("req-10", {}),
    ])

    def bad_callback(update_type: str, update: dict) -> None:
        raise ValueError("callback error!")

    # Should not raise
    result = await receive_messages(
        fake, request_id="req-10", on_notification=bad_callback
    )
    assert result == {}


@pytest.mark.asyncio
async def test_receive_messages_per_message_timeout():
    """Should raise RuntimeError when per-message timeout exceeded."""
    class SlowWebSocket:
        async def send(self, data):
            pass

        async def recv(self):
            await asyncio.sleep(10)  # longer than test timeout

    with pytest.raises(RuntimeError, match="No response from server"):
        await receive_messages(
            SlowWebSocket(), request_id="req-slow", timeout=0.05
        )


@pytest.mark.asyncio
async def test_receive_messages_aggregate_timeout():
    """Should raise RuntimeError when aggregate deadline exceeded."""
    class DrippingWebSocket:
        def __init__(self):
            self._count = 0

        async def send(self, data):
            pass

        async def recv(self):
            self._count += 1
            await asyncio.sleep(0.05)
            return json.dumps(make_session_update("ping"))

    with pytest.raises(RuntimeError, match="[Tt]imeout|No response"):
        await receive_messages(
            DrippingWebSocket(),
            request_id="req-agg",
            timeout=1.0,
            aggregate_timeout=0.1,
        )


# ---------------------------------------------------------------------------
# Persistent mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_receive_messages_persistent_mode_dispatches_all():
    """In persistent mode (no request_id), should dispatch notifications until close."""
    fake = FakeWebSocket(responses=[
        make_session_update("chunk_1"),
        make_session_update("chunk_2"),
        {"__close__": True},
    ])

    collected: list[str] = []

    def on_notification(update_type: str, update: dict) -> None:
        collected.append(update_type)

    with pytest.raises(ConnectionError):
        await receive_messages(fake, request_id=None, on_notification=on_notification)

    assert collected == ["chunk_1", "chunk_2"]
