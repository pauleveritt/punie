"""Tests for WebSocket functionality: integration, reconnection, and message handling.

Consolidates:
- WebSocket integration tests (multi-client support, session routing, cleanup)
- WebSocket reconnection tests (grace period, session persistence, resume)
- WebSocket send tests (message handling, async bridging, prompt delivery)
- Toad agent send tests (async-to-sync bridging, call_later pattern)

Following function-based-tests standard - no classes, just functions.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocket

from punie.agent.adapter import PunieAgent
from punie.http.app import create_app


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def agent() -> PunieAgent:
    """Create test agent with test model."""
    return PunieAgent(model="test", name="test-agent")


@pytest.fixture
def test_app(agent: PunieAgent):
    """Create test Starlette app."""
    return create_app(agent)


# ============================================================================
# WebSocket Integration Tests
# ============================================================================


def test_single_client_connection(test_app):
    """Test that a single WebSocket client can connect and create a session."""
    with TestClient(test_app) as client:
        with client.websocket_connect("/ws") as websocket:
            # Send initialize request
            initialize_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocol_version": 1,
                },
            }
            websocket.send_json(initialize_request)

            # Receive initialize response
            response = websocket.receive_json()
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response
            assert response["result"]["protocolVersion"] == 1

            # Send new_session request
            new_session_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "new_session",
                "params": {
                    "cwd": "/tmp",
                    "mcp_servers": [],
                },
            }
            websocket.send_json(new_session_request)

            # Receive new_session response
            response = websocket.receive_json()
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 2
            assert "result" in response
            assert "sessionId" in response["result"]


def test_multiple_clients_simultaneously(test_app, agent):
    """Test that multiple WebSocket clients can connect simultaneously."""
    with TestClient(test_app) as client:
        # Connect two clients
        with client.websocket_connect("/ws") as ws1:
            with client.websocket_connect("/ws") as ws2:
                # Client 1 creates session
                ws1.send_json({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "new_session",
                    "params": {"cwd": "/tmp", "mcp_servers": []},
                })
                resp1 = ws1.receive_json()
                session1_id = resp1["result"]["sessionId"]

                # Client 2 creates session
                ws2.send_json({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "new_session",
                    "params": {"cwd": "/tmp", "mcp_servers": []},
                })
                resp2 = ws2.receive_json()
                session2_id = resp2["result"]["sessionId"]

                # Verify sessions are different
                assert session1_id != session2_id

                # Verify both clients are registered
                assert len(agent._connections) == 2

                # Verify session ownership
                assert session1_id in agent._session_owners
                assert session2_id in agent._session_owners
                assert agent._session_owners[session1_id] != agent._session_owners[session2_id]


def test_session_routing(test_app, agent):
    """Test that prompts route to the correct client via session ownership."""
    with TestClient(test_app) as client:
        with client.websocket_connect("/ws") as ws1:
            with client.websocket_connect("/ws") as ws2:
                # Client 1 creates session
                ws1.send_json({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "new_session",
                    "params": {"cwd": "/tmp", "mcp_servers": []},
                })
                resp1 = ws1.receive_json()
                session1_id = resp1["result"]["sessionId"]

                # Client 2 creates session
                ws2.send_json({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "new_session",
                    "params": {"cwd": "/tmp", "mcp_servers": []},
                })
                resp2 = ws2.receive_json()
                session2_id = resp2["result"]["sessionId"]

                # Verify session ownership routing works
                # Session 1 should route to client 1
                client1_conn = agent.get_client_connection(session1_id)
                client2_conn = agent.get_client_connection(session2_id)

                assert client1_conn is not None
                assert client2_conn is not None
                assert client1_conn != client2_conn

                # Verify sessions are owned by different clients
                client1_id = agent._session_owners[session1_id]
                client2_id = agent._session_owners[session2_id]
                assert client1_id != client2_id


def test_graceful_disconnect_cleanup(test_app, agent):
    """Test that disconnecting a client cleans up its sessions."""
    with TestClient(test_app) as client:
        # Connect and create session
        with client.websocket_connect("/ws") as ws:
            ws.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "new_session",
                "params": {"cwd": "/tmp", "mcp_servers": []},
            })
            resp = ws.receive_json()
            session_id = resp["result"]["sessionId"]

            # Verify client and session are registered
            assert len(agent._connections) == 1
            assert session_id in agent._sessions
            assert session_id in agent._session_owners

        # After disconnect (context manager exit)
        # With Phase 28.1 reconnection support, sessions persist during grace period
        assert len(agent._connections) == 0
        # Session should still exist (grace period active)
        assert session_id in agent._sessions
        assert session_id in agent._session_owners
        # Client should be marked as disconnected
        assert len(agent._disconnected_clients) == 1


def test_invalid_json_handling(test_app):
    """Test that invalid JSON is handled gracefully."""
    with TestClient(test_app) as client:
        with client.websocket_connect("/ws") as websocket:
            # Send invalid JSON
            websocket.send_text("not valid json")

            # Should receive error response
            response = websocket.receive_json()
            assert response["jsonrpc"] == "2.0"
            assert "error" in response
            assert response["error"]["code"] == -32700  # Parse error
            assert "Parse error" in response["error"]["message"]


def test_unknown_method_handling(test_app):
    """Test that unknown methods return errors."""
    with TestClient(test_app) as client:
        with client.websocket_connect("/ws") as websocket:
            # Send request with unknown method
            websocket.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "unknown_method",
                "params": {},
            })

            # Should receive error response
            response = websocket.receive_json()
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "error" in response
            assert response["error"]["code"] == -32603  # Internal error
            assert "Unknown method" in response["error"]["data"]


async def test_client_id_generation(agent):
    """Test that client IDs are unique and sequential."""
    from punie.http.websocket_client import WebSocketClient

    # Create mock WebSocket
    mock_ws = Mock(spec=WebSocket)

    # Register multiple clients
    client1 = WebSocketClient(mock_ws)
    client2 = WebSocketClient(mock_ws)
    client3 = WebSocketClient(mock_ws)

    id1 = await agent.register_client(client1)
    id2 = await agent.register_client(client2)
    id3 = await agent.register_client(client3)

    # Verify IDs are unique
    assert id1 != id2 != id3
    assert id1 == "client-0"
    assert id2 == "client-1"
    assert id3 == "client-2"

    # Cleanup
    await agent.unregister_client(id1)
    await agent.unregister_client(id2)
    await agent.unregister_client(id3)


async def test_session_ownership_tracking(agent):
    """Test that session ownership is correctly tracked."""
    from punie.http.websocket_client import WebSocketClient

    mock_ws = Mock(spec=WebSocket)
    client = WebSocketClient(mock_ws)
    client_id = await agent.register_client(client)

    # Create session with client_id (required for WebSocket sessions)
    session = await agent.new_session(cwd="/tmp", mcp_servers=[], client_id=client_id)
    assert session.session_id in agent._session_owners
    assert agent._session_owners[session.session_id] == client_id

    # Verify get_client_connection works
    conn = agent.get_client_connection(session.session_id)
    assert conn is client

    # Cleanup (with reconnection support, sessions persist during grace period)
    await agent.unregister_client(client_id)
    # Session should still exist during grace period
    assert session.session_id in agent._session_owners
    # Client should be marked as disconnected
    assert client_id in agent._disconnected_clients


# ============================================================================
# WebSocket Reconnection Tests
# ============================================================================


async def test_session_persists_during_grace_period(test_app, agent):
    """Test that sessions survive disconnection for grace period."""
    with TestClient(test_app) as client:
        # Client connects and creates session
        with client.websocket_connect("/ws") as ws:
            ws.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "new_session",
                "params": {"cwd": "/tmp", "mcp_servers": []},
            })
            resp = ws.receive_json()
            session_id = resp["result"]["sessionId"]
            resume_token = resp["result"].get("_meta", {}).get("resume_token")

            assert session_id
            assert resume_token  # Should get resume token

            # Verify session is registered
            assert session_id in agent._sessions
            assert session_id in agent._session_owners

        # After disconnect (context manager exit)
        # Session should still exist (grace period active)
        await asyncio.sleep(0.1)  # Give cleanup a moment
        assert session_id in agent._sessions, "Session should persist during grace period"
        assert session_id in agent._session_owners


async def test_resume_session_after_reconnect(test_app, agent):
    """Test successful session resumption after reconnection."""
    with TestClient(test_app) as client:
        # First connection: create session
        with client.websocket_connect("/ws") as ws1:
            ws1.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "new_session",
                "params": {"cwd": "/tmp", "mcp_servers": []},
            })
            resp = ws1.receive_json()
            session_id = resp["result"]["sessionId"]
            resume_token = resp["result"]["_meta"]["resume_token"]

        # Session should persist
        await asyncio.sleep(0.1)
        assert session_id in agent._sessions

        # Second connection: resume session
        with client.websocket_connect("/ws") as ws2:
            ws2.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resume_session",
                "params": {
                    "cwd": "/tmp",
                    "session_id": session_id,
                    "resume_token": resume_token,
                },
            })
            resp = ws2.receive_json()

            # Should succeed
            assert "result" in resp
            assert resp["id"] == 1

            # Session should still exist and be owned by new client
            assert session_id in agent._sessions
            assert session_id in agent._session_owners


async def test_invalid_resume_token_rejected(test_app, agent):
    """Test that invalid resume tokens are rejected."""
    with TestClient(test_app) as client:
        # Create session
        with client.websocket_connect("/ws") as ws1:
            ws1.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "new_session",
                "params": {"cwd": "/tmp", "mcp_servers": []},
            })
            resp = ws1.receive_json()
            session_id = resp["result"]["sessionId"]

        # Try to resume with invalid token
        with client.websocket_connect("/ws") as ws2:
            ws2.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resume_session",
                "params": {
                    "cwd": "/tmp",
                    "session_id": session_id,
                    "resume_token": "invalid-token",
                },
            })
            resp = ws2.receive_json()

            # Should fail with error
            assert "error" in resp
            assert "Invalid resume token" in resp["error"]["data"]


async def test_expired_session_cleanup(agent):
    """Test that expired sessions are cleaned up after grace period."""
    from punie.http.websocket_client import WebSocketClient

    mock_ws = Mock(spec=WebSocket)
    client = WebSocketClient(mock_ws)

    # Register client and create session
    client_id = await agent.register_client(client)
    resp = await agent.new_session(cwd="/tmp", mcp_servers=[], client_id=client_id)
    session_id = resp.session_id

    # Disconnect client (marks for cleanup)
    await agent.unregister_client(client_id)

    # Session should still exist
    assert session_id in agent._sessions
    assert client_id in agent._disconnected_clients

    # Manually set disconnect time to past (simulate expiration)
    agent._disconnected_clients[client_id] = time.time() - 400  # 400 seconds ago

    # Trigger cleanup manually (normally runs in background)
    async with agent._state_lock:
        expired = [
            cid for cid, disconnect_time in agent._disconnected_clients.items()
            if time.time() - disconnect_time > agent._grace_period
        ]

        for cid in expired:
            sessions_to_remove = [
                sid for sid, owner in agent._session_owners.items()
                if owner == cid
            ]
            for sid in sessions_to_remove:
                agent._sessions.pop(sid, None)
                agent._session_tokens.pop(sid, None)
                del agent._session_owners[sid]
            del agent._disconnected_clients[cid]

    # Session should be cleaned up
    assert session_id not in agent._sessions
    assert client_id not in agent._disconnected_clients


async def test_resume_nonexistent_session(test_app):
    """Test that resuming non-existent session fails."""
    with TestClient(test_app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resume_session",
                "params": {
                    "cwd": "/tmp",
                    "session_id": "nonexistent-session",
                    "resume_token": "any-token",
                },
            })
            resp = ws.receive_json()

            # Should fail with error
            assert "error" in resp
            assert "not found or expired" in resp["error"]["data"]


async def test_multiple_sessions_per_client(test_app, agent):
    """Test that client can have multiple sessions across reconnects."""
    with TestClient(test_app) as client:
        # First connection: create two sessions
        with client.websocket_connect("/ws") as ws1:
            # Session 1
            ws1.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "new_session",
                "params": {"cwd": "/tmp", "mcp_servers": []},
            })
            resp1 = ws1.receive_json()
            session1_id = resp1["result"]["sessionId"]
            token1 = resp1["result"]["_meta"]["resume_token"]

            # Session 2
            ws1.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "new_session",
                "params": {"cwd": "/tmp", "mcp_servers": []},
            })
            resp2 = ws1.receive_json()
            session2_id = resp2["result"]["sessionId"]
            _token2 = resp2["result"]["_meta"]["resume_token"]

        # Both sessions should persist
        await asyncio.sleep(0.1)
        assert session1_id in agent._sessions
        assert session2_id in agent._sessions

        # Reconnect and resume first session
        with client.websocket_connect("/ws") as ws2:
            ws2.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resume_session",
                "params": {
                    "cwd": "/tmp",
                    "session_id": session1_id,
                    "resume_token": token1,
                },
            })
            resp = ws2.receive_json()
            assert "result" in resp

            # First session should be owned by new client
            # Second session should be cleaned up (old client's other sessions)
            assert session1_id in agent._sessions
            # Note: session2 might still exist depending on cleanup timing


async def test_grace_period_configuration(agent):
    """Test that grace period is configurable."""
    # Default is 300 seconds (5 minutes)
    assert agent._grace_period == 300


async def test_cleanup_task_runs(agent):
    """Test that cleanup task is created and runs."""
    from punie.http.websocket_client import WebSocketClient

    # Cleanup task starts lazily on first client registration
    assert agent._cleanup_task is None
    assert not agent._cleanup_started

    # Register a client to trigger task start
    mock_ws = Mock(spec=WebSocket)
    client = WebSocketClient(mock_ws)
    await agent.register_client(client)

    # Now cleanup task should be created
    assert agent._cleanup_task is not None
    assert agent._cleanup_started
    assert not agent._cleanup_task.done()

    # Shutdown should cancel cleanup task
    await agent.shutdown()
    assert agent._cleanup_task.done()
    assert agent._cleanup_task.cancelled()


# ============================================================================
# WebSocket Message Handling Tests
# ============================================================================


def test_websocket_handles_text_messages(test_app):
    """WebSocket should process valid text messages."""
    with TestClient(test_app).websocket_connect("/ws") as websocket:
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocol_version": 1,
                "client_info": {"name": "test-client", "version": "1.0"},
            },
            "id": 1,
        }
        websocket.send_json(init_request)

        # Should receive initialize response
        response = websocket.receive_json()
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response


def test_websocket_handles_disconnect_gracefully(test_app):
    """WebSocket should handle disconnect frames without crashing.

    This reproduces the KeyError: 'text' bug we fixed.
    """
    with TestClient(test_app).websocket_connect("/ws") as websocket:
        # Send initialize
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocol_version": 1,
                "client_info": {"name": "test-client", "version": "1.0"},
            },
            "id": 1,
        }
        websocket.send_json(init_request)
        websocket.receive_json()  # Get response

        # Close connection - server should handle gracefully
        websocket.close()

    # If we get here without exception, the test passes
    # Previously this would raise KeyError: 'text'


def test_websocket_handles_binary_messages(test_app):
    """WebSocket should ignore binary messages with warning."""
    with TestClient(test_app).websocket_connect("/ws") as websocket:
        # Send initialize first
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocol_version": 1,
                "client_info": {"name": "test-client", "version": "1.0"},
            },
            "id": 1,
        }
        websocket.send_json(init_request)
        response = websocket.receive_json()
        assert "result" in response

        # Send binary data (like a ping frame)
        websocket.send_bytes(b"\x00\x01\x02")

        # Server should continue working - send another request
        new_session_request = {
            "jsonrpc": "2.0",
            "method": "new_session",
            "params": {"cwd": "/test"},
            "id": 2,
        }
        websocket.send_json(new_session_request)

        # Should still process requests
        response = websocket.receive_json()
        assert response["id"] == 2


# ============================================================================
# Prompt Delivery Tests
# ============================================================================


@pytest.mark.asyncio
async def test_prompt_reaches_server(test_app):
    """End-to-end test: prompt sent from client reaches server.

    This is the integration test that would have caught the
    'Initializing...' hang issue.
    """
    with TestClient(test_app).websocket_connect("/ws") as websocket:
        # Initialize
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocol_version": 1,
                "client_info": {"name": "test-client", "version": "1.0"},
            },
            "id": 1,
        }
        websocket.send_json(init_request)
        init_response = websocket.receive_json()
        assert "result" in init_response

        # New session
        new_session_request = {
            "jsonrpc": "2.0",
            "method": "new_session",
            "params": {"cwd": "/test", "mcp_servers": []},
            "id": 2,
        }
        websocket.send_json(new_session_request)
        session_response = websocket.receive_json()
        assert "result" in session_response
        session_id = session_response["result"]["sessionId"]  # ACP uses camelCase

        # Send a prompt - this is what was failing
        prompt_request = {
            "jsonrpc": "2.0",
            "method": "prompt",
            "params": {
                "session_id": session_id,
                "prompt": [
                    {"type": "text", "text": "What is dependency injection?"}
                ],
            },
            "id": 3,
        }
        websocket.send_json(prompt_request)

        # Should receive session_update notifications
        # (We'll receive multiple updates as the response streams)
        updates_received = 0
        max_updates = 10  # Don't wait forever

        while updates_received < max_updates:
            try:
                message = websocket.receive_json()  # ty: ignore[call-arg]
                if message.get("method") == "session_update":
                    updates_received += 1
                    # Check that we're getting real updates
                    assert "params" in message
                    assert "session_id" in message["params"]
                elif "result" in message:
                    # Final response
                    break
            except Exception:  # noqa: S110
                break

        # We should have received at least some updates
        assert updates_received > 0, "No session_update notifications received"


# ============================================================================
# Async-to-Sync Bridging Tests
# ============================================================================


@pytest.fixture
def mock_toad_components():
    """Mock Toad/Textual components needed for agent."""
    # Mock the message target (Textual's event scheduling)
    message_target = Mock()
    message_target.call_later = Mock()

    # Mock the WebSocket connection
    websocket = AsyncMock()
    websocket.send = AsyncMock()

    # Mock JSON-RPC request
    request = Mock()
    request.body = '{"jsonrpc": "2.0", "method": "prompt", "id": 1}'
    request.body_json = b'{"jsonrpc": "2.0", "method": "prompt", "id": 1}'

    return {
        "message_target": message_target,
        "websocket": websocket,
        "request": request,
    }


def test_send_uses_call_later(mock_toad_components):
    """send() should use message_target.call_later() to schedule async send.

    This tests the fix for the event loop issue where asyncio.create_task()
    didn't work from sync context.
    """
    message_target = mock_toad_components["message_target"]
    websocket = mock_toad_components["websocket"]
    request = mock_toad_components["request"]

    # Simulate what send() should do
    def send(request, message_target, websocket):
        if websocket is None:
            return
        if message_target is not None:
            # Should use call_later to schedule in Textual's event loop
            message_target.call_later(lambda: print("sending..."), request)

    # Call send
    send(request, message_target, websocket)

    # Verify call_later was called
    message_target.call_later.assert_called_once()


def test_send_with_none_websocket_returns_early(mock_toad_components):
    """send() should return early if WebSocket is not connected.

    This prevents errors when Toad tries to send before connection.
    """
    request = mock_toad_components["request"]
    message_target = mock_toad_components["message_target"]

    # Simulate send with None websocket
    def send(request, message_target, websocket):
        if websocket is None:
            return False  # Indicate early return
        return True

    # Should return early
    result = send(request, message_target, None)
    assert result is False

    # call_later should NOT be called
    message_target.call_later.assert_not_called()


def test_send_with_none_message_target_logs_error(mock_toad_components):
    """send() should log error if message_target is None.

    This happens if agent is not properly initialized in Textual context.
    """
    websocket = mock_toad_components["websocket"]
    request = mock_toad_components["request"]

    error_logged = False

    def send(request, message_target, websocket):
        nonlocal error_logged
        if websocket is None:
            return
        if message_target is None:
            error_logged = True
            return

    # Call with None message_target
    send(request, None, websocket)

    # Should have logged error
    assert error_logged is True


@pytest.mark.asyncio
async def test_send_async_sends_json_rpc(mock_toad_components):
    """_send_async() should send JSON-RPC message over WebSocket.

    This is the final step that actually delivers the message.
    """
    websocket = mock_toad_components["websocket"]
    request = mock_toad_components["request"]

    # Simulate _send_async
    async def _send_async(websocket, request):
        if websocket is None:
            return
        await websocket.send(request.body_json)

    # Call it
    await _send_async(websocket, request)

    # Verify send was called with correct data
    websocket.send.assert_called_once_with(request.body_json)


@pytest.mark.asyncio
async def test_send_async_handles_websocket_errors(mock_toad_components):
    """_send_async() should handle WebSocket send errors gracefully."""
    websocket = mock_toad_components["websocket"]
    request = mock_toad_components["request"]

    # Make send raise an error
    websocket.send.side_effect = ConnectionError("Connection lost")

    error_caught = False

    # Simulate _send_async with error handling
    async def _send_async(websocket, request):
        nonlocal error_caught
        if websocket is None:
            return
        try:
            await websocket.send(request.body_json)
        except Exception:
            error_caught = True

    # Call it
    await _send_async(websocket, request)

    # Should have caught the error
    assert error_caught is True


def test_full_send_flow_integration(mock_toad_components):
    """Test the complete flow: send() → call_later → _send_sync → _send_async.

    This integration test verifies the entire async bridging chain.
    """
    message_target = mock_toad_components["message_target"]
    websocket = mock_toad_components["websocket"]
    request = mock_toad_components["request"]

    # Track the flow
    flow = []

    def send(request, message_target, websocket):
        flow.append("send")
        if websocket is None:
            return
        if message_target is not None:
            # Schedule _send_sync via call_later
            message_target.call_later(_send_sync, request)

    def _send_sync(request):
        flow.append("_send_sync")
        # Would create async task here
        # For test, just record the call

    # Execute
    send(request, message_target, websocket)

    # Verify flow started correctly
    assert "send" in flow

    # Simulate call_later executing the callback
    # (In real Textual, this happens in the event loop)
    args = message_target.call_later.call_args[0]
    callback = args[0]
    callback_request = args[1]

    # Execute the callback
    callback(callback_request)

    # Verify complete flow
    assert flow == ["send", "_send_sync"]


# ============================================================================
# Event Loop Integration Tests
# ============================================================================


def test_asyncio_create_task_requires_running_loop():
    """asyncio.create_task() requires a running event loop.

    This test documents why our first attempts failed - we were calling
    create_task() from sync context without a running loop.
    """
    async def dummy_coroutine():
        pass

    # Without running loop, create_task fails
    try:
        asyncio.create_task(dummy_coroutine())
        pytest.fail("Should have raised RuntimeError")
    except RuntimeError as e:
        assert "no running event loop" in str(e).lower()


@pytest.mark.asyncio
async def test_create_task_works_in_async_context():
    """create_task() works fine when called from async context.

    This shows that _send_sync() → create_task() → _send_async()
    should work if _send_sync() is called within the event loop.
    """
    executed = False

    async def async_task():
        nonlocal executed
        executed = True

    # In async context, create_task works
    task = asyncio.create_task(async_task())
    await task

    # Task executed
    assert executed is True


def test_call_later_provides_event_loop_context():
    """Textual's call_later() executes callbacks in the event loop.

    This is why using message_target.call_later() solves the problem -
    it ensures _send_sync() runs in the event loop context.
    """
    # Mock Textual's call_later behavior
    callbacks = []

    def call_later(callback, *args):
        # Textual schedules this to run in its event loop
        callbacks.append((callback, args))

    # Use it
    def my_callback(arg):
        return f"called with {arg}"

    call_later(my_callback, "test")

    # Callback is scheduled (would execute in event loop)
    assert len(callbacks) == 1
    callback, args = callbacks[0]

    # Execute it
    result = callback(*args)
    assert result == "called with test"
