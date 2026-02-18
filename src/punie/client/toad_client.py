"""Toad WebSocket client for browser-based frontend integration.

This module provides a WebSocket client optimized for the Toad browser UI,
with streaming support and tool execution visibility via callbacks.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Callable

from websockets.asyncio.client import ClientConnection

from punie.client.connection import (
    connect_to_server,
    initialize_session,
    punie_session,
)
from punie.client.receiver import receive_messages

logger = logging.getLogger(__name__)

__all__ = [
    "run_toad_client",
    "send_prompt_stream",
    "handle_tool_update",
    "create_toad_session",
]


async def create_toad_session(
    server_url: str,
    cwd: str,
    capture: Any = None,
) -> tuple[ClientConnection, str]:
    """Create session and return (websocket, session_id).

    This is a non-context-manager version of punie_session() for cases where
    the caller wants explicit control over the WebSocket lifecycle.

    Args:
        server_url: WebSocket URL (e.g., ws://localhost:8000/ws)
        cwd: Current working directory for session
        capture: Optional ToadCapture for diagnostic logging. When provided,
                 the returned websocket is wrapped with DiagnosticWebSocket so
                 all messages during initialize_session() and beyond are recorded.

    Returns:
        Tuple of (websocket, session_id). If capture is provided, websocket is
        a DiagnosticWebSocket wrapping the real connection.

    Raises:
        websockets.exceptions.WebSocketException: If connection fails
        RuntimeError: If handshake fails

    Example:
        websocket, session_id = await create_toad_session(
            "ws://localhost:8000/ws",
            "/path/to/workspace"
        )
        try:
            # Use websocket...
        finally:
            await websocket.close()

    Note:
        Caller is responsible for closing the websocket when done.
    """
    logger.info(f"Creating Toad session: {server_url}")
    if capture is not None:
        capture.phase("connect_start", server_url=server_url)
    websocket = await connect_to_server(server_url)
    if capture is not None:
        capture.phase("connect_done")
        websocket = capture.wrap(websocket)  # type: ignore[assignment]
    try:
        if capture is not None:
            capture.phase("initialize_start")
        session_id = await initialize_session(websocket, cwd)  # type: ignore[arg-type]
        if capture is not None:
            capture.phase("initialize_done", session_id=session_id)
        logger.info(f"Toad session created: {session_id}")
        return websocket, session_id  # type: ignore[return-value]
    except Exception as exc:
        if capture is not None:
            capture.on_error("create_toad_session", exc)
        # Clean up on failure
        try:
            await websocket.close()
        except Exception as close_exc:
            logger.debug(f"Error closing WebSocket after failed handshake: {close_exc}")
        raise


async def send_prompt_stream(
    websocket: ClientConnection,
    session_id: str,
    prompt: str,
    on_chunk: Callable[[str, dict[str, Any]], None],
) -> dict[str, Any]:
    """Send prompt and stream updates via callback.

    Args:
        websocket: Connected WebSocket client
        session_id: Active session ID from create_toad_session
        prompt: User prompt text
        on_chunk: Callback(update_type, content) invoked for each update

    Returns:
        Final response result dict

    Raises:
        RuntimeError: If prompt execution times out or fails
        ConnectionError: If WebSocket disconnects during streaming

    Example:
        def on_chunk(update_type, content):
            if update_type == "agent_message_chunk":
                print(content["text"])
            elif update_type == "tool_call":
                print(f"Tool: {content['title']}")

        result = await send_prompt_stream(ws, sid, "Hello!", on_chunk)

    Streaming Pattern:
        1. Send prompt request with UUID request_id
        2. Use shared receive_messages() loop
        3. For each session_update notification call on_chunk(update_type, content)
        4. Exit on response with matching request_id
        5. Return final result
    """
    # Send prompt request (UUID to prevent collision)
    request_id = str(uuid.uuid4())
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "prompt",
        "params": {
            "session_id": session_id,
            "prompt": [{"type": "text", "text": prompt}],
        },
    }
    logger.debug(f"Sending prompt request (id={request_id})")
    await websocket.send(json.dumps(request))

    def on_notification(update_type: str, update: dict[str, Any]) -> None:
        try:
            on_chunk(update_type, update)
        except Exception as exc:
            logger.error(f"Error in on_chunk callback: {exc}", exc_info=True)

    result = await receive_messages(
        websocket,
        request_id=request_id,
        on_notification=on_notification,
    )
    return result or {}


async def handle_tool_update(
    update: dict[str, Any],
    on_tool_call: Callable[[str, dict[str, Any]], None],
) -> None:
    """Handle tool call updates and dispatch to callback.

    This is a convenience helper that parses tool_call and tool_call_update
    notifications and extracts the relevant fields for UI display.

    Args:
        update: session_update notification dict (from on_chunk callback)
        on_tool_call: Callback(tool_call_id, tool_data) for tool execution

    Update types handled:
        - "tool_call" (ToolCallStart) - Tool execution begins
        - "tool_call_update" (ToolCallProgress) - Tool execution progress

    Extracted fields:
        - tool_call_id (str): Unique identifier for this tool execution
        - title (str): Human-readable tool description
        - kind (str): Tool type ("read", "edit", "execute", "search", etc.)
        - status (str): Execution status ("pending", "in_progress", "completed", "failed")
        - content (list): List of ContentBlock (text, code, diff, etc.)
        - locations (list): List of {path, line} for affected files
        - raw_input (Any): Tool input arguments
        - raw_output (Any): Tool execution result

    Example:
        def on_chunk(update_type, content):
            if update_type in ("tool_call", "tool_call_update"):
                await handle_tool_update(content, on_tool_call)

        def on_tool_call(tool_call_id, tool_data):
            print(f"Tool {tool_call_id}: {tool_data['title']}")
            print(f"  Status: {tool_data['status']}")

    Note:
        This is async for consistency with other client functions, even though
        it doesn't perform any async operations. This allows for future
        extensions (e.g., fetching additional tool metadata).
    """
    update_type = update.get("sessionUpdate")

    # Only handle tool-related updates
    if update_type not in ("tool_call", "tool_call_update"):
        return

    # Extract tool call fields
    tool_call_id = update.get("tool_call_id")
    if not tool_call_id:
        logger.warning("Tool update missing tool_call_id field")
        return

    # Build tool data dict with all relevant fields
    tool_data = {
        "title": update.get("title"),
        "kind": update.get("kind"),
        "status": update.get("status"),
        "content": update.get("content", []),
        "locations": update.get("locations", []),
        "raw_input": update.get("raw_input"),
        "raw_output": update.get("raw_output"),
    }

    # Call callback with tool_call_id and extracted data
    try:
        on_tool_call(tool_call_id, tool_data)
    except Exception as exc:
        logger.error(f"Error in on_tool_call callback: {exc}", exc_info=True)
        # Don't propagate - callback errors are caller's problem


async def run_toad_client(
    server_url: str,
    cwd: str,
    on_update: Callable[[dict[str, Any]], None],
) -> None:
    """Run Toad WebSocket client with persistent connection.

    This is the main entry point for Toad frontend integration. It maintains
    a persistent WebSocket connection and routes all session_update notifications
    to the provided callback.

    Args:
        server_url: WebSocket URL (e.g., ws://localhost:8000/ws)
        cwd: Current working directory for session
        on_update: Callback(update) invoked for each session_update notification

    Raises:
        websockets.exceptions.WebSocketException: If connection fails
        RuntimeError: If handshake fails

    Example:
        def on_update(update):
            update_type = update.get("sessionUpdate")
            if update_type == "agent_message_chunk":
                content = update.get("content")
                if content and content.get("type") == "text":
                    print(content["text"])

        await run_toad_client(
            "ws://localhost:8000/ws",
            "/workspace",
            on_update
        )

    Pattern:
        1. Connect using punie_session context manager
        2. Wait for messages using shared receive_messages() in persistent mode
        3. Route session_update notifications to callback
        4. Maintain connection until explicitly closed (KeyboardInterrupt, etc.)

    Note:
        This function does not return until the connection is closed.
        Use asyncio.create_task() if you need to run it in the background.
    """
    logger.info(f"Starting Toad client: {server_url}")

    async with punie_session(server_url, cwd) as (websocket, session_id):
        logger.info(f"Toad client connected: session_id={session_id}")

        def on_notification(update_type: str, update: dict[str, Any]) -> None:
            try:
                on_update(update)
            except Exception as exc:
                logger.error(f"Error in on_update callback: {exc}", exc_info=True)

        try:
            # Persistent mode: receive_messages loops until connection closes
            await receive_messages(
                websocket,
                request_id=None,  # persistent mode
                on_notification=on_notification,
                timeout=None,  # no per-message timeout in persistent mode
            )
        except ConnectionError as exc:
            logger.info(f"Toad client connection closed: {exc}")
        except KeyboardInterrupt:
            logger.info("Toad client interrupted by user")
        except Exception as exc:
            logger.error(f"Toad client error: {exc}", exc_info=True)
            raise
        finally:
            logger.info("Toad client shutting down")
