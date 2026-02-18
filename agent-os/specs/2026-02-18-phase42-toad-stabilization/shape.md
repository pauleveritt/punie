# Phase 42: Shape — Scope Decisions and Architecture Notes

## Problem Statement

The Toad WebSocket integration (Phases 28/29) works in the happy path but fails
under real-world conditions:

1. **"Initializing..." hang** — `_run_agent()` sets `self._task` then returns, but
   Toad's message pump waits for `AgentReady` before showing the UI. If the async
   `run()` errors before posting `AgentReady`, the UI hangs indefinitely.

2. **KeyError on `params["update"]`** — `message["params"]["update"]` throws
   `KeyError` if the server sends `session_update` with `params` that omits
   `"update"` (e.g., a notification with extra fields).

3. **Per-send ThreadPoolExecutor** — Each `send()` call creates and destroys a
   `ThreadPoolExecutor`. This is expensive (OS thread creation overhead) and
   leaks threads if `future.result(timeout=5.0)` times out.

4. **No reconnection** — If the server restarts or the network blips, the client
   has no way to reconnect. The session is lost.

5. **Hardcoded timeouts scattered everywhere** — 8 different timeout values in
   6+ files. Impossible to tune without hunting through source.

6. **Duplicated receive loops** — `ask_client.py` and `toad_client.py` have nearly
   identical 50-line receive loops. Any bug fix must be applied twice.

7. **Test gaps** — `run_toad_client()` has zero tests. `stdio_bridge.py` has
   zero tests. Integration test requires a model server.

## Scope Decisions

### In Scope
- Fix all 6 concrete bugs listed in plan.md §42.1
- Centralize timeouts (no behavior change, just configuration)
- Extract shared receiver (refactor, no behavior change)
- Add reconnection logic to `run_toad_client()` only
- Move Toad agent class to a proper module
- Fix ThreadPoolExecutor lifecycle
- Add unit tests for all new modules
- Add integration test (marked `@pytest.mark.integration`)

### Out of Scope
- Changing the ACP protocol format
- Adding new tools or training data
- Performance optimizations beyond timeout fixes
- Toad UI changes
- Server-side reconnection logic changes (adapter.py grace period is a minor bug fix only)

## Architecture Notes

### Why a Shared Receiver?
The receive loop pattern in `ask_client.py:79-134` and `toad_client.py:136-184`
is structurally identical:
1. `wait_for(websocket.recv(), timeout=per_message_timeout)`
2. JSON decode with error handling
3. Route: session_update → callback, matching id → break/return, other → log

Extracting to `receiver.py` makes both clients thin wrappers and means bug fixes
apply once.

### Why Protocol over ABC?
`PunieClient` is a `Protocol` (structural subtyping) rather than ABC because:
- The actual clients (`ask_client`, `toad_client`) are module-level functions, not classes
- Protocol allows duck-typing for test fakes
- No runtime enforcement needed — the protocol documents the interface

### Why `reconnecting_session()` as async context manager?
The reconnection logic wraps `punie_session()` rather than duplicating it because:
- `punie_session()` already handles connect + handshake cleanly
- The reconnect layer only needs to catch `ConnectionClosed` and retry
- Context manager pattern matches existing usage in `run_toad_client()`

### ThreadPoolExecutor Fix
The fix caches a single `ThreadPoolExecutor(max_workers=1)` at the class level,
created in `__init__()` and shut down in `stop()`. This avoids thread creation
overhead on every `send()` call and ensures clean shutdown.

## Bug Inventory

| # | File | Line | Bug | Fix |
|---|------|------|-----|-----|
| 1 | `websocket_client.py` | 448-449 | Logs 0 (clears before counting) | Capture count before `clear()` |
| 2 | `ask_client.py` | 99 | `message["params"]["update"]` KeyError | `.get("params", {}).get("update", {})` |
| 3 | `toad_client.py` | 155, 326 | Same KeyError | Same fix |
| 4 | `stdio_bridge.py` | 155, 160 | `asyncio.get_event_loop()` deprecated in 3.10+ | `asyncio.get_running_loop()` |
| 5 | `websocket.py` | 278 | Error code -32603 for unknown method | Use -32601 (MethodNotFound) |
| 6 | `websocket.py` | 159, 181 | Magic number `!= 1` | `WebSocketState.CONNECTED` |
| 7 | `run_toad_websocket.py` | 117-151 | 11 `print()` debug statements | `logger.debug()` |
