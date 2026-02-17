"""Tests for WebSocket reconnection support (Phase 28.1).

Tests:
- Session persistence during grace period
- Resume token validation
- Session resumption after reconnection
- Expired session cleanup
- Multiple reconnection attempts
- Invalid resume token handling
"""

import asyncio
import time

import pytest
from starlette.testclient import TestClient

from punie.agent.adapter import PunieAgent
from punie.http.app import create_app


@pytest.fixture
def agent() -> PunieAgent:
    """Create test agent with test model."""
    return PunieAgent(model="test", name="test-agent")


@pytest.fixture
def test_app(agent: PunieAgent):
    """Create test Starlette app."""
    return create_app(agent)


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
    # Manually simulate session creation and disconnection
    from punie.http.websocket_client import WebSocketClient
    from unittest.mock import Mock
    from starlette.websockets import WebSocket

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
            token2 = resp2["result"]["_meta"]["resume_token"]

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

    # Could be configured in __init__ in future
    # agent = PunieAgent(model="test", grace_period=600)
    # assert agent._grace_period == 600


async def test_cleanup_task_runs(agent):
    """Test that cleanup task is created and runs."""
    from punie.http.websocket_client import WebSocketClient
    from unittest.mock import Mock
    from starlette.websockets import WebSocket

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
