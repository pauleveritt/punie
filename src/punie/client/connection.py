"""WebSocket connection and ACP handshake utilities.

This module provides helpers for connecting to a Punie server via WebSocket
and performing the ACP protocol handshake (initialize → new_session).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)

__all__ = ["connect_to_server", "send_request", "initialize_session", "punie_session"]


async def connect_to_server(url: str) -> ClientConnection:
    """Connect to Punie server via WebSocket.

    Args:
        url: WebSocket URL (e.g., ws://localhost:8000/ws)

    Returns:
        Connected WebSocket client

    Raises:
        websockets.exceptions.WebSocketException: If connection fails

    Example:
        websocket = await connect_to_server("ws://localhost:8000/ws")
        await websocket.send(...)
        data = await websocket.recv()
        await websocket.close()
    """
    logger.debug(f"Connecting to {url}")
    websocket = await websockets.connect(url)
    logger.info(f"Connected to {url}")
    return websocket


async def send_request(
    websocket: ClientConnection, method: str, params: dict[str, Any]
) -> dict[str, Any]:
    """Send JSON-RPC request and wait for response.

    Args:
        websocket: Connected WebSocket client
        method: JSON-RPC method name
        params: Method parameters dict

    Returns:
        Response result dict (raises if error present)

    Raises:
        RuntimeError: If response contains error or timeout
        ConnectionError: If WebSocket disconnects
        websockets.exceptions.WebSocketException: If connection fails

    Example:
        result = await send_request(ws, "initialize", {"protocol_version": 1})
        print(result["protocol_version"])
    """
    # Generate unique request ID (Issue #4: use UUID to prevent collision)
    request_id = str(uuid.uuid4())

    # Send request
    request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    logger.debug(f"Sending {method} request (id={request_id})")
    await websocket.send(json.dumps(request))

    # Wait for response (Issue #1: add timeout protection)
    while True:
        try:
            data = await asyncio.wait_for(websocket.recv(), timeout=30.0)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Timeout waiting for {method} response (id={request_id}) after 30s"
            )
        except websockets.exceptions.ConnectionClosed as exc:
            raise ConnectionError(f"Server disconnected during {method}: {exc}")

        # Parse JSON (Issue #2: handle malformed data)
        try:
            message = json.loads(data)
        except json.JSONDecodeError as exc:
            logger.warning(f"Invalid JSON from server: {exc}")
            continue  # Skip and wait for next message

        logger.debug(f"Received message: {message}")

        # Skip notifications
        if "method" in message:
            logger.debug(f"Skipping notification: {message['method']}")
            continue

        # Check if this is our response
        if message.get("id") == request_id:
            if "error" in message:
                error = message["error"]
                raise RuntimeError(
                    f"{method} (req={request_id}) failed: {error.get('message')} (code {error.get('code')})"
                )
            return message.get("result", {})


async def initialize_session(websocket: ClientConnection, cwd: str) -> str:
    """Perform ACP handshake (initialize → new_session).

    Args:
        websocket: Connected WebSocket client
        cwd: Current working directory for session

    Returns:
        Session ID

    Raises:
        RuntimeError: If handshake fails

    Example:
        ws = await connect_to_server("ws://localhost:8000/ws")
        session_id = await initialize_session(ws, "/path/to/project")
        print(f"Session created: {session_id}")
    """
    # Step 1: Initialize
    logger.debug("Sending initialize request")
    init_result = await send_request(
        websocket,
        "initialize",
        {
            "protocol_version": 1,
            "client_info": {"name": "punie-client", "version": "0.1.0"},
        },
    )
    logger.info(
        f"Initialized: protocol={init_result.get('protocol_version')}, "
        f"agent={init_result.get('agent_info', {}).get('name')}"
    )

    # Step 2: Create new session
    logger.debug(f"Creating new session for workspace: {cwd}")
    session_result = await send_request(
        websocket,
        "new_session",
        {"cwd": cwd, "mode": "code", "mcp_servers": []},  # snake_case for Python
    )
    session_id = session_result["sessionId"]  # camelCase in response (by_alias=True)
    logger.info(f"Session created: {session_id}")

    return session_id


@asynccontextmanager
async def punie_session(
    server_url: str, cwd: str
) -> AsyncIterator[tuple[ClientConnection, str]]:
    """Context manager for session lifecycle.

    Connects to server, performs handshake, yields (websocket, session_id),
    and ensures clean disconnect on exit.

    Args:
        server_url: WebSocket URL (e.g., ws://localhost:8000/ws)
        cwd: Current working directory for session

    Yields:
        (websocket, session_id) tuple

    Example:
        async with punie_session("ws://localhost:8000/ws", "/workspace") as (ws, sid):
            # Send prompts, receive responses
            await send_request(ws, "prompt", {
                "session_id": sid,
                "prompt": [{"type": "text", "text": "Hello"}]
            })
    """
    websocket = await connect_to_server(server_url)
    try:
        session_id = await initialize_session(websocket, cwd)
        yield websocket, session_id
    finally:
        # Issue #13: Close connection (websocket.close() is idempotent)
        try:
            await websocket.close()
        except Exception as exc:
            logger.debug(f"Error closing WebSocket: {exc}")
        logger.info("WebSocket connection closed")
