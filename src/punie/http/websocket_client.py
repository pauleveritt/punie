"""WebSocket client wrapper for ACP protocol.

This module provides a Client protocol implementation that wraps a WebSocket
connection, allowing the agent to communicate with WebSocket clients using
the same interface as stdio clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from starlette.websockets import WebSocket

from punie.acp.schema import (
    AgentMessageChunk,
    AgentPlanUpdate,
    AgentThoughtChunk,
    AvailableCommandsUpdate,
    ConfigOptionUpdate,
    CreateTerminalRequest,
    CreateTerminalResponse,
    CurrentModeUpdate,
    EnvVariable,
    KillTerminalCommandRequest,
    KillTerminalCommandResponse,
    PermissionOption,
    ReadTextFileRequest,
    ReadTextFileResponse,
    ReleaseTerminalRequest,
    ReleaseTerminalResponse,
    RequestPermissionRequest,
    RequestPermissionResponse,
    SessionInfoUpdate,
    SessionNotification,
    TerminalOutputRequest,
    TerminalOutputResponse,
    ToolCallProgress,
    ToolCallStart,
    ToolCallUpdate,
    UserMessageChunk,
    WaitForTerminalExitRequest,
    WaitForTerminalExitResponse,
    WriteTextFileRequest,
    WriteTextFileResponse,
)

logger = logging.getLogger(__name__)

__all__ = ["WebSocketClient"]


class WebSocketClient:
    """Client protocol implementation for WebSocket connections.

    Wraps a Starlette WebSocket and provides the ACP Client protocol interface,
    allowing agents to communicate with WebSocket clients the same way they
    communicate with stdio clients.
    """

    def __init__(self, websocket: WebSocket) -> None:
        """Initialize WebSocket client wrapper.

        Args:
            websocket: Starlette WebSocket connection.
        """
        self._websocket = websocket
        self._pending_requests: dict[str, asyncio.Future[Any]] = {}
        self._connected = True

    async def _send_request(self, method: str, params: dict[str, Any]) -> Any:
        """Send a JSON-RPC request and wait for response.

        Args:
            method: JSON-RPC method name.
            params: Method parameters.

        Returns:
            Response result.

        Raises:
            RuntimeError: If WebSocket is disconnected.
        """
        if not self._connected:
            raise RuntimeError("WebSocket is disconnected")

        # Use UUID to prevent ID reuse/overflow (Issue #5)
        request_id = str(uuid.uuid4())

        # Register future BEFORE sending to prevent race condition (Issue #3)
        future: asyncio.Future[Any] = asyncio.Future()
        self._pending_requests[request_id] = future

        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        try:
            # Send request
            await self._websocket.send_text(json.dumps(message))

            # Wait for response (with timeout)
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Request {request_id} timed out after 30s")
            raise
        finally:
            # Clean up (Issue #10: prevent memory leak)
            self._pending_requests.pop(request_id, None)

    async def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected).

        Args:
            method: JSON-RPC method name.
            params: Method parameters.
        """
        if not self._connected:
            logger.warning(f"Cannot send notification {method}: WebSocket disconnected")
            return

        message = {"jsonrpc": "2.0", "method": method, "params": params}
        try:
            await self._websocket.send_text(json.dumps(message))
        except Exception as exc:
            logger.warning(f"Failed to send notification {method}: {exc}")

    async def session_update(
        self,
        session_id: str,
        update: UserMessageChunk
        | AgentMessageChunk
        | AgentThoughtChunk
        | ToolCallStart
        | ToolCallProgress
        | AgentPlanUpdate
        | AvailableCommandsUpdate
        | CurrentModeUpdate
        | ConfigOptionUpdate
        | SessionInfoUpdate,
        **kwargs: Any,
    ) -> None:
        """Send session update notification to client.

        Args:
            session_id: Session ID.
            update: Update content.
            **kwargs: Additional parameters.
        """
        # Debug logging
        logger.info(f"📤 Sending session_update for session {session_id}")
        logger.info(f"   Update type: {type(update).__name__}")

        # Issue #5: Fix protocol serialization - use by_alias=True for camelCase
        params = SessionNotification(
            session_id=session_id, update=update, field_meta=kwargs or None
        ).model_dump(mode="json", exclude_none=True, by_alias=True)
        await self._send_notification("session_update", params)
        logger.info("   ✅ Notification sent")

    async def request_permission(
        self,
        options: list[PermissionOption],
        session_id: str,
        tool_call: ToolCallUpdate,
        **kwargs: Any,
    ) -> RequestPermissionResponse:
        """Request permission from client.

        Args:
            options: Permission options.
            session_id: Session ID.
            tool_call: Tool call requesting permission.
            **kwargs: Additional parameters.

        Returns:
            Permission response.
        """
        params = RequestPermissionRequest(
            options=options,
            session_id=session_id,
            tool_call=tool_call,
            field_meta=kwargs or None,
        ).model_dump(mode="json", exclude_none=True)
        result = await self._send_request("session_request_permission", params)
        return RequestPermissionResponse(**result)

    async def read_text_file(
        self,
        path: str,
        session_id: str,
        limit: int | None = None,
        line: int | None = None,
        **kwargs: Any,
    ) -> ReadTextFileResponse:
        """Read text file via client.

        Args:
            path: File path.
            session_id: Session ID.
            limit: Optional line limit.
            line: Optional starting line.
            **kwargs: Additional parameters.

        Returns:
            File content response.
        """
        params = ReadTextFileRequest(
            path=path,
            session_id=session_id,
            limit=limit,
            line=line,
            field_meta=kwargs or None,
        ).model_dump(mode="json", exclude_none=True)
        result = await self._send_request("fs_read_text_file", params)
        return ReadTextFileResponse(**result)

    async def write_text_file(
        self, content: str, path: str, session_id: str, **kwargs: Any
    ) -> WriteTextFileResponse | None:
        """Write text file via client.

        Args:
            content: File content.
            path: File path.
            session_id: Session ID.
            **kwargs: Additional parameters.

        Returns:
            Write response or None.
        """
        params = WriteTextFileRequest(
            content=content,
            path=path,
            session_id=session_id,
            field_meta=kwargs or None,
        ).model_dump(mode="json", exclude_none=True)
        result = await self._send_request("fs_write_text_file", params)
        return WriteTextFileResponse(**result) if result else None

    async def create_terminal(
        self,
        command: str,
        session_id: str,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: list[EnvVariable] | None = None,
        output_byte_limit: int | None = None,
        **kwargs: Any,
    ) -> CreateTerminalResponse:
        """Create terminal via client.

        Args:
            command: Command to execute.
            session_id: Session ID.
            args: Command arguments.
            cwd: Working directory.
            env: Environment variables.
            output_byte_limit: Output limit.
            **kwargs: Additional parameters.

        Returns:
            Terminal creation response.
        """
        params = CreateTerminalRequest(
            command=command,
            session_id=session_id,
            args=args,
            cwd=cwd,
            env=env,
            output_byte_limit=output_byte_limit,
            field_meta=kwargs or None,
        ).model_dump(mode="json", exclude_none=True)
        result = await self._send_request("terminal_create", params)
        return CreateTerminalResponse(**result)

    async def terminal_output(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> TerminalOutputResponse:
        """Get terminal output via client.

        Args:
            session_id: Session ID.
            terminal_id: Terminal ID.
            **kwargs: Additional parameters.

        Returns:
            Terminal output response.
        """
        params = TerminalOutputRequest(
            session_id=session_id,
            terminal_id=terminal_id,
            field_meta=kwargs or None,
        ).model_dump(mode="json", exclude_none=True)
        result = await self._send_request("terminal_output", params)
        return TerminalOutputResponse(**result)

    async def release_terminal(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> ReleaseTerminalResponse | None:
        """Release terminal via client.

        Args:
            session_id: Session ID.
            terminal_id: Terminal ID.
            **kwargs: Additional parameters.

        Returns:
            Release response or None.
        """
        params = ReleaseTerminalRequest(
            session_id=session_id,
            terminal_id=terminal_id,
            field_meta=kwargs or None,
        ).model_dump(mode="json", exclude_none=True)
        result = await self._send_request("terminal_release", params)
        return ReleaseTerminalResponse(**result) if result else None

    async def wait_for_terminal_exit(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> WaitForTerminalExitResponse:
        """Wait for terminal exit via client.

        Args:
            session_id: Session ID.
            terminal_id: Terminal ID.
            **kwargs: Additional parameters.

        Returns:
            Terminal exit response.
        """
        params = WaitForTerminalExitRequest(
            session_id=session_id,
            terminal_id=terminal_id,
            field_meta=kwargs or None,
        ).model_dump(mode="json", exclude_none=True)
        result = await self._send_request("terminal_wait_for_exit", params)
        return WaitForTerminalExitResponse(**result)

    async def kill_terminal(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> KillTerminalCommandResponse | None:
        """Kill terminal via client.

        Args:
            session_id: Session ID.
            terminal_id: Terminal ID.
            **kwargs: Additional parameters.

        Returns:
            Kill response or None.
        """
        params = KillTerminalCommandRequest(
            session_id=session_id,
            terminal_id=terminal_id,
            field_meta=kwargs or None,
        ).model_dump(mode="json", exclude_none=True)
        result = await self._send_request("terminal_kill", params)
        return KillTerminalCommandResponse(**result) if result else None

    async def discover_tools(self, session_id: str, **kwargs: Any) -> dict[str, Any]:
        """Discover tools via client.

        Args:
            session_id: Session ID.
            **kwargs: Additional parameters.

        Returns:
            Tool catalog.
        """
        params = {"session_id": session_id, **kwargs}
        result = await self._send_request("_discover_tools", params)
        return result

    async def ext_method(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Call extension method.

        Args:
            method: Method name.
            params: Method parameters.

        Returns:
            Method result.
        """
        return await self._send_request(f"_{method}", params)

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send extension notification.

        Args:
            method: Method name.
            params: Method parameters.
        """
        await self._send_notification(f"_{method}", params)

    def on_connect(self, conn: Any) -> None:
        """Called when connection is established (no-op for WebSocket)."""
        pass

    async def handle_response(self, response: dict[str, Any]) -> None:
        """Handle JSON-RPC response from client.

        Args:
            response: JSON-RPC response message.
        """
        request_id = response.get("id")
        if request_id is None:
            return

        future = self._pending_requests.get(request_id)
        if not future or future.done():
            return

        if "result" in response:
            future.set_result(response["result"])
        elif "error" in response:
            error = response["error"]
            # Extract full error details (Issue #15)
            error_code = error.get("code", -1)
            error_message = error.get("message", "Unknown")
            error_data = error.get("data")
            exc = RuntimeError(
                f"JSON-RPC error [{error_code}]: {error_message}"
                + (f" - {error_data}" if error_data else "")
            )
            future.set_exception(exc)

    def abort_pending_requests(self) -> None:
        """Abort all pending requests (Issue #4).

        Called when WebSocket disconnects to prevent 30s hangs.
        """
        self._connected = False
        for request_id, future in list(self._pending_requests.items()):
            if not future.done():
                future.set_exception(
                    ConnectionError("WebSocket disconnected while waiting for response")
                )
        self._pending_requests.clear()
        logger.info(f"Aborted {len(self._pending_requests)} pending requests")
