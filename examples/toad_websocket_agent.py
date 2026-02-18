"""Example WebSocket agent for Toad integration.

This demonstrates how to use Punie's WebSocket client utilities to create
a Toad-compatible agent that connects over WebSocket instead of stdio/subprocess.

Toad developers can use this as a reference for implementing WebSocket transport
in toad/acp/agent.py.

Key differences from stdio agent:
- No subprocess management
- Persistent WebSocket connection
- Built-in reconnection support
- Streaming via callbacks
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from websockets.asyncio.client import ClientConnection

from punie.client.toad_client import create_toad_session, send_prompt_stream

logger = logging.getLogger(__name__)

__all__ = ["ToadWebSocketAgent"]


class ToadWebSocketAgent:
    """Example WebSocket agent for Toad integration.

    This demonstrates how to wrap Punie's WebSocket client utilities
    in a Toad-compatible interface.

    Example:
        >>> agent = ToadWebSocketAgent(
        ...     server_url="ws://localhost:8000/ws",
        ...     project_root="/workspace"
        ... )
        >>> await agent.connect()
        >>> await agent.send_prompt("What is dependency injection?")
        >>> await agent.disconnect()

    Attributes:
        server_url: WebSocket URL (e.g., ws://localhost:8000/ws)
        project_root: Project working directory
    """

    def __init__(self, server_url: str, project_root: str) -> None:
        """Initialize agent with server URL and project root.

        Args:
            server_url: WebSocket URL (e.g., ws://localhost:8000/ws)
            project_root: Project working directory path
        """
        self.server_url = server_url
        self.project_root = project_root
        self._websocket: ClientConnection | None = None
        self._session_id: str | None = None
        self._updates: list[tuple[str, dict[str, Any]]] = []

    async def connect(self) -> None:
        """Establish WebSocket connection and perform ACP handshake.

        Creates a new session with the Punie server.

        Raises:
            ConnectionError: If connection or handshake fails
        """
        try:
            logger.info(f"Connecting to {self.server_url}")
            self._websocket, self._session_id = await create_toad_session(
                self.server_url, self.project_root
            )
            logger.info(f"Connected with session_id={self._session_id}")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise ConnectionError(f"Cannot connect to Punie server: {e}") from e

    async def send_prompt(
        self,
        prompt: str,
        on_update: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Send prompt and handle streaming response.

        Args:
            prompt: User prompt text
            on_update: Optional callback(update_type, content) for streaming

        Returns:
            Final response result dict

        Raises:
            RuntimeError: If not connected or prompt execution fails
            ConnectionError: If WebSocket disconnects during streaming

        Example:
            >>> def on_update(update_type, content):
            ...     if update_type == "agent_message_chunk":
            ...         text = content.get("content", {}).get("text", "")
            ...         print(text, end="", flush=True)
            ...
            >>> result = await agent.send_prompt("Hello!", on_update)
        """
        if not self._websocket or not self._session_id:
            raise RuntimeError("Not connected - call connect() first")

        logger.debug(f"Sending prompt: {prompt}")

        # Use internal callback to capture updates
        self._updates.clear()

        def _capture_update(update_type: str, content: dict[str, Any]) -> None:
            """Capture updates for internal tracking."""
            self._updates.append((update_type, content))
            # Forward to user callback if provided
            if on_update:
                on_update(update_type, content)

        try:
            result = await send_prompt_stream(
                self._websocket, self._session_id, prompt, _capture_update
            )
            logger.debug(f"Prompt complete, received {len(self._updates)} updates")
            return result
        except RuntimeError as e:
            logger.error(f"Prompt failed: {e}")
            raise
        except ConnectionError as e:
            logger.error(f"Connection lost during prompt: {e}")
            raise

    async def disconnect(self) -> None:
        """Close WebSocket connection and clean up.

        Safe to call even if not connected.
        """
        if self._websocket:
            logger.info("Disconnecting")
            try:
                await self._websocket.close()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._websocket = None
                self._session_id = None

    def get_updates(self) -> list[tuple[str, dict[str, Any]]]:
        """Get all updates from last prompt.

        Returns:
            List of (update_type, content) tuples

        Example:
            >>> await agent.send_prompt("Hello")
            >>> updates = agent.get_updates()
            >>> for update_type, content in updates:
            ...     print(f"{update_type}: {content}")
        """
        return self._updates.copy()

    def _handle_update(self, update_type: str, content: dict[str, Any]) -> None:
        """Internal callback for streaming updates.

        This demonstrates how to process different update types.

        Args:
            update_type: Type of update (from sessionUpdate field)
            content: Full update dict with type-specific fields
        """
        if update_type == "agent_message_chunk":
            # Extract text from agent response
            text = content.get("content", {}).get("text", "")
            logger.debug(f"Agent message: {text[:50]}...")

        elif update_type == "tool_call":
            # Tool execution started
            tool_call_id = content.get("tool_call_id")
            title = content.get("title")
            kind = content.get("kind")
            logger.debug(f"Tool call {tool_call_id}: {title} (kind={kind})")

        elif update_type == "tool_call_update":
            # Tool execution progress
            tool_call_id = content.get("tool_call_id")
            status = content.get("status")
            logger.debug(f"Tool {tool_call_id} status: {status}")

        else:
            # Other update types
            logger.debug(f"Update: {update_type}")


# Example usage (can be run as script)
async def main() -> int:
    """Example usage of ToadWebSocketAgent.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    import sys

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Create agent
    agent = ToadWebSocketAgent(server_url="ws://localhost:8000/ws", project_root="/tmp")

    try:
        # Connect
        await agent.connect()

        # Define callback for streaming
        def on_update(update_type: str, content: dict[str, Any]) -> None:
            if update_type == "agent_message_chunk":
                text = content.get("content", {}).get("text", "")
                print(text, end="", flush=True)

        # Send prompt
        prompt = sys.argv[1] if len(sys.argv) > 1 else "What is dependency injection?"
        print(f"Prompt: {prompt}\n")
        await agent.send_prompt(prompt, on_update)
        print()  # Newline after response

        # Show summary
        updates = agent.get_updates()
        print(f"\nReceived {len(updates)} updates")

    except ConnectionError as e:
        print(f"Connection error: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Runtime error: {e}", file=sys.stderr)
        return 1
    finally:
        # Always disconnect
        await agent.disconnect()

    return 0


if __name__ == "__main__":
    """Run example from command line.

    Usage:
        python examples/toad_websocket_agent.py "Your question"

    Requires Punie server running:
        uv run punie serve
    """
    exit_code = asyncio.run(main())
    exit(exit_code)
