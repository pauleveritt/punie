"""WebSocket endpoint for ACP protocol.

This module provides a WebSocket endpoint that allows multiple clients to
connect to the Punie agent simultaneously, each maintaining independent
sessions over persistent WebSocket connections.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING, Any

from starlette.websockets import WebSocket, WebSocketDisconnect

from punie.http.websocket_client import WebSocketClient

if TYPE_CHECKING:
    from punie.agent.adapter import PunieAgent

logger = logging.getLogger(__name__)

__all__ = ["websocket_endpoint"]


async def websocket_endpoint(websocket: WebSocket, agent: PunieAgent) -> None:
    """Handle WebSocket connections for ACP protocol.

    Accepts WebSocket connections, wraps them in WebSocketClient, registers
    with the agent, and dispatches incoming JSON-RPC messages to the agent.

    Args:
        websocket: Starlette WebSocket connection.
        agent: PunieAgent instance to handle requests.
    """
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    # Wrap WebSocket in Client protocol implementation
    client = WebSocketClient(websocket)

    # Issue #7: Handle registration failure
    try:
        client_id = await agent.register_client(client)
        logger.info(f"Registered WebSocket client {client_id}")
    except Exception as exc:
        logger.error(f"Failed to register client: {exc}")
        await websocket.close(code=1011, reason="Registration failed")
        return

    try:
        # Listen for messages from client (Issue #18: add timeout for idle connections)
        while True:
            # Receive JSON-RPC message with 5-minute idle timeout
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=300.0
                )
            except asyncio.TimeoutError:
                logger.info(f"Client {client_id} idle for 5 minutes, disconnecting")
                break

            logger.debug(f"Received message from {client_id}: {data[:200]}...")

            try:
                message = json.loads(data)
            except json.JSONDecodeError as exc:
                logger.warning(f"Invalid JSON from {client_id}: {exc}")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error",
                        "data": str(exc),
                    },
                    "id": None,
                }
                # Issue #12: Handle send_text exceptions
                try:
                    await websocket.send_text(json.dumps(error_response))
                except WebSocketDisconnect:
                    logger.debug(f"Client {client_id} disconnected during error send")
                    break
                except Exception as send_exc:
                    logger.warning(
                        f"Failed to send error response to {client_id}: {send_exc}"
                    )
                    break
                continue

            # Dispatch message (Issue #6: check responses before requests)
            if "result" in message or "error" in message:
                # Response to our request - forward to WebSocketClient
                await client.handle_response(message)
            elif "method" in message:
                # Request from client - dispatch to agent
                await _handle_request(websocket, agent, client_id, message)
            else:
                logger.warning(f"Invalid JSON-RPC message from {client_id}: {message}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected")
    except Exception as exc:
        logger.exception(f"Error handling WebSocket {client_id}: {exc}")
    finally:
        # Issue #4: Abort pending requests before cleanup
        client.abort_pending_requests()
        logger.debug(f"Aborted pending requests for {client_id}")

        # Cleanup: unregister client and close owned sessions (now async)
        await agent.unregister_client(client_id)
        logger.info(f"Cleaned up WebSocket client {client_id}")


async def _handle_request(
    websocket: WebSocket, agent: PunieAgent, client_id: str, message: dict
) -> None:
    """Handle JSON-RPC request from client.

    Args:
        websocket: WebSocket connection.
        agent: PunieAgent instance.
        client_id: Client ID for session tracking.
        message: JSON-RPC request message.
    """
    method = message.get("method")
    params = message.get("params", {})
    request_id = message.get("id")

    if not method:
        logger.warning(f"Missing method in message from {client_id}")
        return

    logger.debug(f"Dispatching {method} from {client_id}")

    try:
        # Dispatch to agent method
        result = await _dispatch_method(agent, client_id, method, params)

        # Send response (Issue #12: handle send exceptions)
        if request_id is not None:
            # Issue #8: Check connection state before sending
            if websocket.client_state.value != 1:  # 1 = CONNECTED
                logger.warning(
                    f"Client {client_id} disconnected before {method} response could be sent"
                )
                return

            response = {"jsonrpc": "2.0", "id": request_id, "result": result}
            try:
                await websocket.send_text(json.dumps(response))
                logger.debug(f"Sent response for {method} to {client_id}")
            except WebSocketDisconnect:
                logger.debug(f"Client {client_id} disconnected before response sent")
            except Exception as send_exc:
                logger.warning(
                    f"Failed to send response to {client_id}: {send_exc}"
                )

    except Exception as exc:
        logger.exception(f"Error executing {method}: {exc}")

        if request_id is not None:
            # Issue #8: Check connection state before sending error
            if websocket.client_state.value != 1:  # 1 = CONNECTED
                logger.warning(
                    f"Client {client_id} disconnected before {method} error could be sent"
                )
                return

            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(exc),
                },
            }
            # Issue #12: Handle send exceptions
            try:
                await websocket.send_text(json.dumps(error_response))
            except WebSocketDisconnect:
                logger.debug(f"Client {client_id} disconnected before error sent")
            except Exception as send_exc:
                logger.warning(
                    f"Failed to send error response to {client_id}: {send_exc}"
                )


async def _dispatch_method(
    agent: PunieAgent, client_id: str, method: str, params: dict[str, Any]
) -> dict[str, Any]:
    """Dispatch method call to agent.

    Args:
        agent: PunieAgent instance.
        client_id: Client ID for session tracking.
        method: Method name.
        params: Method parameters.

    Returns:
        Method result as dict.

    Raises:
        RuntimeError: If method is unknown.
    """
    # Map JSON-RPC method names to agent methods
    if method == "initialize":
        result = await agent.initialize(**params)
    elif method == "new_session":
        # Inject client_id for session ownership tracking
        result = await agent.new_session(**params, client_id=client_id)
    elif method == "load_session":
        result = await agent.load_session(**params)
    elif method == "list_sessions":
        result = await agent.list_sessions(**params)
    elif method == "set_session_mode":
        result = await agent.set_session_mode(**params)
    elif method == "set_session_model":
        result = await agent.set_session_model(**params)
    elif method == "fork_session":
        result = await agent.fork_session(**params)
    elif method == "resume_session":
        # Session resumption requires client_id for reconnection
        result = await agent.resume_session(**params, client_id=client_id)
    elif method == "authenticate":
        result = await agent.authenticate(**params)
    elif method == "prompt":
        # Log prompt for user feedback
        prompt_content = params.get("prompt", [])
        prompt_text = ""
        for block in prompt_content:
            if isinstance(block, dict) and block.get("type") == "text":
                prompt_text += block.get("text", "")

        logger.info("=" * 60)
        logger.info("📝 PROMPT RECEIVED")
        logger.info("=" * 60)
        logger.info(f"Session: {params.get('session_id', 'unknown')}")
        logger.info(f"Question: {prompt_text[:100]}{'...' if len(prompt_text) > 100 else ''}")
        logger.info("=" * 60)

        # Start timing
        start_time = time.time()

        logger.info("⚙️  Processing request...")

        # Issue #1: Pass calling_client_id for session ownership validation
        result = await agent.prompt(**params, calling_client_id=client_id)

        # Log completion with elapsed time
        elapsed = time.time() - start_time
        logger.info(f"✅ Response complete in {elapsed:.2f}s")
    elif method == "cancel":
        await agent.cancel(**params)
        result = {}
    elif method.startswith("_"):
        # Extension method
        result = await agent.ext_method(method[1:], params)
    else:
        raise RuntimeError(f"Unknown method: {method}")

    # Convert Pydantic model to dict (use by_alias=True to match ACP protocol)
    if hasattr(result, "model_dump") and callable(result.model_dump):
        return result.model_dump(mode="json", exclude_none=True, by_alias=True)  # type: ignore[union-attr]
    return result if isinstance(result, dict) else {}
