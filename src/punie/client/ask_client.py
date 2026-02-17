"""Thin client for `punie ask` command.

This module provides a simple client that connects to the server, creates
a session, sends a prompt, and prints the response.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

import websockets
from punie.client.connection import punie_session

logger = logging.getLogger(__name__)

__all__ = ["run_ask_client"]


async def run_ask_client(server_url: str, prompt: str, workspace: Path) -> str:
    """Send prompt to server and return response.

    Connects to server, creates session, sends prompt, streams response to
    stdout, and returns full response text.

    Args:
        server_url: WebSocket URL (e.g., ws://localhost:8000/ws)
        prompt: User's question or instruction
        workspace: Workspace directory for session

    Returns:
        Complete response text

    Raises:
        RuntimeError: If connection or prompt execution fails

    Example:
        response = await run_ask_client(
            "ws://localhost:8000/ws",
            "What is dependency injection?",
            Path.cwd()
        )
        print(response)
    """
    logger.info(f"Connecting to {server_url}")

    async with punie_session(server_url, str(workspace)) as (websocket, session_id):
        logger.info(f"Session created: {session_id}")

        # Send prompt request (Issue #4: use UUID to prevent collision)
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "prompt",
            "params": {
                "session_id": session_id,
                "prompt": [{"type": "text", "text": prompt}],
            },
        }
        logger.debug(f"Sending prompt request (id={request_id})")
        await websocket.send(json.dumps(request))

        # Show "Working..." message to user (stderr, not stdout)
        print("⏳ Working...", file=sys.stderr, flush=True)

        # Listen for session_update notifications
        # ACP Protocol flow:
        # 1. Client sends prompt request
        # 2. Server sends session_update notifications (greeting, content chunks)
        # 3. Server sends final response (after all notifications are sent)
        response_text = ""
        first_chunk = True

        while True:
            # Issue #1: Add timeout protection (5 min for long operations)
            try:
                data = await asyncio.wait_for(websocket.recv(), timeout=300.0)
            except asyncio.TimeoutError:
                raise RuntimeError("No response from server after 5 minutes")
            except websockets.exceptions.ConnectionClosed as exc:
                raise ConnectionError(f"Server disconnected during prompt: {exc}")

            # Issue #2: Handle malformed JSON
            try:
                message = json.loads(data)
            except json.JSONDecodeError as exc:
                logger.warning(f"Invalid JSON from server: {exc}")
                continue  # Skip and wait for next message

            logger.debug(f"Received message: {message.get('method', 'response')}")

            # Handle session_update notifications (streaming response chunks)
            if message.get("method") == "session_update":
                update = message["params"]["update"]

                # Agent message content (text block)
                # Issue #5: Use camelCase (now fixed in server)
                if update.get("sessionUpdate") == "agent_message_chunk":
                    # content is a single ContentBlock, not a list
                    content = update.get("content")
                    if content and content.get("type") == "text":
                        chunk = content["text"]

                        # Clear "Working..." message on first chunk
                        if first_chunk:
                            print("\r" + " " * 20 + "\r", end="", file=sys.stderr, flush=True)
                            first_chunk = False

                        print(chunk, end="", flush=True)  # Stream to stdout
                        response_text += chunk

            # Handle final response (comes AFTER all session_update notifications)
            elif message.get("id") == request_id:
                if "error" in message:
                    error = message["error"]
                    raise RuntimeError(
                        f"Prompt (req={request_id}) failed: {error.get('message')} (code {error.get('code')})"
                    )
                # Final response received - all notifications have been sent, we're done!
                logger.debug("Received final response - prompt complete")
                break  # Exit loop

            # Issue #10: Handle unknown notifications gracefully
            elif "method" in message:
                logger.debug(f"Ignoring notification: {message['method']}")
                continue
            else:
                logger.warning(f"Unknown message format: {message}")
                continue

        # Add newline if we printed any content
        if response_text and not first_chunk:
            print()  # Newline after response

        logger.info("Ask complete")
        return response_text
