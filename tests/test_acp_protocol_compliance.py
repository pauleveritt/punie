"""ACP protocol compliance tests.

Regression tests for the four bug classes uncovered during Phase 42 Toad stabilisation,
plus Bug Classes 5-6 discovered during Phase 42 post-commit diagnosis:

1. No single source of truth for method names (inbound AND outbound)
2. Untestable protocol logic (message routing / classification)
3. No protocol validation (wrong method names fail silently)
4. Bytes vs str mishandling in diagnostic capture
5. Binary WebSocket frames silently dropped — Toad prompts never reach the agent
6. Back-channel deadlock — server-to-Toad requests (terminal/create,
   terminal/wait_for_exit, etc.) time out because the WebSocket receive loop
   was blocked inside await _handle_request() and never called websocket.receive()
   to collect Toad's responses.

All tests are function-based, no network I/O, no subprocess (Sections 7-8 use TestClient).
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from punie.acp.meta import AGENT_METHODS, CLIENT_METHODS
from punie.http.websocket import normalize_acp_params, resolve_method_name
from punie.toad.agent import classify_jsonrpc_message
from punie.toad.diagnostic import ToadCapture


# ============================================================================
# Section 1: Method Name Resolution (Bug Class 1 — inbound)
# ============================================================================


def test_all_agent_methods_resolve_from_acp_slash():
    """Every AGENT_METHODS value must resolve — catches stale _ACP_TO_HANDLER entries."""
    for snake_key, acp_slash in AGENT_METHODS.items():
        result = resolve_method_name(acp_slash)
        assert result is not None, (
            f"AGENT_METHODS[{snake_key!r}] = {acp_slash!r} does not resolve. "
            "Add it to _ACP_TO_HANDLER in websocket.py."
        )


def test_resolve_session_prompt_both_forms():
    """ACP slash form and legacy flat form both resolve to the same handler key."""
    assert resolve_method_name("session/prompt") == "prompt"
    assert resolve_method_name("prompt") == "prompt"


def test_resolve_session_new_both_forms():
    """session/new (ACP) and new_session (legacy) both resolve to new_session."""
    assert resolve_method_name("session/new") == "new_session"
    assert resolve_method_name("new_session") == "new_session"


@pytest.mark.parametrize(
    "acp_slash,expected_handler",
    [
        ("authenticate", "authenticate"),
        ("initialize", "initialize"),
        ("session/cancel", "cancel"),
        ("session/fork", "fork_session"),
        ("session/list", "list_sessions"),
        ("session/load", "load_session"),
        ("session/new", "new_session"),
        ("session/prompt", "prompt"),
        ("session/resume", "resume_session"),
        ("session/set_config_option", "set_session_config_option"),
        ("session/set_mode", "set_session_mode"),
        ("session/set_model", "set_session_model"),
    ],
)
def test_resolve_all_agent_methods_exhaustive(acp_slash: str, expected_handler: str):
    """All 12 AGENT_METHODS map to the correct handler key."""
    assert resolve_method_name(acp_slash) == expected_handler


def test_resolve_unknown_method_returns_none():
    """Completely unknown method names return None (not a silent pass-through)."""
    assert resolve_method_name("bogus") is None
    assert resolve_method_name("session_prompt") is None  # underscore, not slash
    assert resolve_method_name("") is None
    assert resolve_method_name("SESSION/PROMPT") is None  # case-sensitive


def test_resolve_extension_methods_pass_through():
    """Extension methods prefixed with _ pass through unchanged."""
    assert resolve_method_name("_discover_tools") == "_discover_tools"
    assert resolve_method_name("_custom_extension") == "_custom_extension"
    assert resolve_method_name("_") == "_"


# ============================================================================
# Section 2: Outbound Method Names (Bug Class 1 — outbound)
# ============================================================================


async def test_websocket_client_session_update_sends_slash_name():
    """session_update() must send 'session/update' — not 'session_update'."""
    from punie.http.websocket_client import WebSocketClient
    from punie.acp.schema import AgentMessageChunk, TextContentBlock

    mock_ws = MagicMock()
    sent_messages: list[dict] = []

    async def capture_send_text(data: str) -> None:
        sent_messages.append(json.loads(data))

    mock_ws.send_text = capture_send_text
    mock_ws.client_state = MagicMock()

    client = WebSocketClient(mock_ws)

    chunk = AgentMessageChunk(
        content=TextContentBlock(type="text", text="hello"),
        session_update="agent_message_chunk",
    )
    await client.session_update(session_id="sess-1", update=chunk)

    assert len(sent_messages) == 1
    assert sent_messages[0]["method"] == "session/update", (
        f"Expected 'session/update' but got {sent_messages[0]['method']!r}. "
        "Update websocket_client.py or meta.py."
    )


def test_all_client_methods_match_meta_py():
    """Every CLIENT_METHODS value must appear in websocket_client.py source.

    This guards against CLIENT_METHODS diverging from what the code actually sends.
    """
    from punie.http import websocket_client

    source = inspect.getsource(websocket_client)
    for snake_key, acp_slash in CLIENT_METHODS.items():
        assert acp_slash in source, (
            f"CLIENT_METHODS[{snake_key!r}] = {acp_slash!r} not found in "
            "websocket_client.py. Either update the code or fix meta.py."
        )


# ============================================================================
# Section 3: Message Routing Classification (Bug Class 2)
# ============================================================================


def test_classify_response_with_result():
    assert classify_jsonrpc_message({"jsonrpc": "2.0", "id": 1, "result": {}}) == "response"


def test_classify_response_with_error():
    assert classify_jsonrpc_message(
        {"jsonrpc": "2.0", "id": 1, "error": {"code": -32603, "message": "err"}}
    ) == "response"


def test_classify_request_with_method_and_id():
    assert classify_jsonrpc_message(
        {"jsonrpc": "2.0", "id": "abc", "method": "session/request_permission", "params": {}}
    ) == "request"


def test_classify_notification_with_method_no_id():
    assert classify_jsonrpc_message(
        {"jsonrpc": "2.0", "method": "session/update", "params": {}}
    ) == "notification"


def test_classify_invalid_message():
    assert classify_jsonrpc_message({}) == "invalid"
    assert classify_jsonrpc_message({"id": 1}) == "invalid"
    assert classify_jsonrpc_message({"jsonrpc": "2.0"}) == "invalid"


def test_routing_bug_regression():
    """Documents the correct routing contract for regression purposes.

    Phase 42 bug: responses were routed to server.call() instead of
    API.process_response(), causing futures to never resolve and Toad to hang.
    """
    # Responses MUST go to API.process_response() (resolves pending futures)
    response_msg = {"jsonrpc": "2.0", "id": "abc", "result": {"sessionId": "s1"}}
    assert classify_jsonrpc_message(response_msg) == "response"

    # Notifications MUST go to server.call() (dispatches to rpc_* methods)
    notification_msg = {"jsonrpc": "2.0", "method": "session/update", "params": {}}
    assert classify_jsonrpc_message(notification_msg) == "notification"

    # Requests with id also go to server.call() (need a response sent back)
    request_msg = {"jsonrpc": "2.0", "id": "xyz", "method": "session/request_permission"}
    assert classify_jsonrpc_message(request_msg) == "request"


# ============================================================================
# Section 4: Parameter Normalization (Bug Class 3)
# ============================================================================


def test_normalize_session_id():
    result = normalize_acp_params({"sessionId": "abc123"})
    assert result == {"session_id": "abc123"}


def test_normalize_preserves_snake_case():
    """Keys already in snake_case pass through unchanged."""
    params = {"session_id": "abc", "cwd": "/tmp"}
    assert normalize_acp_params(params) == params


def test_normalize_multiple_camel_case():
    """Multiple camelCase keys in one dict are all normalised."""
    params = {
        "sessionId": "s1",
        "protocolVersion": 1,
        "clientInfo": {"name": "Toad"},
        "mcpServers": [],
    }
    result = normalize_acp_params(params)
    assert result == {
        "session_id": "s1",
        "protocol_version": 1,
        "client_info": {"name": "Toad"},
        "mcp_servers": [],
    }


def test_normalize_unknown_keys_pass_through():
    """Unknown/non-ACP keys are not touched."""
    params = {"myCustomKey": "value", "anotherKey": 42}
    result = normalize_acp_params(params)
    assert result == params


def test_normalize_empty_params():
    assert normalize_acp_params({}) == {}


# ============================================================================
# Section 5: Bytes vs str (Bug Class 4)
# ============================================================================


def test_toad_capture_on_send_handles_bytes():
    """on_send() must not raise TypeError when given bytes."""
    capture = ToadCapture()
    capture.start("ws://localhost:8000/ws")
    data = json.dumps({"jsonrpc": "2.0", "method": "initialize", "id": "1", "params": {}})
    capture.on_send(data.encode("utf-8"))  # must not raise
    events = [e for e in capture._events if e["event"] == "send"]
    assert len(events) == 1


def test_toad_capture_on_send_handles_str():
    """on_send() must work with plain str (existing behaviour)."""
    capture = ToadCapture()
    capture.start("ws://localhost:8000/ws")
    data = json.dumps({"jsonrpc": "2.0", "method": "initialize", "id": "1", "params": {}})
    capture.on_send(data)
    events = [e for e in capture._events if e["event"] == "send"]
    assert len(events) == 1
    assert events[0]["method"] == "initialize"


def test_toad_capture_on_send_truncates_long_bytes():
    """Long bytes payloads are truncated without raising."""
    capture = ToadCapture()
    capture.start("ws://localhost:8000/ws")
    # Build a JSON string longer than the 800-char body limit
    big_payload = json.dumps({"jsonrpc": "2.0", "method": "session/prompt", "id": "x",
                              "params": {"text": "a" * 1000}})
    capture.on_send(big_payload.encode("utf-8"))  # must not raise
    events = [e for e in capture._events if e["event"] == "send"]
    assert len(events) == 1
    # Body in the log must be <= 800 + 1 (the ellipsis character)
    assert len(events[0]["body"]) <= 801


async def test_diagnostic_websocket_send_handles_bytes():
    """DiagnosticWebSocket.send() must forward bytes to the underlying ws."""
    received: list = []

    class FakeWS:
        async def send(self, data):
            received.append(data)

    capture = ToadCapture()
    capture.start("ws://localhost:8000/ws")
    diag_ws = capture.wrap(FakeWS())

    payload = b'{"jsonrpc":"2.0","method":"initialize","id":"1","params":{}}'
    await diag_ws.send(payload)

    assert received == [payload]


# ============================================================================
# Section 6: Meta Consistency (cross-cutting)
# ============================================================================


def test_meta_agent_methods_all_have_slash_notation():
    """All session_* entries in AGENT_METHODS use '/' notation.

    Guards against accidental snake_case values like 'session_prompt'.
    """
    for key, value in AGENT_METHODS.items():
        if key.startswith("session_"):
            assert "/" in value, (
                f"AGENT_METHODS[{key!r}] = {value!r} should use slash notation "
                f"(e.g. 'session/{key[8:]}')."
            )


def test_meta_client_methods_all_have_slash_notation():
    """All entries in CLIENT_METHODS use '/' notation."""
    for key, value in CLIENT_METHODS.items():
        assert "/" in value, (
            f"CLIENT_METHODS[{key!r}] = {value!r} should use slash notation."
        )


def test_meta_agent_and_client_disjoint():
    """AGENT_METHODS and CLIENT_METHODS must not share any ACP method names.

    Overlap would indicate a protocol direction error (e.g. a server→client
    notification accidentally registered as a client→server call).
    """
    agent_slash = set(AGENT_METHODS.values())
    client_slash = set(CLIENT_METHODS.values())
    overlap = agent_slash & client_slash
    assert not overlap, (
        f"AGENT_METHODS and CLIENT_METHODS share method names: {overlap}. "
        "Each direction must have exclusive ownership."
    )


# ============================================================================
# Section 7: Binary Frame Regression (Bug Class 5)
#
# Root cause: toad.jsonrpc.Request.body_json returns bytes (UTF-8 encoded
# JSON).  WebSocketToadAgent.send() passed this directly to the websockets
# library, which transmitted a *binary* WebSocket frame.
#
# Starlette's websocket.receive() returns {"type": "websocket.receive",
# "bytes": ...} for binary frames — no "text" key.  The server's receive loop
# checked `if "text" not in message` and silently dropped the message with a
# WARNING log.  The client sent a prompt and received no response, causing
# Toad to hang on "New session..." indefinitely.
#
# Confirmed in ~/.punie/logs/punie.log:
#   WARNING - Received non-text message from client-0  (at exact prompt times)
#
# Fixes applied:
#   1. toad/agent.py _run_async_send: decode body bytes → str before ws.send()
#   2. http/websocket.py: accept binary frames by decoding "bytes" key
# ============================================================================


def test_toad_request_body_json_returns_bytes():
    """Documents that toad.jsonrpc.Request.body_json returns bytes, not str.

    This is the root cause of Bug Class 5.  The fix in _run_async_send decodes
    bytes → str before calling ws.send() so the frame is text, not binary.

    If Toad ever changes body_json to return str, remove the isinstance decode
    in WebSocketToadAgent._run_async_send() and this test can be deleted.
    """
    from toad import jsonrpc

    # Inspect the property source to confirm it encodes to bytes
    src = inspect.getsource(jsonrpc.Request.body_json.fget)
    assert ".encode(" in src, (
        "toad.jsonrpc.Request.body_json no longer encodes to bytes. "
        "Remove the 'if isinstance(body, bytes): body = body.decode()' workaround "
        "in WebSocketToadAgent._run_async_send() in src/punie/toad/agent.py."
    )


def test_binary_jsonrpc_message_dispatched_not_dropped():
    """Regression: binary WebSocket frames must be dispatched, not silently dropped.

    Before the fix:
        client sends binary JSON → server logs WARNING, continue → NO response

    After the fix:
        client sends binary JSON → server decodes UTF-8 → dispatches normally

    This test would have FAILED before the websocket.py fix and caught the bug
    that caused Toad to hang on 'New session...' after every prompt submission.
    """
    from punie.agent.adapter import PunieAgent
    from punie.http.app import create_app

    agent = PunieAgent(model="test", name="test-agent")
    app = create_app(agent)

    with TestClient(app).websocket_connect("/ws") as ws:
        # Initialize
        ws.send_json({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocol_version": 1},
        })
        ws.receive_json()

        # Send new_session as binary bytes — exactly as Toad's body_json does
        msg = json.dumps({
            "jsonrpc": "2.0", "id": 2, "method": "new_session",
            "params": {"cwd": "/tmp", "mcp_servers": []},
        })
        ws.send_bytes(msg.encode("utf-8"))

        # Must receive a response (id==2), not hang or get nothing
        resp = ws.receive_json()
        assert resp.get("id") == 2, (
            f"Expected response id=2 but got {resp!r}. "
            "Binary frames are being dropped — check websocket_endpoint in websocket.py."
        )
        assert "result" in resp, f"Expected result in response, got {resp!r}"


# ============================================================================
# Section 8: Back-Channel Deadlock (Bug Class 6)
#
# Root cause: websocket_endpoint processed inbound requests with
#   await _handle_request(websocket, agent, client_id, message)
# which blocked the receive loop for the entire duration of the request.
# While the LLM was running execute_code and waiting for terminal/create or
# terminal/wait_for_exit responses from Toad, nobody called websocket.receive()
# — so Toad's responses piled up in the TCP buffer and the _send_request()
# futures timed out after 30 s.  Pydantic AI retried, same deadlock, then
# raised "Tool 'execute_code' exceeded max retries count of 1".
#
# Fix: inbound requests are now dispatched as asyncio.create_task() so the
# receive loop stays unblocked and continues to collect Toad responses via
# client.handle_response(), resolving the pending _send_request() futures.
# ============================================================================


def test_websocket_receive_loop_stays_unblocked_during_request():
    """Regression: the receive loop must NOT be blocked while handling a request.

    Strategy: connect two WebSocket clients.  Client 1 sends new_session
    (a slow-ish request that needs a response).  While client 1's request is
    being processed, client 2 should be able to send its own initialize and
    get a response — proving the server's receive loop is not blocked.

    Before the fix (await _handle_request):
        Client 2's initialize would be stuck until client 1's new_session
        response was sent, because the receive loop was blocked.

    After the fix (asyncio.create_task):
        Both clients proceed concurrently.

    This is a structural test of the concurrency model, not a timing test.
    It passes deterministically because both requests are processed from the
    same event loop and TestClient's thread-safe queues handle the sequencing.
    """
    from punie.agent.adapter import PunieAgent
    from punie.http.app import create_app

    agent = PunieAgent(model="test", name="test-agent")
    app = create_app(agent)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws1:
            with client.websocket_connect("/ws") as ws2:
                # Both clients send requests concurrently (from test's perspective,
                # these are sequential but both are queued before any response is read)
                ws1.send_json({
                    "jsonrpc": "2.0", "id": 10, "method": "new_session",
                    "params": {"cwd": "/tmp", "mcp_servers": []},
                })
                ws2.send_json({
                    "jsonrpc": "2.0", "id": 20, "method": "initialize",
                    "params": {"protocol_version": 1},
                })

                # Both must receive responses — if the receive loop were blocked
                # by ws1's new_session, ws2's initialize would never be processed
                resp1 = ws1.receive_json()
                assert resp1.get("id") == 10, (
                    f"ws1 expected response id=10 but got {resp1!r}. "
                    "Check that _handle_request runs as create_task in websocket.py."
                )
                assert "result" in resp1

                resp2 = ws2.receive_json()
                assert resp2.get("id") == 20, (
                    f"ws2 expected response id=20 but got {resp2!r}. "
                    "Back-channel deadlock regression: receive loop was blocked."
                )
                assert "result" in resp2


async def test_back_channel_response_handling_does_not_block_receive_loop():
    """Responses to server-initiated requests must be routed synchronously.

    client.handle_response() is called with `await` (not create_task) to
    ensure pending _send_request() futures are resolved immediately when
    Toad sends a response — before the receive loop picks up the next message.

    Verifies that handle_response() resolves the pending future immediately
    (same event loop iteration), not via a deferred task.
    """
    import asyncio
    from unittest.mock import MagicMock

    from punie.http.websocket_client import WebSocketClient

    mock_ws = MagicMock()
    client = WebSocketClient(mock_ws)

    # Inject a pending future directly (simulates an in-flight _send_request)
    future: asyncio.Future = asyncio.get_event_loop().create_future()
    client._pending_requests["req-42"] = future

    # Deliver the response
    response = {"jsonrpc": "2.0", "id": "req-42", "result": {"terminalId": "t1"}}
    await client.handle_response(response)

    # Future must be resolved immediately, not pending
    assert future.done(), "handle_response() must resolve the future immediately"
    assert future.result() == {"terminalId": "t1"}
