"""WebSocket-enabled Toad agent subclass.

⚠️  WARNING: This module causes circular imports with toad.acp.agent and should NOT be imported!

The actual implementation is defined inline in scripts/run_toad_websocket.py to avoid
circular import issues. This file is kept for reference only.

Circular import chain:
    punie.toad.websocket_agent → toad.acp.agent → toad.acp.messages → toad.acp.agent (Mode)

Solution: Define WebSocketToadAgent inline in the launcher script after Toad is fully loaded.

See: scripts/run_toad_websocket.py for the working implementation
See: docs/toad-websocket-subclass.md for architecture details
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from websockets.asyncio.client import ClientConnection

from punie.client.toad_client import create_toad_session
from toad import jsonrpc
from toad.acp.agent import Agent as ToadAgent
from toad.agent import AgentFail, AgentReady
from toad.agent_schema import Agent as AgentData

logger = logging.getLogger(__name__)

__all__ = ["WebSocketToadAgent"]


class WebSocketToadAgent(ToadAgent):
    """WebSocket-enabled Toad agent.

    Extends Toad's Agent class to use WebSocket transport instead of stdio/subprocess.
    Reuses all of Toad's UI logic, message handling, and JSON-RPC infrastructure.

    Key differences from parent:
    - No subprocess management
    - WebSocket connection instead of stdin/stdout
    - Direct server communication instead of command execution

    Example:
        >>> agent = WebSocketToadAgent(
        ...     project_root=Path("/workspace"),
        ...     agent_data={"name": "Punie", "run_command": None},
        ...     session_id=None,
        ...     server_url="ws://localhost:8000/ws"
        ... )
        >>> await agent.run()
    """

    def __init__(
        self,
        project_root: Path,
        agent: AgentData,
        session_id: str | None,
        session_pk: int | None = None,
        server_url: str = "ws://localhost:8000/ws",
    ) -> None:
        """Initialize WebSocket agent.

        Args:
            project_root: Project root path
            agent: Agent configuration data
            session_id: Existing session ID (None for new session)
            session_pk: Database primary key for session
            server_url: Punie server WebSocket URL
        """
        # Initialize parent (sets up JSON-RPC, messages, etc.)
        super().__init__(project_root, agent, session_id, session_pk)

        # WebSocket-specific state
        self.server_url = server_url
        self._websocket: ClientConnection | None = None
        self._punie_session_id: str | None = None

        # Override command to None (we don't spawn subprocess)
        # This prevents parent's subprocess logic from running

    @property
    def command(self) -> str | None:
        """Override to return None - we don't use subprocess."""
        return None

    def send(self, request: jsonrpc.Request) -> None:
        """Send a request to the agent via WebSocket.

        Overrides parent's stdin-based send to use WebSocket.

        Args:
            request: JSONRPC request object
        """
        if self._websocket is None:
            logger.error("Cannot send request: WebSocket not connected")
            return

        self.log(f"[client] {request.body}")

        # Send via WebSocket instead of stdin
        try:
            # Use asyncio.create_task to avoid blocking
            asyncio.create_task(self._send_async(request))
        except Exception as e:
            logger.error(f"Failed to send request: {e}")

    async def _send_async(self, request: jsonrpc.Request) -> None:
        """Async helper to send request via WebSocket."""
        if self._websocket is None:
            return

        try:
            # Send JSON-RPC message as bytes
            await self._websocket.send(request.body_json)
        except Exception as e:
            logger.error(f"WebSocket send failed: {e}")
            self.post_message(
                AgentFail(
                    "Connection lost",
                    f"Failed to send request to Punie server: {e}",
                )
            )

    async def stop(self) -> None:
        """Stop the agent and close WebSocket connection.

        Overrides parent's process termination with WebSocket cleanup.
        """
        # Call parent's stop (handles database updates)
        await super().stop()

        # Close WebSocket
        if self._websocket is not None:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            finally:
                self._websocket = None
                self._punie_session_id = None

    async def run(self) -> None:
        """Main agent logic with WebSocket connection.

        Overrides parent's subprocess-based run with WebSocket connection.
        """
        try:
            # Connect to Punie server via WebSocket
            logger.info(f"Connecting to Punie server at {self.server_url}")
            self._websocket, self._punie_session_id = await create_toad_session(
                self.server_url, str(self.project_root_path)
            )
            logger.info(f"Connected with session_id={self._punie_session_id}")

            # Start listening for messages in background
            self._agent_task = asyncio.create_task(self._listen_loop())

            # Reuse parent's initialization logic (ACP handshake, session setup)
            # This calls acp_initialize(), acp_new_session(), etc.
            # Parent's logic uses self.send() which we've overridden for WebSocket
            try:
                # Initialize ACP protocol
                await self.acp_initialize()

                if self.session_id is None:
                    # Create new session
                    await self.acp_new_session()
                else:
                    # Load existing session
                    if not self.agent_capabilities.get("loadSession", False):
                        self.post_message(
                            AgentFail(
                                "Resume not supported",
                                f"{self._agent_data['name']} does not currently support resuming sessions.",
                                help="no_resume",
                            )
                        )
                        return
                    await self.acp_load_session()
                    if self.session_pk is not None:
                        from toad.db import DB

                        db = DB()
                        await db.session_update_last_used(self.session_pk)

            except jsonrpc.APIError as error:
                if isinstance(error.data, dict):
                    reason = str(error.data.get("reason") or "Failed to initialize agent")
                    details = str(error.data.get("details") or error.data.get("error") or "")
                else:
                    reason = "Failed to initialize agent"
                    details = ""
                self.post_message(AgentFail(reason, details))
                return

            # Signal ready
            self.post_message(AgentReady())

        except Exception as e:
            logger.error(f"Failed to connect to Punie server: {e}")
            self.post_message(
                AgentFail(
                    "Connection failed",
                    f"Could not connect to Punie server at {self.server_url}: {e}",
                )
            )

    async def _listen_loop(self) -> None:
        """Background task to listen for WebSocket messages.

        Receives JSON-RPC messages from server and dispatches to handler.
        """
        if self._websocket is None:
            return

        try:
            while True:
                try:
                    data = await self._websocket.recv()
                except Exception as e:
                    logger.error(f"WebSocket receive error: {e}")
                    self.post_message(
                        AgentFail(
                            "Connection lost",
                            f"Lost connection to Punie server: {e}",
                        )
                    )
                    break

                # Parse JSON-RPC message
                try:
                    message = json.loads(data)
                    self.log(f"[server] {data}")

                    # Dispatch to JSON-RPC server (reuses parent's handlers)
                    # This will call rpc_session_update, rpc_session_request_permission, etc.
                    if hasattr(self.server, "receive"):
                        await self.server.receive(message)  # type: ignore[attr-defined]
                    else:
                        # Fallback: manually dispatch
                        await self.server.dispatch(message)  # type: ignore[attr-defined]

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from server: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)
                    continue

        except asyncio.CancelledError:
            logger.info("Listen loop cancelled")
        except Exception as e:
            logger.error(f"Listen loop error: {e}", exc_info=True)
