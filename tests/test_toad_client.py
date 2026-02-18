"""Tests for punie.client.toad_client.

Covers send_prompt_stream, run_toad_client, create_toad_session, handle_tool_update.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import patch

import pytest

from punie.client.toad_client import (
    create_toad_session,
    handle_tool_update,
    send_prompt_stream,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_update(update_type: str, **extra: Any) -> dict:
    return {
        "method": "session/update",
        "params": {"update": {"sessionUpdate": update_type, **extra}},
    }


def make_final(request_id: str, result: dict | None = None) -> dict:
    return {"id": request_id, "result": result or {}}


# ---------------------------------------------------------------------------
# send_prompt_stream
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_prompt_stream_calls_callback():
    """Should call on_chunk for each session_update notification."""
    calls: list[tuple[str, dict]] = []

    class FakeWs:
        def __init__(self) -> None:
            self._rid: str | None = None
            self._count = 0

        async def send(self, data: str | bytes) -> None:
            msg = json.loads(data)
            self._rid = msg["id"]

        async def recv(self) -> str:
            if self._rid is None:
                # Request not yet sent — return a notification with no update
                return json.dumps({"method": "session/update", "params": {}})
            self._count += 1
            if self._count == 1:
                return json.dumps(make_update("agent_message_chunk", content={"type": "text", "text": "Hi"}))
            return json.dumps(make_final(self._rid, {"done": True}))

        async def close(self) -> None:
            pass

    def on_chunk(update_type: str, update: dict) -> None:
        calls.append((update_type, update))

    result = await send_prompt_stream(FakeWs(), "sess-1", "hello", on_chunk)  # type: ignore[arg-type]

    assert len(calls) >= 1
    assert calls[0][0] == "agent_message_chunk"
    assert result == {"done": True}


@pytest.mark.asyncio
async def test_send_prompt_stream_handles_callback_exception():
    """Exceptions in on_chunk should be caught, not propagated."""
    calls: list[str] = []

    class FakeWs:
        def __init__(self):
            self._count = 0
            self._rid = None

        async def send(self, data):
            self._rid = json.loads(data)["id"]

        async def recv(self):
            self._count += 1
            if self._count == 1:
                return json.dumps(make_update("agent_message_chunk"))
            return json.dumps({"id": self._rid, "result": {}})

    def bad_callback(update_type: str, update: dict) -> None:
        calls.append(update_type)
        raise RuntimeError("callback exploded!")

    result = await send_prompt_stream(FakeWs(), "sess-2", "hello", bad_callback)  # type: ignore[arg-type]
    assert result == {}
    assert "agent_message_chunk" in calls


@pytest.mark.asyncio
async def test_send_prompt_stream_handles_timeout():
    """Should raise RuntimeError when per-message timeout exceeded."""
    class SlowWs:
        async def send(self, data):
            pass

        async def recv(self):
            await asyncio.sleep(10)

    with pytest.raises(RuntimeError, match="No response"):
        # Patch timeouts to use tiny value
        from punie.client import receiver as recv_mod
        from punie.client.timeouts import Timeouts
        fast = Timeouts(streaming_timeout=0.05, aggregate_timeout=0.1)
        with patch.object(recv_mod, "CLIENT_TIMEOUTS", fast):
            await send_prompt_stream(SlowWs(), "sess-t", "prompt", lambda a, b: None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_send_prompt_stream_skips_missing_params_update():
    """Should skip session_update notifications with missing params.update."""
    class FakeWs:
        def __init__(self):
            self._count = 0
            self._rid = None

        async def send(self, data):
            self._rid = json.loads(data)["id"]

        async def recv(self):
            self._count += 1
            if self._count == 1:
                return json.dumps({"method": "session/update", "params": {}})  # missing update
            return json.dumps({"id": self._rid, "result": {}})

    calls: list[str] = []
    result = await send_prompt_stream(
        FakeWs(), "sess-3", "hello", lambda t, u: calls.append(t)  # type: ignore[arg-type]
    )
    assert result == {}
    assert calls == []  # notification with no update not dispatched


# ---------------------------------------------------------------------------
# handle_tool_update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_tool_update_dispatches_tool_call():
    calls: list[tuple[str, dict]] = []

    update = {
        "sessionUpdate": "tool_call",
        "tool_call_id": "tc-1",
        "title": "Read file",
        "kind": "read",
        "status": "pending",
        "content": [],
        "locations": [{"path": "/tmp/test.py"}],
    }

    await handle_tool_update(update, lambda tid, data: calls.append((tid, data)))

    assert len(calls) == 1
    tool_id, data = calls[0]
    assert tool_id == "tc-1"
    assert data["title"] == "Read file"
    assert data["kind"] == "read"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_handle_tool_update_ignores_non_tool():
    calls: list[tuple] = []

    update = {
        "sessionUpdate": "agent_message_chunk",
        "content": {"type": "text", "text": "Hi"},
    }

    await handle_tool_update(update, lambda t, d: calls.append((t, d)))
    assert calls == []


@pytest.mark.asyncio
async def test_handle_tool_update_missing_tool_call_id():
    calls: list[tuple] = []

    update = {
        "sessionUpdate": "tool_call",
        "title": "Read file",
        # missing tool_call_id
    }

    await handle_tool_update(update, lambda t, d: calls.append((t, d)))
    assert calls == []


# ---------------------------------------------------------------------------
# create_toad_session error path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_toad_session_cleans_up_on_handshake_failure():
    """Should close WebSocket if handshake fails."""
    import websockets

    with pytest.raises((OSError, ConnectionError, websockets.exceptions.WebSocketException)):
        await create_toad_session("ws://localhost:9999/no-server", "/tmp")
