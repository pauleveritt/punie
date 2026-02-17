# Phase 28: Server/Client Separation Architecture

## Context

**Problem:** The current Punie server runs in "dual protocol mode" (stdio + HTTP/WebSocket in same process). When stdin closes (background mode), the stdio task completes, triggering cancellation of the HTTP server. This makes it impossible to run the server in background.

**Root Cause:** `run_dual()` in `src/punie/http/runner.py` uses `asyncio.wait(FIRST_COMPLETED)` - when either stdio or HTTP completes, the other is cancelled. Background processes have no stdin, so the stdio task completes immediately.

**Solution:** Separate concerns so that:
- **Punie server** speaks ONLY HTTP/WebSocket (no stdio)
- **`punie` (default command)** becomes a thin WebSocket client that bridges stdio ↔ server (for PyCharm)
- **`punie ask`** becomes a thin WebSocket client that sends prompts to server

## Implementation Summary

### Files Created (8 new files)

**Client Infrastructure:**
1. `src/punie/client/__init__.py` - Client package exports
2. `src/punie/client/connection.py` - WebSocket connection utilities and ACP handshake
3. `src/punie/client/stdio_bridge.py` - Bidirectional stdio ↔ WebSocket bridge
4. `src/punie/client/ask_client.py` - Thin client for `punie ask` command

**Spec Documentation:**
5. `agent-os/specs/2026-02-16-phase28-server-client-separation/plan.md` - This file
6. `agent-os/specs/2026-02-16-phase28-server-client-separation/shape.md` - Shaping decisions
7. `agent-os/specs/2026-02-16-phase28-server-client-separation/standards.md` - Standards applied
8. `agent-os/specs/2026-02-16-phase28-server-client-separation/references.md` - Code references

### Files Modified (5 files)

1. `src/punie/http/runner.py` - Added `run_http()` function, marked `run_dual()` as deprecated
2. `src/punie/http/__init__.py` - Export `run_http`
3. `src/punie/cli.py` - Updated all three commands to use new architecture
4. `pyproject.toml` - Added `websockets>=13.0` dependency
5. `Justfile` - Fixed `dev-servers-bg` recipe (server now works in background)

### Key Changes

**1. HTTP-Only Server Mode (`run_http()`)**
- Server runs indefinitely without stdio dependency
- Clean separation: server handles WebSocket connections only
- Multiple clients can connect simultaneously

**2. WebSocket Client Utilities**
- `connect_to_server()` - Connect to WebSocket URL
- `send_request()` - Send JSON-RPC request, wait for response
- `initialize_session()` - Perform ACP handshake (initialize → new_session)
- `punie_session()` - Context manager for session lifecycle

**3. Stdio Bridge Client**
- Bidirectional forwarding: stdin → WebSocket, WebSocket → stdout
- Stateless proxy (all session state lives in server)
- PyCharm integration via ACP JSON-RPC over stdio

**4. Ask Client**
- Thin client for CLI questions
- Connects, creates session, sends prompt, streams response
- Clean shutdown after response complete

**5. CLI Command Updates**
- `punie` (default) - Now runs stdio bridge (connects to server)
- `punie serve` - Now runs HTTP-only server (no stdio)
- `punie ask` - Now connects to server via WebSocket

## Architecture Diagram

```
┌──────────────┐
│ punie serve  │ ── HTTP/WebSocket ONLY
│ (server)     │     ws://localhost:8000/ws
└──────────────┘
       ↑
       │ WebSocket connections
       ├───────────────────────────────┐
       │                               │
┌──────┴──────┐              ┌────────┴────────┐
│ punie       │              │ punie ask       │
│ (PyCharm)   │              │ (CLI)           │
│             │              │                 │
│ stdio ↔ ws  │              │ prompt → ws     │
└─────────────┘              └─────────────────┘
```

## Breaking Changes

**Migration Required:**

```bash
# OLD (all-in-one, broken in background)
punie  # Starts agent + server

# NEW (separate server/client)
# Terminal 1: Start server
punie serve --model local:http://localhost:5001/v1/model

# Terminal 2: Use client
punie  # Connects to server

# Or background mode (NOW WORKS!)
punie serve --model <model> > server.log 2>&1 &
punie ask "test"
```

## Verification Steps

1. **Server-only mode works:**
   ```bash
   punie serve --model test
   # Server stays running indefinitely
   ```

2. **Ask client works:**
   ```bash
   punie serve --model test &
   punie ask "What is dependency injection?"
   # Response printed to stdout
   ```

3. **Stdio bridge works:**
   ```bash
   punie serve --model test &
   echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | punie
   # JSON-RPC response on stdout
   ```

4. **Multiple clients work:**
   ```bash
   punie serve --model test &
   punie ask "Query 1" &
   punie ask "Query 2" &
   wait
   # Both complete successfully
   ```

5. **Background mode works:**
   ```bash
   just dev-servers-bg
   # Both MLX and Punie stay running
   punie ask "Test query"
   just stop-all
   ```

## Success Criteria

- ✅ Server runs indefinitely in background
- ✅ Multiple WebSocket clients connect simultaneously
- ✅ Stdio bridge correctly forwards ACP messages
- ✅ Ask client sends prompts and receives responses
- ✅ All existing tests pass
- ✅ New integration tests pass
- ✅ `just dev-servers-bg` works correctly
- ✅ Documentation updated with new workflow
