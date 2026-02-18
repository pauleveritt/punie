"""Proper Toad WebSocket agent module.

Provides a factory function that returns a WebSocket-enabled Toad agent class.
The class definition is deferred via a factory to avoid circular imports with
the toad package (toad.acp.agent → toad.acp.messages → toad.acp.agent.Mode).

Usage (in scripts or tests):
    from punie.toad.agent import create_websocket_agent_class

    WebSocketToadAgent = create_websocket_agent_class("ws://localhost:8000/ws")
    agent = WebSocketToadAgent(project_root=Path("."), agent=agent_data, session_id=None)
"""

from __future__ import annotations

import concurrent.futures
import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

__all__ = ["classify_jsonrpc_message", "create_websocket_agent_class"]


def classify_jsonrpc_message(
    message: dict,
) -> Literal["response", "request", "notification", "invalid"]:
    """Classify a JSON-RPC message by its structure.

    Args:
        message: Parsed JSON-RPC message dict.

    Returns:
        "response" if it has result/error keys,
        "request" if it has method + id,
        "notification" if it has method but no id,
        "invalid" otherwise.
    """
    if "result" in message or "error" in message:
        return "response"
    if "method" in message:
        return "request" if "id" in message else "notification"
    return "invalid"


def create_websocket_agent_class(
    server_url: str = "ws://localhost:8000/ws",
    capture: object = None,
) -> type:
    """Create a WebSocket-enabled Toad agent class.

    Imports Toad components at call time to break the circular import chain:
        punie.toad.agent → toad.acp.agent → toad.acp.messages → toad.acp.agent.Mode

    Solution: import toad.widgets.conversation BEFORE toad.acp.agent to satisfy
    toad.acp.agent.Mode's import of toad.widgets.conversation.

    Args:
        server_url: Default WebSocket URL used when agent is instantiated without
                    an explicit URL argument.

    Returns:
        WebSocketToadAgent class ready for instantiation.

    Example:
        WebSocketToadAgent = create_websocket_agent_class("ws://localhost:8000/ws")
        agent = WebSocketToadAgent(
            project_root=Path("/workspace"),
            agent={"name": "Punie", "run_command": {"*": "punie"}},
            session_id=None,
        )
    """
    # Capture is referenced via closure — the class does not own it
    _capture = capture

    import asyncio
    import json

    # CRITICAL: Import widgets.conversation BEFORE toad.acp.agent to break circular import
    import toad.widgets.conversation  # noqa: F401 — side-effect import required
    import toad.acp.agent
    from toad import jsonrpc
    from toad.agent import AgentFail, AgentReady
    from toad.acp.api import API

    from punie.client.toad_client import create_toad_session

    class WebSocketToadAgent(toad.acp.agent.Agent):
        """WebSocket-enabled Toad agent.

        Extends Toad's Agent to use WebSocket transport instead of
        stdio/subprocess. All of Toad's UI logic, message handling, and
        JSON-RPC infrastructure is reused.

        Key differences from parent:
        - No subprocess management
        - WebSocket connection instead of stdin/stdout
        - A single cached ThreadPoolExecutor for the agent lifetime

        Args:
            project_root: Project root path.
            agent: Agent configuration dict.
            session_id: Existing session ID (None for new session).
            session_pk: Database primary key for session.
            server_url: Punie server WebSocket URL.
        """

        def __init__(
            self,
            project_root: Any,
            agent: Any,
            session_id: str | None,
            session_pk: Any = None,
            server_url: str = server_url,
        ) -> None:
            super().__init__(project_root, agent, session_id, session_pk)
            self.server_url = server_url
            self._websocket: Any = None
            self._punie_session_id: str | None = None
            # Single executor for the agent lifetime (not per-send)
            self._executor: concurrent.futures.ThreadPoolExecutor | None = None

        def send(self, request: jsonrpc.Request) -> None:
            """Send request via WebSocket (synchronous API, async execution).

            CRITICAL: This method MUST be synchronous to match the parent
            Agent.send() contract. The async I/O runs in a cached thread
            executor to avoid creating a new executor on every send().
            """
            if self._websocket is None:
                logger.error("Cannot send: WebSocket not connected")
                return

            logger.debug(f"[client→server] {request.body}")

            if self._executor is None:
                self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

            def _run_async_send() -> None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # body_json returns bytes; decode to str so websockets sends a
                # text frame instead of a binary frame.  The server's receive()
                # handler checks for "text" in the Starlette message dict and
                # silently drops binary frames with a WARNING log.
                body = request.body_json
                if isinstance(body, bytes):
                    body = body.decode("utf-8")
                try:
                    loop.run_until_complete(self._websocket.send(body))
                except Exception as exc:
                    logger.error(f"WebSocket send failed: {exc}")
                    self.post_message(AgentFail("Connection lost", str(exc)))
                finally:
                    loop.close()

            future = self._executor.submit(_run_async_send)
            try:
                from punie.client.timeouts import CLIENT_TIMEOUTS
                future.result(timeout=CLIENT_TIMEOUTS.send_timeout)
            except concurrent.futures.TimeoutError:
                logger.error("WebSocket send timed out")
            except Exception as exc:
                logger.error(f"Failed to send: {exc}")

        async def stop(self) -> None:
            """Stop the agent and close WebSocket + executor."""
            await super().stop()

            # Shut down executor
            if self._executor is not None:
                self._executor.shutdown(wait=False)
                self._executor = None

            # Close WebSocket
            if self._websocket is not None:
                try:
                    await self._websocket.close()
                except Exception as exc:
                    logger.warning(f"Error closing WebSocket: {exc}")
                finally:
                    self._websocket = None

        async def acp_initialize(self) -> None:
            """No-op: Punie handshake already completed in create_toad_session().

            The parent's acp_initialize() sends an ACP initialize request and awaits
            a future that is resolved by API.process_response(). But _listen_loop()
            routes all inbound messages to toad.jsonrpc.Server which has no dispatch
            method, so the response is dropped and the future never resolves.

            Since create_toad_session() already performed the full Punie handshake
            (initialize + new_session), we skip the redundant ACP call here and just
            copy the capabilities that the parent would have set from the response.
            """
            logger.debug("acp_initialize: skipping (Punie handshake already done)")
            # Set agent_capabilities from the server info we already received
            # The parent reads agentCapabilities from the initialize response;
            # we seed it with a safe default so downstream code doesn't KeyError.
            if not hasattr(self, "agent_capabilities") or not self.agent_capabilities:
                self.agent_capabilities = {}

        async def acp_new_session(self) -> None:
            """Set session_id from the already-established Punie session.

            The parent's acp_new_session() sends session/new and awaits a future.
            Same broken routing problem as acp_initialize(). We already have the
            session ID from create_toad_session(), so just copy it here.
            """
            logger.debug(
                f"acp_new_session: using existing session {self._punie_session_id}"
            )
            self.session_id = self._punie_session_id

        async def _run_agent(self) -> None:
            """Override parent's _run_agent to skip subprocess creation."""
            logger.debug("_run_agent called — skipping subprocess, scheduling run()")
            self._task = asyncio.create_task(self.run())

        async def run(self) -> None:
            """Main agent logic — connect to Punie server via WebSocket."""
            logger.debug("run() started")
            if _capture is not None:
                _capture.phase("run_start")
            try:
                logger.debug("Creating WebSocket session...")
                self._websocket, self._punie_session_id = await create_toad_session(
                    self.server_url, str(self.project_root_path), capture=_capture
                )
                logger.debug(
                    f"WebSocket connected! Session ID: {self._punie_session_id}"
                )

                if _capture is not None:
                    _capture.phase("listen_loop_start")
                self._agent_task = asyncio.create_task(self._listen_loop())

                logger.debug("Calling acp_initialize()...")
                if _capture is not None:
                    _capture.phase("acp_initialize_start")
                await self.acp_initialize()
                logger.debug("acp_initialize() complete")
                if _capture is not None:
                    _capture.phase("acp_initialize_done")

                if self.session_id is None:
                    logger.debug("Calling acp_new_session()...")
                    if _capture is not None:
                        _capture.phase("acp_new_session_start")
                    await self.acp_new_session()
                    logger.debug("acp_new_session() complete")
                    if _capture is not None:
                        _capture.phase("acp_new_session_done")
                else:
                    if not self.agent_capabilities.get("loadSession", False):
                        if _capture is not None:
                            _capture.phase("resume_not_supported")
                        self.post_message(
                            AgentFail(
                                "Resume not supported",
                                f"{self._agent_data['name']} does not support resuming.",
                            )
                        )
                        return
                    if _capture is not None:
                        _capture.phase("acp_load_session_start")
                    await self.acp_load_session()
                    if _capture is not None:
                        _capture.phase("acp_load_session_done")

                logger.debug("Posting AgentReady message...")
                if _capture is not None:
                    _capture.phase("agent_ready")
                self.post_message(AgentReady())
                logger.debug("Agent fully initialized and ready!")

            except Exception as exc:
                logger.error(f"Failed to connect: {exc}")
                if _capture is not None:
                    _capture.on_error("run", exc)
                self.post_message(AgentFail("Connection failed", str(exc)))

        async def _listen_loop(self) -> None:
            """Background task to listen for WebSocket messages."""
            if self._websocket is None:
                return

            async def _handle_server_call(msg: dict) -> None:
                """Dispatch a method call/notification from Punie to Toad's server.

                Punie sends two kinds of inbound messages:
                  - Notifications (no id): session/update with streaming chunks
                  - Requests (with id): session/request_permission awaiting user input

                self.server.call() dispatches to the @jsonrpc.expose methods on this
                class (rpc_session_update, rpc_request_permission, etc.). For requests
                that expect a response (permission), the result is sent back to Punie.
                """
                try:
                    result = await self.server.call(msg)
                    if result is not None and self._websocket is not None:
                        await self._websocket.send(json.dumps(result))
                except Exception as exc:
                    logger.error(f"Error dispatching server call: {exc}")

            try:
                while True:
                    try:
                        data = await self._websocket.recv()
                    except Exception as exc:
                        error_str = str(exc)
                        if "sent 1000" in error_str and "received 1000" in error_str:
                            logger.info(f"WebSocket closed normally: {exc}")
                            break
                        else:
                            logger.error(f"WebSocket receive error: {exc}")
                            self.post_message(AgentFail("Connection lost", str(exc)))
                            break

                    try:
                        message = json.loads(data)
                        logger.debug(f"[server→client] {data[:200]}")
                        if isinstance(message, dict):
                            msg_type = classify_jsonrpc_message(message)
                            if _capture is not None:
                                destination = (
                                    "API.process_response"
                                    if msg_type == "response"
                                    else "server.call"
                                )
                                _capture.on_route(
                                    msg_type, message.get("method"), destination
                                )
                            if msg_type == "response":
                                # Response to a request Toad made (session/prompt, etc.)
                                # Resolves the future in acp_session_prompt().wait()
                                API.process_response(message)
                            elif msg_type in ("request", "notification"):
                                # Notification or request from Punie (session/update, etc.)
                                asyncio.create_task(_handle_server_call(message))
                            else:
                                logger.warning(f"Invalid JSON-RPC message: {data[:200]}")
                        else:
                            logger.warning(f"Non-dict JSON message: {data[:200]}")
                    except json.JSONDecodeError as exc:
                        logger.warning(f"Invalid JSON: {exc}")
                    except Exception as exc:
                        logger.error(f"Error handling message: {exc}")

            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.error(f"Listen loop error: {exc}")

    return WebSocketToadAgent
