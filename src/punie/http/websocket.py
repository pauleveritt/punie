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

from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from punie.http.errors import MethodNotFoundError
from punie.http.websocket_client import WebSocketClient

if TYPE_CHECKING:
    from punie.agent.adapter import PunieAgent

logger = logging.getLogger(__name__)

__all__ = ["normalize_acp_params", "resolve_method_name", "websocket_endpoint"]

# Maps ACP slash notation and legacy flat names → canonical handler key used in
# _dispatch_method().  Covers all 12 AGENT_METHODS from punie.acp.meta.
_ACP_TO_HANDLER: dict[str, str] = {
    # ACP slash notation (from AGENT_METHODS values)
    "authenticate": "authenticate",
    "initialize": "initialize",
    "session/cancel": "cancel",
    "session/fork": "fork_session",
    "session/list": "list_sessions",
    "session/load": "load_session",
    "session/new": "new_session",
    "session/prompt": "prompt",
    "session/resume": "resume_session",
    "session/set_config_option": "set_session_config_option",
    "session/set_mode": "set_session_mode",
    "session/set_model": "set_session_model",
    # Legacy flat handler names (backward compat)
    "cancel": "cancel",
    "fork_session": "fork_session",
    "list_sessions": "list_sessions",
    "load_session": "load_session",
    "new_session": "new_session",
    "prompt": "prompt",
    "resume_session": "resume_session",
    "set_session_config_option": "set_session_config_option",
    "set_session_mode": "set_session_mode",
    "set_session_model": "set_session_model",
}

# Known camelCase ACP param keys → snake_case.  Unknown keys pass through.
_CAMEL_TO_SNAKE: dict[str, str] = {
    "sessionId": "session_id",
    "protocolVersion": "protocol_version",
    "clientInfo": "client_info",
    "mcpServers": "mcp_servers",
    "configKey": "config_key",
    "configValue": "config_value",
    "sessionMode": "session_mode",
    "sessionModel": "session_model",
    "forkId": "fork_id",
    "resumeToken": "resume_token",
}


def resolve_method_name(method: str) -> str | None:
    """Resolve an ACP method name to the canonical handler key.

    Accepts both ACP slash notation (``session/prompt``) and legacy flat names
    (``prompt``).  Extension methods prefixed with ``_`` pass through unchanged.

    Args:
        method: Raw method name from a JSON-RPC request.

    Returns:
        Canonical handler key understood by ``_dispatch_method``, or ``None``
        if the method name is not recognised.
    """
    if method.startswith("_"):
        return method
    return _ACP_TO_HANDLER.get(method)


def normalize_acp_params(params: dict) -> dict:
    """Convert known camelCase ACP parameter keys to snake_case.

    Uses an explicit allow-list; unknown keys are passed through unchanged so
    that extension methods and future protocol additions are not silently dropped.

    Args:
        params: Raw params dict from a JSON-RPC message.

    Returns:
        New dict with ACP camelCase keys replaced by their snake_case equivalents.
    """
    return {_CAMEL_TO_SNAKE.get(k, k): v for k, v in params.items()}


