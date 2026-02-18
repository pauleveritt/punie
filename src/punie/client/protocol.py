"""PunieClient protocol definition.

Defines the structural interface that all Punie client implementations must satisfy.
Using a Protocol (structural subtyping) allows test fakes without inheritance.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable

__all__ = ["PunieClient", "MessageCallback"]

#: Callback type for streaming update notifications.
MessageCallback = Callable[[str, dict[str, Any]], None]


@runtime_checkable
class PunieClient(Protocol):
    """Structural interface for Punie WebSocket clients.

    All client implementations (ask, toad, test fakes) satisfy this protocol.

    Example:
        >>> def run_task(client: PunieClient, prompt: str) -> dict:
        ...     await client.connect("ws://localhost:8000/ws", "/workspace")
        ...     return await client.send_prompt(prompt)
    """

    @property
    def is_connected(self) -> bool:
        """Whether the client has an active connection."""
        ...

    async def connect(self, server_url: str, cwd: str) -> None:
        """Establish connection and perform ACP handshake.

        Args:
            server_url: WebSocket URL (e.g., ws://localhost:8000/ws)
            cwd: Current working directory for session
        """
        ...

    async def disconnect(self) -> None:
        """Close connection and clean up resources."""
        ...

    async def send_prompt(
        self,
        prompt: str,
        on_update: MessageCallback | None = None,
    ) -> dict[str, Any]:
        """Send prompt and return final result.

        Args:
            prompt: User prompt text
            on_update: Optional callback(update_type, content) for streaming

        Returns:
            Final response result dict
        """
        ...
