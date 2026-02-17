"""WebSocket client utilities for connecting to Punie server.

This package provides thin WebSocket clients that connect to the Punie server:
- connection: Low-level WebSocket connection and ACP handshake utilities
- stdio_bridge: Stdio ↔ WebSocket bridge for PyCharm integration
- ask_client: Simple client for one-shot questions via `punie ask`
- toad_client: WebSocket client for browser-based Toad frontend integration
"""

from punie.client.ask_client import run_ask_client
from punie.client.connection import connect_to_server, punie_session
from punie.client.stdio_bridge import run_stdio_bridge
from punie.client.toad_client import (
    create_toad_session,
    handle_tool_update,
    run_toad_client,
    send_prompt_stream,
)

__all__ = [
    "connect_to_server",
    "punie_session",
    "run_stdio_bridge",
    "run_ask_client",
    "run_toad_client",
    "send_prompt_stream",
    "handle_tool_update",
    "create_toad_session",
]