async def websocket_endpoint(websocket: WebSocket, agent: PunieAgent) -> None:
    """Handle WebSocket connections for ACP protocol.

    Accepts WebSocket connections, wraps them in WebSocketClient, registers
    with the agent, and dispatches incoming JSON-RPC messages to the agent.

    IMPORTANT: Inbound requests (session/prompt etc.) are dispatched as
    background asyncio tasks so the receive loop stays unblocked.  This is
    required for back-channel ACP calls (terminal/create, terminal/wait_for_exit,
    fs/read_text_file, etc.) to work: those calls are awaited inside the
    background task while the receive loop continues to collect Toad's responses
    and resolve the pending futures via client.handle_response().

    Without background tasks the receive loop would be stuck inside
    _handle_request() and would never call websocket.receive() again, causing
    every _send_request() future to time out after 30 s.

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

    # Track background request tasks so we can cancel them on disconnect
    pending_tasks: set[asyncio.Task] = set()

    try:
        # Listen for messages from client (Issue #18: add timeout for idle connections)
        while True:
            # Receive JSON-RPC message with 30-minute idle timeout
            try:
                raw = await asyncio.wait_for(
                    websocket.receive(), timeout=1800.0
                )

                # Handle different message types
                if raw["type"] == "websocket.disconnect":
                    logger.info(f"Client {client_id} disconnected gracefully")
                    break
                elif raw["type"] == "websocket.receive":
                    if "text" in raw and raw["text"]:
                        data = raw["text"]
                    elif "bytes" in raw and raw["bytes"]:
                        # Toad's jsonrpc.Request.body_json returns bytes; accept
                        # binary frames and decode to str so dispatch works normally.
                        data = raw["bytes"].decode("utf-8", errors="replace")
                        logger.debug(f"Decoded binary frame from {client_id} ({len(raw['bytes'])} bytes)")
                    else:
                        logger.warning(f"Received empty or unrecognised message from {client_id}")
                        continue
                else:
                    logger.warning(f"Unknown message type from {client_id}: {raw['type']}")
                    continue

            except asyncio.TimeoutError:
                logger.info(f"Client {client_id} idle for 30 minutes, disconnecting")
                break

            logger.debug(f"Received message from {client_id}: {data[:200]}...")

            try:
                msg = json.loads(data)
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
            if "result" in msg or "error" in msg:
                # Response to our outbound request — resolve the pending future
                # immediately (fast path, must not be deferred to a task).
                await client.handle_response(msg)
            elif "method" in msg:
                # Inbound request/notification — run as background task so the
                # receive loop stays live and can collect back-channel responses.
                task = asyncio.create_task(
                    _handle_request(websocket, agent, client_id, msg)
                )
                pending_tasks.add(task)
                task.add_done_callback(pending_tasks.discard)
            else:
                logger.warning(f"Invalid JSON-RPC message from {client_id}: {msg}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected")
    except Exception as exc:
        logger.exception(f"Error handling WebSocket {client_id}: {exc}")
    finally:
        # Issue #4: Abort pending requests before cleanup.
        # This resolves any in-flight _send_request() futures with ConnectionError,
        # which causes background request tasks to exit naturally at their next await
        # point without needing explicit cancellation (which can propagate
        # concurrent.futures.CancelledError through executor threads).
        client.abort_pending_requests()
        logger.debug(f"Aborted pending requests for {client_id}, {len(pending_tasks)} tasks in flight")

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
            if websocket.client_state != WebSocketState.CONNECTED:
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
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.warning(
                    f"Client {client_id} disconnected before {method} error could be sent"
                )
                return

            # Use -32601 for unknown methods, -32603 for internal errors
            error_code = getattr(exc, "json_rpc_code", -32603)
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": error_code,
                    "message": "Method not found" if error_code == -32601 else "Internal error",
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
        method: Method name (ACP slash notation or legacy flat form).
        params: Method parameters (camelCase ACP keys are normalised).

    Returns:
        Method result as dict.

    Raises:
        MethodNotFoundError: If method is unknown.
    """
    # Resolve ACP slash notation / legacy flat name → canonical handler key.
    resolved = resolve_method_name(method)
    if resolved is None:
        raise MethodNotFoundError(f"Unknown method: {method}")

    # Normalise camelCase ACP params to snake_case for all dispatch branches.
    params = normalize_acp_params(params)

    if resolved == "initialize":
        result = await agent.initialize(**params)
    elif resolved == "new_session":
        # Inject client_id for session ownership tracking
        result = await agent.new_session(**params, client_id=client_id)
    elif resolved == "load_session":
        result = await agent.load_session(**params)
    elif resolved == "list_sessions":
        result = await agent.list_sessions(**params)
    elif resolved == "set_session_mode":
        result = await agent.set_session_mode(**params)
    elif resolved == "set_session_model":
        result = await agent.set_session_model(**params)
    elif resolved == "fork_session":
        result = await agent.fork_session(**params)
    elif resolved == "resume_session":
        # Session resumption requires client_id for reconnection
        result = await agent.resume_session(**params, client_id=client_id)
    elif resolved == "authenticate":
        result = await agent.authenticate(**params)
    elif resolved == "prompt":
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

        start_time = time.time()
        logger.info("⚙️  Processing request...")

        # Issue #1: Pass calling_client_id for session ownership validation
        result = await agent.prompt(**params, calling_client_id=client_id)

        elapsed = time.time() - start_time
        logger.info(f"✅ Response complete in {elapsed:.2f}s")
    elif resolved == "cancel":
        await agent.cancel(**params)
        result = {}
    elif resolved.startswith("_"):
        # Extension method — strip leading underscore for agent dispatch
        result = await agent.ext_method(resolved[1:], params)
    else:
        raise MethodNotFoundError(f"Unknown method: {method}")

    # Convert Pydantic model to dict (use by_alias=True to match ACP protocol)
    if hasattr(result, "model_dump") and callable(result.model_dump):
        return result.model_dump(mode="json", exclude_none=True, by_alias=True)  # type: ignore[union-attr]
    return result if isinstance(result, dict) else {}
