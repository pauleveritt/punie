# Plan: HTTP Server Alongside ACP (Roadmap 3.1)

## Context

Punie currently communicates only via ACP stdio (JSON-RPC over stdin/stdout to PyCharm). The mission states "Punie also provides a parallel web interface for interacting with the agent outside the IDE." Phase 3.1 lays the foundation: prove that an HTTP server and ACP stdio can coexist in the same asyncio event loop.

**Framework choice:** Starlette — matches Pydantic AI's built-in serving (`to_a2a()`, `to_ag_ui()`, `to_web()` all return Starlette apps), enabling seamless integration in phases 3.2–3.4.

**Scope:** Minimal proof of dual-protocol architecture. `/health` GET + `/echo` POST endpoints running alongside ACP stdio. Real agent API deferred to 3.2+.

## Key Design Decision

`run_agent()` blocks on `conn.listen()` → `_receive_loop()` which is an `async` coroutine that yields on `await self._reader.readline()`. It does NOT monopolize the event loop. So running it concurrently with a Starlette/uvicorn server via `asyncio.wait()` is correct and simple. No changes to vendored ACP code needed.

## Tasks

### Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-07-http-server/` with:
- **plan.md** — This plan
- **shape.md** — Scope decisions, dual-protocol rationale
- **standards.md** — agent-verification, protocol-first-design, function-based-tests, fakes-over-mocks
- **references.md** — Pydantic AI ASGI patterns, current ACP architecture pointers

### Task 2: Add Dependencies

**Modify `pyproject.toml`:**

`[project] dependencies` — add:
- `starlette>=0.45.0`
- `uvicorn>=0.34.0`

`[dependency-groups] dev` — add:
- `httpx>=0.28.0` (required for Starlette TestClient)

Run `uv sync`.

**Verify:** `uv run python -c "import starlette; import uvicorn; import httpx"`

### Task 3: Create HTTP App (Protocol + Implementation)

Create `src/punie/http/` package:

**`src/punie/http/types.py`** — Protocol (protocol-first-design):
```python
@runtime_checkable
class HttpAppFactory(Protocol):
    def __call__(self) -> ASGIApp: ...
```

**`src/punie/http/app.py`** — Implementation:
- `async def health(request) -> JSONResponse` — returns `{"status": "ok"}`
- `async def echo(request) -> JSONResponse` — returns `{"echo": <body>}`
- `def create_app() -> Starlette` — factory with both routes

**`src/punie/http/__init__.py`** — exports `create_app`, `HttpAppFactory`

### Task 4: Create Dual-Protocol Runner

**`src/punie/http/runner.py`:**

```python
async def run_dual(agent: Agent, app: ASGIApp, *, host="127.0.0.1", port=8000, ...) -> None:
```

Architecture:
1. Create `uvicorn.Server(config)` with the Starlette app
2. Create two asyncio tasks: `_run_acp()` (calls `run_agent()`) and `_run_http()` (calls `server.serve()`)
3. Use `asyncio.wait(return_when=FIRST_COMPLETED)` — when either finishes (e.g., stdin EOF), cancel the other cleanly

This does NOT modify `run_agent()` — full backward compatibility for stdio-only mode.

Update `src/punie/http/__init__.py` to also export `run_dual`.

### Task 5: HTTP Unit Tests

**`tests/test_http_app.py`** — Using Starlette `TestClient` (no real server):
- `test_create_app_satisfies_http_app_factory()` — protocol satisfaction
- `test_health_returns_ok()` — GET /health → 200 `{"status": "ok"}`
- `test_echo_returns_request_body()` — POST /echo with JSON
- `test_echo_with_empty_body()` — POST /echo with `{}`
- `test_echo_rejects_get()` — GET /echo → 405
- `test_unknown_route_returns_404()`

### Task 6: Dual-Protocol Integration Test

**`tests/fixtures/dual_agent.py`** — Subprocess that runs both ACP stdio + HTTP using `run_dual()`. Reuses `MinimalAgent` from existing `minimal_agent.py`.

**`tests/test_dual_protocol.py`** (marked `@pytest.mark.slow`):

**`test_dual_protocol_stdio_and_http()`:**
1. Spawn dual agent subprocess with `_find_free_port()`
2. Poll `/health` until HTTP is ready (`_wait_for_http()`)
3. Verify HTTP `/health` and `/echo` via `httpx.AsyncClient`
4. Verify ACP stdio handshake: `initialize` → `new_session` → `prompt` via `connect_to_agent()`
5. All against the SAME running process

**`test_http_works_after_acp_disconnects()`:**
1. Spawn dual agent, wait for HTTP ready
2. Close stdin (simulate editor disconnect)
3. Assert process exits cleanly (return code 0)

### Task 7: Update Exports and Tech Stack

- **`src/punie/__init__.py`** — add `create_app`, `run_dual` to exports
- **`agent-os/product/tech-stack.md`** — update HTTP server from "to be determined" to "Starlette"

### Task 8: Verification and Roadmap Update

1. `uv run pytest -v` — all existing 68 tests pass (no regressions)
2. `uv run pytest tests/test_http_app.py -v` — HTTP unit tests pass
3. `uv run pytest tests/test_dual_protocol.py -v -m slow` — integration tests pass
4. Use `astral:ty` skill — no type errors on new code
5. Use `astral:ruff` skill — no lint issues
6. `uv run python -c "from punie.http import create_app, run_dual"` — imports work

Update `agent-os/product/roadmap.md` — mark 3.1 complete.

## Files Summary

| Action | Files |
|--------|-------|
| **Create (spec)** | `agent-os/specs/2026-02-07-http-server/{plan,shape,standards,references}.md` |
| **Create (HTTP)** | `src/punie/http/{__init__,types,app,runner}.py` |
| **Create (tests)** | `tests/test_http_app.py`, `tests/test_dual_protocol.py` |
| **Create (fixture)** | `tests/fixtures/dual_agent.py` |
| **Modify** | `pyproject.toml` (deps), `src/punie/__init__.py` (exports) |
| **Modify** | `agent-os/product/{roadmap.md,tech-stack.md}` |

No existing code is modified — only new packages, new tests, dependency additions, and export updates.

## Critical Files (read before implementing)

- `src/punie/acp/core.py` — `run_agent()` (lines 32–65), used unchanged by dual runner
- `src/punie/acp/agent/connection.py` — `AgentSideConnection.listen()` (line 74), the blocking point
- `tests/fixtures/minimal_agent.py` — pattern for dual_agent.py
- `tests/test_stdio_integration.py` — pattern for dual integration tests
