"""Stdio ↔ WebSocket bridge for PyCharm integration.

This module provides a bidirectional bridge that forwards JSON-RPC messages
between stdin/stdout and a WebSocket connection to the Punie server.

This is a stateless proxy - all session state lives in the server.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import NoReturn

from websockets.asyncio.client import ClientConnection
from websockets.exceptions import WebSocketException

from punie.client.connection import connect_to_server

logger = logging.getLogger(__name__)

__all__ = ["run_stdio_bridge"]


async def _forward_stdin_to_websocket(
    reader: asyncio.StreamReader, websocket: ClientConnection
) -> None:
    """Forward messages from stdin to WebSocket.

    Reads newline-delimited JSON-RPC messages from stdin and forwards them
    to the WebSocket server.

    Args:
        reader: asyncio StreamReader connected to stdin
        websocket: WebSocket connection to server

    Raises:
        asyncio.IncompleteReadError: If stdin closes
        WebSocketException: If WebSocket connection fails
    """
    logger.debug("Starting stdin → WebSocket forwarding")
    try:
        while True:
            # Read line from stdin (blocks until newline or EOF)
            line = await reader.readline()

            if not line:
                logger.info("stdin closed (EOF), stopping stdin forwarding")
                break

            # Validate JSON before forwarding
            try:
                message = json.loads(line.decode("utf-8"))
                logger.debug(f"stdin → ws: {message.get('method', 'response')}")
            except json.JSONDecodeError as exc:
                logger.warning(f"Invalid JSON from stdin: {exc}")
                continue

            # Forward to WebSocket
            await websocket.send(line.decode("utf-8"))

    except asyncio.IncompleteReadError:
        logger.info("stdin stream incomplete, stopping stdin forwarding")
    except WebSocketException as exc:
        logger.warning(f"WebSocket error during stdin forward: {exc}")
        raise
    except Exception:
        logger.exception("Error in stdin → WebSocket forwarding")
        raise


async def _forward_websocket_to_stdout(
    websocket: ClientConnection, writer: asyncio.StreamWriter
) -> None:
    """Forward messages from WebSocket to stdout.

    Receives JSON-RPC messages from WebSocket and writes them to stdout
    as newline-delimited JSON.

    Args:
        websocket: WebSocket connection to server
        writer: asyncio StreamWriter connected to stdout

    Raises:
        WebSocketException: If WebSocket connection fails
    """
    logger.debug("Starting WebSocket → stdout forwarding")
    try:
        while True:
            # Receive from WebSocket (always string for text frames)
            data = await websocket.recv()

            # Ensure we have a string
            if isinstance(data, bytes):
                data = data.decode("utf-8")

            # Validate JSON
            try:
                message = json.loads(data)
                logger.debug(f"ws → stdout: {message.get('method', 'response')}")
            except json.JSONDecodeError as exc:
                logger.warning(f"Invalid JSON from WebSocket: {exc}")
                continue

            # Forward to stdout (add newline)
            writer.write(data.encode("utf-8") + b"\n")
            await writer.drain()

    except WebSocketException as exc:
        logger.info(f"WebSocket disconnected: {exc}")
    except Exception:
        logger.exception("Error in WebSocket → stdout forwarding")
        raise


async def run_stdio_bridge(server_url: str) -> NoReturn:
    """Run stdio ↔ WebSocket bridge for PyCharm.

    Connects to Punie server and forwards JSON-RPC messages bidirectionally:
    - stdin → WebSocket (client requests)
    - WebSocket → stdout (server responses/notifications)

    This is a stateless proxy. All ACP protocol handling (initialize,
    new_session, etc.) happens at the server.

    Args:
        server_url: WebSocket URL (e.g., ws://localhost:8000/ws)

    Raises:
        RuntimeError: If connection fails or forwarding errors

    Example:
        # Start server first:
        # $ punie serve --model local

        # Run bridge:
        # $ echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | punie

    Note:
        This function never returns normally - it runs until stdin closes
        or WebSocket disconnects, then exits the process.
    """
    logger.info(f"Starting stdio bridge to {server_url}")

    try:
        # Connect to server
        websocket = await connect_to_server(server_url)
        logger.info("WebSocket connection established")

        # Setup stdio streams
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())

        logger.info("Stdio streams connected, starting bidirectional forwarding")

        # Create forwarding tasks
        stdin_task = asyncio.create_task(
            _forward_stdin_to_websocket(reader, websocket), name="stdin-to-ws"
        )
        ws_task = asyncio.create_task(
            _forward_websocket_to_stdout(websocket, writer), name="ws-to-stdout"
        )

        # Wait for either direction to complete (FIRST_COMPLETED)
        done, pending = await asyncio.wait(
            {stdin_task, ws_task}, return_when=asyncio.FIRST_COMPLETED
        )

        # Log which task completed first
        for task in done:
            if task.exception():
                logger.error(f"{task.get_name()} failed: {task.exception()}")
            else:
                logger.info(f"{task.get_name()} completed normally")

        # Cancel remaining task
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(f"{task.get_name()} cancelled")

        # Clean shutdown
        await websocket.close()
        logger.info("Bridge shutdown complete")

    except Exception as exc:
        logger.exception(f"Fatal error in stdio bridge: {exc}")
        sys.exit(1)

    # Normal exit (stdin closed)
    sys.exit(0)
