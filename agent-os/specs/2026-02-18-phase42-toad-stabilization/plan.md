# Phase 42: Toad/WebSocket Stabilization — Plan

## Context

Phases 28/29 shipped server/client separation and Toad WebSocket integration but have known bugs. The user reports: "Claude Code keeps saying 'Fixed' then I go to Toad and get an error ('Initializing....', or answering a question, etc.)" The root causes: duplicated message receive loops with unsafe field access, no reconnection logic, hardcoded timeouts everywhere, a fragile Toad agent architecture (monkey-patching, inline class, ThreadPoolExecutor per-send), and major test gaps.

**Branch:** `phase42-toad-stabilization`

## Dependency Graph

```
Task 1 (spec docs)
Task 2 (bug fixes + timeouts) ← no deps
  ↓
Task 3 (shared Protocol + receiver) ← needs timeouts
  ↓         ↓
Task 4    Task 5     ← can run in parallel
(reconnect) (Toad agent)
  ↓         ↓
Task 6 (test coverage) ← needs all above
```

## Sub-Phase Summary

### 42.1 — Centralized Timeouts + Bug Fixes
- Create `src/punie/client/timeouts.py` (8 timeout constants)
- Fix 6 concrete bugs (abort log, KeyError, deprecated API, error code, magic number, print statements)
- Add missing timeouts to connect/recv paths

### 42.2 — Shared Client Protocol + Receiver
- Define `PunieClient` Protocol in `src/punie/client/protocol.py`
- Extract shared receive loop into `src/punie/client/receiver.py`
- Refactor `ask_client.py` and `toad_client.py` to use shared receiver

### 42.3 — Reconnection with Backoff
- Create `src/punie/client/reconnect.py` with `ReconnectConfig` + `reconnecting_session()`
- Integrate into `run_toad_client()`
- Fix grace period resume leak in `adapter.py`

### 42.4 — Toad Agent Architecture Fix
- Create `src/punie/toad/agent.py` with proper module
- Fix ThreadPoolExecutor (cache per-lifetime, not per-send)
- Simplify `scripts/run_toad_websocket.py`
- Delete dead `src/punie/toad/websocket_agent.py`

### 42.5 — Test Coverage
- Create `src/punie/testing/fakes.py` (FakeWebSocket, FakeClientConnection)
- Add receiver, toad_client, stdio_bridge, reconnection tests
- Add integration round-trip test (`tests/test_toad_roundtrip.py`)

## Key Files

| File | Role |
|------|------|
| `src/punie/client/timeouts.py` | NEW — centralized timeout config |
| `src/punie/client/protocol.py` | NEW — `PunieClient` Protocol |
| `src/punie/client/receiver.py` | NEW — shared message receive loop |
| `src/punie/client/reconnect.py` | NEW — reconnection with backoff |
| `src/punie/client/connection.py` | MODIFY — add connect timeout |
| `src/punie/client/ask_client.py` | MODIFY — use shared receiver |
| `src/punie/client/toad_client.py` | MODIFY — use shared receiver, fix KeyError |
| `src/punie/client/stdio_bridge.py` | MODIFY — fix deprecated API, add timeouts |
| `src/punie/http/websocket.py` | MODIFY — fix error code, magic number |
| `src/punie/http/websocket_client.py` | MODIFY — fix abort log bug |
| `src/punie/toad/agent.py` | NEW — proper Toad agent module |
| `src/punie/toad/websocket_agent.py` | DELETE — dead reference code |
| `scripts/run_toad_websocket.py` | MODIFY — use module, remove prints |
| `src/punie/agent/adapter.py` | MODIFY — fix resume leak |
| `src/punie/testing/fakes.py` | NEW — test fakes for WebSocket |
| `tests/test_toad_roundtrip.py` | NEW — integration test |

## Verification

1. `astral:ruff` — all modified/new Python files pass
2. `astral:ty` — type checks pass
3. `uv run pytest tests/` — all existing + new tests pass
4. `uv run pytest -m integration` — round-trip test passes (requires model server)
5. Manual: `punie serve` + `punie ask "hello"` works reliably
6. Manual: `python scripts/run_toad_websocket.py` initializes without hanging
