"""Toad integration for Punie.

WebSocket-enabled Toad agent that connects to Punie server without forking Toad repo.

Note: The WebSocketToadAgent class is defined inline in scripts/run_toad_websocket.py
to avoid circular import issues with toad.acp.agent. See docs/toad-websocket-subclass.md
for implementation details.
"""

# Do not import websocket_agent here - causes circular import with toad.acp.agent
# The actual implementation is in scripts/run_toad_websocket.py

__all__: list[str] = []
