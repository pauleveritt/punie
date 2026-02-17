#!/usr/bin/env python3
"""Launch Toad with WebSocket agent.

This script launches Toad UI using the WebSocket-enabled agent subclass,
connecting to Punie server instead of spawning subprocess agents.

Usage:
    python scripts/run_toad_websocket.py [--server-url ws://localhost:8000/ws]
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

app = typer.Typer()


def get_websocket_toad_agent_class(server_url: str = "ws://localhost:8000/ws"):
    """Get WebSocketToadAgent class with Toad imports.

    This factory function imports Toad components and returns the agent class.
    Used by both the CLI and tests to avoid circular import issues.

    Args:
        server_url: Default WebSocket server URL

    Returns:
        WebSocketToadAgent class ready for instantiation
    """
    import asyncio
    import json
    import logging

    # Import widgets first to avoid circular import in toad.acp.agent
    import toad.widgets.conversation  # Breaks circular import
    import toad.acp.agent
    from toad import jsonrpc
    from toad.agent import AgentFail, AgentReady
    from websockets.asyncio.client import ClientConnection

    from punie.client.toad_client import create_toad_session

    logger = logging.getLogger(__name__)

    class WebSocketToadAgent(toad.acp.agent.Agent):
        """WebSocket-enabled Toad agent."""

        def __init__(
            self,
            project_root,
            agent,
            session_id,
            session_pk=None,
            server_url=server_url,
        ):
            super().__init__(project_root, agent, session_id, session_pk)
            self.server_url = server_url
            self._websocket: ClientConnection | None = None
            self._punie_session_id: str | None = None

        def send(self, request: jsonrpc.Request) -> None:
            """Send request via WebSocket (synchronous API with async execution).

            CRITICAL: This method MUST be synchronous to match the parent Agent.send() contract.
            However, we need to do async I/O (WebSocket.send()).

            Solution: Run the async send in a separate thread with its own event loop.
            This ensures the send completes before this method returns, avoiding the race
            condition where the parent waits for a response before the request is sent.
            """
            import concurrent.futures
            import threading

            if self._websocket is None:
                logger.error("Cannot send: WebSocket not connected")
                return

            self.log(f"[client] {request.body}")

            def _run_async_send():
                """Run async send in a new thread with its own event loop."""
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._websocket.send(request.body_json))
                except Exception as e:
                    logger.error(f"WebSocket send failed: {e}")
                    self.post_message(AgentFail("Connection lost", str(e)))
                finally:
                    loop.close()

            # Execute in thread pool and wait for completion
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_async_send)
                try:
                    future.result(timeout=5.0)  # Wait for send to complete
                except concurrent.futures.TimeoutError:
                    logger.error("WebSocket send timed out")
                except Exception as e:
                    logger.error(f"Failed to send: {e}")

        async def stop(self) -> None:
            await super().stop()
            if self._websocket is not None:
                try:
                    await self._websocket.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket: {e}")
                finally:
                    self._websocket = None

        async def _run_agent(self) -> None:
            """Override parent's _run_agent to skip subprocess creation."""
            print("🚀 _run_agent called")  # DEBUG
            self._task = asyncio.create_task(self.run())
            print("🚀 run() task created")  # DEBUG

        async def run(self) -> None:
            print("🎯 run() started")  # DEBUG
            try:
                print("🎯 Creating WebSocket session...")  # DEBUG
                self._websocket, self._punie_session_id = await create_toad_session(
                    self.server_url, str(self.project_root_path)
                )
                print(f"🎯 WebSocket connected! Session ID: {self._punie_session_id}")  # DEBUG
                self._agent_task = asyncio.create_task(self._listen_loop())

                print("🎯 Calling acp_initialize()...")  # DEBUG
                await self.acp_initialize()
                print("🎯 acp_initialize() complete")  # DEBUG
                if self.session_id is None:
                    print("🎯 Calling acp_new_session()...")  # DEBUG
                    await self.acp_new_session()
                    print("🎯 acp_new_session() complete")  # DEBUG
                else:
                    if not self.agent_capabilities.get("loadSession", False):
                        self.post_message(
                            AgentFail(
                                "Resume not supported",
                                f"{self._agent_data['name']} does not support resuming.",
                            )
                        )
                        return
                    await self.acp_load_session()

                print("🎯 Posting AgentReady message...")  # DEBUG
                self.post_message(AgentReady())
                print("✅ Agent fully initialized and ready!")  # DEBUG
            except Exception as e:
                logger.error(f"Failed to connect: {e}")
                self.post_message(AgentFail("Connection failed", str(e)))

        async def _listen_loop(self) -> None:
            if self._websocket is None:
                return
            try:
                while True:
                    try:
                        data = await self._websocket.recv()
                    except Exception as e:
                        error_str = str(e)
                        if "sent 1000" in error_str and "received 1000" in error_str:
                            logger.info(f"WebSocket closed normally: {e}")
                            break
                        else:
                            logger.error(f"WebSocket receive error: {e}")
                            self.post_message(AgentFail("Connection lost", str(e)))
                            break

                    try:
                        message = json.loads(data)
                        self.log(f"[server] {data}")
                        if hasattr(self.server, "receive"):
                            await self.server.receive(message)  # type: ignore
                        else:
                            await self.server.dispatch(message)  # type: ignore
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON: {e}")
                    except Exception as e:
                        logger.error(f"Error handling message: {e}")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Listen loop error: {e}")

    return WebSocketToadAgent


@app.command()
def main(
    server_url: str = "ws://localhost:8000/ws",
    project: Path | None = None,
) -> None:
    """Launch Toad with WebSocket connection to Punie server.

    Args:
        server_url: Punie server WebSocket URL
        project: Project root directory (defaults to current directory)
    """
    # Get project root
    if project is None:
        project = Path.cwd()

    print("🐸 Starting Toad with WebSocket connection...")
    print(f"   Server: {server_url}")
    print(f"   Project: {project}")
    print()

    # Import Toad first (let it fully initialize)
    import toad.cli

    # CRITICAL: Import widgets.conversation BEFORE acp.agent to break circular import
    # (toad.acp.agent → toad.acp.messages → toad.acp.agent.Mode)
    import toad.widgets.conversation  # noqa: F401
    import toad.acp.agent

    # Get WebSocketToadAgent class from factory (handles all imports safely)
    WebSocketToadAgent = get_websocket_toad_agent_class(server_url)

    # Replace the Agent class (monkey-patch)
    toad.acp.agent.Agent = WebSocketToadAgent  # type: ignore[assignment]

    # Run Toad CLI with Punie agent auto-selected
    try:
        # Pass arguments to auto-select Punie agent and set project directory
        sys.argv = ["toad", "run", str(project), "-a", "punie"]
        toad.cli.main()
    except KeyboardInterrupt:
        print("\n\n✓ Toad closed")
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    app()
