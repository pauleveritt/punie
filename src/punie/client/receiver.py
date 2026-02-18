"""Shared JSON-RPC message receive loop for Punie clients.

Extracts the duplicated receive-loop pattern from ask_client.py and toad_client.py
into a single reusable function.

Pattern handled:
1. Per-message timeout via asyncio.wait_for
2. Optional aggregate deadline (hard cut-off for entire prompt)
3. JSON decode errors → log + continue
4. session_update notifications → dispatch to on_notification callback
5. Matching response (id == request_id) → return result
6. Connection close → raise ConnectionError
7. Persistent mode (request_id=None) → loop forever, dispatch all notifications
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable

import websockets

from punie.client.timeouts import CLIENT_TIMEOUTS

logger = logging.getLogger(__name__)

__all__ = ["receive_messages"]

#: Callback type: (update_type: str, update_dict: dict) → None
NotificationCallback = Callable[[str, dict[str, Any]], None]


async def receive_messages(
    websocket: Any,
    request_id: str | None = None,
    on_notification: NotificationCallback | None = None,
    timeout: float | None = None,
    aggregate_timeout: float | None = None,
) -> dict[str, Any] | None:
    """Receive JSON-RPC messages and dispatch notifications.

    This is the single receive loop used by all Punie clients.

    Args:
        websocket: WebSocket connection (websockets ClientConnection or compatible).
        request_id: If set, loop exits when a response with this ID arrives.
                    If None, runs until connection closes (persistent mode).
        on_notification: Callback(update_type, update_dict) for session_update
                         notifications. Called synchronously; exceptions are caught
                         and logged but do not crash the loop.
        timeout: Per-message receive timeout in seconds.
                 Defaults to CLIENT_TIMEOUTS.streaming_timeout.
        aggregate_timeout: Hard deadline for the entire call in seconds.
                           Defaults to CLIENT_TIMEOUTS.aggregate_timeout.
                           Only enforced when request_id is set.

    Returns:
        Final response result dict when request_id matches, or None in persistent
        mode (never returns normally — exits via ConnectionError or cancellation).

    Raises:
        RuntimeError: Per-message timeout exceeded.
        RuntimeError: Aggregate deadline exceeded.
        RuntimeError: Server returned an error response.
        ConnectionError: WebSocket connection closed unexpectedly.

    Example (one-shot prompt):
        result = await receive_messages(ws, request_id="req-1", on_notification=cb)

    Example (persistent mode):
        await receive_messages(ws, on_notification=cb)  # runs until close
    """
    # In one-shot mode (request_id set), default to streaming_timeout per message.
    # In persistent mode (request_id=None), default to no per-message timeout.
    if timeout is None and request_id is not None:
        timeout = CLIENT_TIMEOUTS.streaming_timeout
    if aggregate_timeout is None:
        aggregate_timeout = CLIENT_TIMEOUTS.aggregate_timeout

    deadline = time.monotonic() + aggregate_timeout if request_id else None

    while True:
        # Check aggregate deadline
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError(
                    f"Aggregate timeout exceeded after {aggregate_timeout}s"
                )
            recv_timeout = min(timeout, remaining) if timeout is not None else remaining
        else:
            recv_timeout = timeout

        # Receive next message (with or without timeout)
        try:
            if recv_timeout is not None:
                data = await asyncio.wait_for(websocket.recv(), timeout=recv_timeout)
            else:
                data = await websocket.recv()
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"No response from server after {recv_timeout:.0f}s"
            )
        except websockets.exceptions.ConnectionClosed as exc:
            raise ConnectionError(f"Server disconnected: {exc}")

        # JSON decode
        try:
            message = json.loads(data)
        except json.JSONDecodeError as exc:
            logger.warning(f"Invalid JSON from server: {exc}")
            continue

        logger.debug(f"Received message: {message.get('method', 'response')}")

        # Dispatch session/update notifications
        if message.get("method") == "session/update":
            update = message.get("params", {}).get("update", {})
            if not update:
                logger.warning("session_update missing params.update field")
                continue

            update_type = update.get("sessionUpdate", "")
            if update_type and on_notification:
                try:
                    on_notification(update_type, update)
                except Exception as exc:
                    logger.error(
                        f"Error in notification callback: {exc}", exc_info=True
                    )
            continue

        # Check for response matching our request_id
        if request_id is not None and message.get("id") == request_id:
            if "error" in message:
                error = message["error"]
                raise RuntimeError(
                    f"Prompt (req={request_id}) failed: "
                    f"{error.get('message')} (code {error.get('code')})"
                )
            logger.debug(f"Received final response for request {request_id}")
            return message.get("result", {})

        # Other notifications or unknown messages
        if "method" in message:
            logger.debug(f"Ignoring notification: {message['method']}")
        else:
            logger.debug(f"Unknown message format: {message}")
