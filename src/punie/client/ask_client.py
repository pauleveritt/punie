"""Thin client for `punie ask` command.

This module provides a simple client that connects to the server, creates
a session, sends a prompt, and prints the response.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from pathlib import Path

from punie.client.connection import punie_session
from punie.client.receiver import receive_messages

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

        # Track state for stdout printing
        response_text = ""
        first_chunk = True

        def on_notification(update_type: str, update: dict) -> None:
            nonlocal response_text, first_chunk

            if update_type == "agent_message_chunk":
                content = update.get("content")
                if content and content.get("type") == "text":
                    chunk = content["text"]

                    # Clear "Working..." message on first chunk
                    if first_chunk:
                        print(
                            "\r" + " " * 20 + "\r", end="", file=sys.stderr, flush=True
                        )
                        first_chunk = False

                    print(chunk, end="", flush=True)  # Stream to stdout
                    response_text += chunk

        # Use shared receiver loop
        await receive_messages(
            websocket,
            request_id=request_id,
            on_notification=on_notification,
        )

        # Add newline if we printed any content
        if response_text and not first_chunk:
            print()  # Newline after response

        logger.info("Ask complete")
        return response_text
