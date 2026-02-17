"""Transport abstraction for ACP connections.

This module provides a protocol-based abstraction over different transport
mechanisms (stdio streams, WebSocket connections) to allow AgentSideConnection
to work with multiple connection types.
"""

from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable

from starlette.websockets import WebSocket


__all__ = ["Transport", "StdioTransport", "WebSocketTransport"]


@runtime_checkable
class Transport(Protocol):
    """Protocol for bidirectional message transport.

    Transport implementations must provide async send/receive/close operations
    for string-based messages (typically JSON-RPC).
    """

    async def send(self, data: str) -> None:
        """Send a message over the transport.

        Args:
            data: String message to send (typically JSON-RPC).
        """
        ...

    async def receive(self) -> str:
        """Receive a message from the transport.

        Returns:
            String message received (typically JSON-RPC).

        Raises:
            asyncio.IncompleteReadError: If connection closed while reading.
        """
        ...

    async def close(self) -> None:
        """Close the transport connection."""
        ...


class StdioTransport:
    """Transport implementation for stdio streams.

    Wraps asyncio.StreamWriter and asyncio.StreamReader to provide
    the Transport protocol interface.
    """

    def __init__(
        self, writer: asyncio.StreamWriter, reader: asyncio.StreamReader
    ) -> None:
        """Initialize stdio transport.

        Args:
            writer: asyncio StreamWriter for sending data.
            reader: asyncio StreamReader for receiving data.
        """
        self._writer = writer
        self._reader = reader

    async def send(self, data: str) -> None:
        """Send a message via stdio.

        Args:
            data: String message to send.
        """
        self._writer.write(data.encode("utf-8"))
        await self._writer.drain()

    async def receive(self) -> str:
        """Receive a message via stdio.

        Returns:
            String message received.

        Raises:
            asyncio.IncompleteReadError: If stdin closed while reading.
        """
        line = await self._reader.readline()
        return line.decode("utf-8")

    async def close(self) -> None:
        """Close stdio transport."""
        self._writer.close()
        await self._writer.wait_closed()


class WebSocketTransport:
    """Transport implementation for WebSocket connections.

    Wraps Starlette's WebSocket to provide the Transport protocol interface.
    """

    def __init__(self, websocket: WebSocket) -> None:
        """Initialize WebSocket transport.

        Args:
            websocket: Starlette WebSocket connection.
        """
        self._websocket = websocket

    async def send(self, data: str) -> None:
        """Send a message via WebSocket.

        Args:
            data: String message to send.
        """
        await self._websocket.send_text(data)

    async def receive(self) -> str:
        """Receive a message via WebSocket.

        Returns:
            String message received.

        Raises:
            RuntimeError: If WebSocket connection closed.
        """
        return await self._websocket.receive_text()

    async def close(self) -> None:
        """Close WebSocket transport."""
        await self._websocket.close()
