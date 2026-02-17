"""Integration tests for WebSocket multi-client support.

Tests WebSocket endpoint for Phase 28, including:
- Single client connection
- Multiple simultaneous clients
- Independent sessions per client
- Session routing (correct client receives updates)
- Graceful cleanup on disconnect
"""


import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocket

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
    from unittest.mock import Mock

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
    from unittest.mock import Mock

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
