# Phase 42: References

## Previous Phases
- Phase 28: Server/client separation (`agent-os/specs/` — search for phase28)
- Phase 29: Toad WebSocket integration (`agent-os/specs/` — search for phase29)

## Key Source Files

### Client Layer
- `src/punie/client/connection.py` — `punie_session()` context manager, `connect_to_server()`
- `src/punie/client/ask_client.py` — `run_ask_client()`, inline receive loop
- `src/punie/client/toad_client.py` — `run_toad_client()`, `send_prompt_stream()`, inline receive loops
- `src/punie/client/stdio_bridge.py` — `run_stdio_bridge()`, deprecated event loop API

### Server Layer
- `src/punie/http/websocket.py` — `websocket_endpoint()`, `_handle_request()`, error codes
- `src/punie/http/websocket_client.py` — `WebSocketClient`, `abort_pending_requests()`
- `src/punie/agent/adapter.py` — `PunieAgent`, `_cleanup_expired_sessions()`, grace period

### Toad Integration
- `scripts/run_toad_websocket.py` — inline `WebSocketToadAgent`, monkey-patch, print statements
- `src/punie/toad/websocket_agent.py` — dead reference code (to be deleted)
- `examples/toad_websocket_agent.py` — `ToadWebSocketAgent` example (used by tests)

### Testing
- `tests/test_toad_integration.py` — existing Toad tests (uses unittest.mock)
- `tests/test_toad_initialization_hang.py` — hang-specific tests
- `tests/test_websocket.py` — WebSocket server tests

## JSON-RPC Error Codes
- `-32700` — Parse error (invalid JSON)
- `-32601` — Method not found
- `-32603` — Internal error (server error during valid method)
- Current bug: unknown methods return `-32603` instead of `-32601`

## WebSocketState Enum (Starlette)
```python
from starlette.websockets import WebSocketState
# CONNECTING = 0, CONNECTED = 1, DISCONNECTED = 3
```

## asyncio.get_running_loop() vs get_event_loop()
- `asyncio.get_event_loop()` deprecated in Python 3.10+ when no running loop
- `asyncio.get_running_loop()` is the correct replacement inside async functions
- `stdio_bridge.py` uses `get_event_loop()` inside an async function — must fix
