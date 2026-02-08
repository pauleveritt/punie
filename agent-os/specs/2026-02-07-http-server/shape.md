# Shape: HTTP Server Alongside ACP

## Problem Statement

Punie currently runs only as an ACP agent over stdio (JSON-RPC to PyCharm). Mission requirement: "Punie also provides a parallel web interface for interacting with the agent outside the IDE." This spec establishes the foundation for dual-protocol operation.

## Scope Decisions

### In Scope (Phase 3.1)
- **Dual-protocol runner** — Run ACP stdio and HTTP server concurrently in the same asyncio event loop
- **Minimal HTTP API** — `/health` GET and `/echo` POST endpoints to prove the architecture
- **Framework choice** — Starlette + uvicorn for HTTP serving
- **Clean lifecycle** — When either protocol terminates (e.g., stdin EOF), shut down both gracefully
- **Full test coverage** — Unit tests for HTTP endpoints, integration tests for concurrent operation

### Out of Scope (Deferred to 3.2+)
- **Real agent API over HTTP** — No `/prompt`, `/sessions`, etc. (phase 3.2)
- **Pydantic AI ASGI integration** — `to_a2a()`, `to_ag_ui()`, `to_web()` mounting (phases 3.2–3.4)
- **Authentication** — No auth layer yet
- **WebSocket support** — HTTP only, no WS endpoints
- **Configuration** — Hardcoded host/port, no CLI args or env vars
- **Production deployment** — No Docker, systemd, reverse proxy guidance

## Key Architecture Decisions

### 1. Framework: Starlette + uvicorn

**Rationale:**
- Pydantic AI's built-in serving methods (`to_a2a()`, `to_ag_ui()`, `to_web()`) all return Starlette ASGI apps
- Enables seamless mounting in phases 3.2–3.4 without adapter layers
- Lightweight, modern, excellent async support
- Native ASGI 3.0, works with any ASGI server (uvicorn chosen for familiarity)

**Alternatives Considered:**
- **FastAPI:** Heavier, includes features (OpenAPI docs, validation) not needed yet. Starlette is FastAPI's foundation — can upgrade later if needed.
- **aiohttp:** Different paradigm (not ASGI), would complicate Pydantic AI integration.

### 2. Concurrent Runner: asyncio.wait(FIRST_COMPLETED)

**Architecture:**
```python
async def run_dual(agent, app, *, host, port):
    config = uvicorn.Config(app, host=host, port=port, ...)
    server = uvicorn.Server(config)

    acp_task = asyncio.create_task(run_agent(agent))
    http_task = asyncio.create_task(server.serve())

    done, pending = await asyncio.wait({acp_task, http_task}, return_when=FIRST_COMPLETED)
    for task in pending:
        task.cancel()
```

**Rationale:**
- `run_agent()` blocks on `await conn.listen()` → `_receive_loop()` → `await reader.readline()`
- This is a proper async coroutine — yields control when waiting for stdin
- HTTP server is also async — both can run concurrently in same event loop
- When stdin closes (IDE disconnect), ACP task completes → cancels HTTP → clean shutdown
- No threads, no subprocesses, no vendored ACP modifications required

**Why This Works:**
- Verified `run_agent()` implementation — it's `async`, not blocking sync code
- `AgentSideConnection.listen()` calls `Connection.main_loop()` which awaits I/O
- Python's asyncio schedules both coroutines cooperatively

### 3. No Changes to Vendored ACP Code

**Critical Constraint:**
- ACP SDK is vendored from Anthropic's reference implementation
- Must remain unmodified to enable future syncs
- All dual-protocol logic lives in new `punie.http` package
- `run_agent()` remains usable for stdio-only mode (backward compatible)

## Testing Strategy

### Unit Tests (Starlette TestClient)
- Protocol satisfaction — `create_app()` satisfies `HttpAppFactory`
- Endpoint behavior — `/health`, `/echo` logic with mocked requests
- Error handling — 404, 405, malformed JSON

**Why TestClient:**
- No real server/sockets — faster, more reliable in CI
- Sufficient for endpoint logic verification

### Integration Tests (Subprocess + HTTP + ACP)
- Spawn real dual agent subprocess
- Verify HTTP `/health` and `/echo` via `httpx.AsyncClient`
- Verify ACP stdio handshake via `connect_to_agent()`
- Both protocols against the SAME process
- Marked `@pytest.mark.slow` (use actual network, slower)

**Critical Validation:**
- Proves asyncio concurrency works in practice
- Catches port binding issues, race conditions, shutdown bugs
- Ensures backward compatibility (ACP stdio still works)

## Risks and Mitigations

### Risk: Event Loop Starvation
**Scenario:** One protocol monopolizes the event loop
**Mitigation:** Both `run_agent()` and `server.serve()` are properly async — verified by reading source
**Validation:** Integration test proves both respond concurrently

### Risk: Port Already in Use
**Scenario:** Test runs fail due to port conflicts
**Mitigation:** Integration test uses `_find_free_port()` to dynamically allocate
**Fallback:** Test skipped if port allocation fails (not test failure)

### Risk: Graceful Shutdown Failure
**Scenario:** Cancelling tasks leaves resources open
**Mitigation:** uvicorn.Server has built-in shutdown hooks; ACP connection closes on task cancel
**Validation:** `test_http_works_after_acp_disconnects()` verifies clean exit

## Future Evolution (Post-3.1)

### Phase 3.2: Agent API over HTTP
- Add `/sessions`, `/prompt` endpoints
- Integrate with existing `Agent` interface
- HTTP → ACP protocol bridge

### Phase 3.3: Pydantic AI Integration
- Mount `to_a2a()` at `/a2a/*`
- Mount `to_ag_ui()` at `/ag-ui/*`
- Mount `to_web()` at `/web/*`

### Phase 3.4: Web UI
- Serve static frontend at `/`
- Use Pydantic AI's built-in web UI or custom React/Vue

### Production Readiness
- Configuration via CLI args / env vars
- TLS support
- Reverse proxy guidance (nginx/Traefik)
- Monitoring and health checks
- Docker images

## Success Criteria

Phase 3.1 is complete when:
1. `run_dual()` runs ACP stdio and HTTP server concurrently
2. `/health` and `/echo` endpoints work and are tested
3. Integration tests prove both protocols work in same process
4. All 68 existing tests still pass (no regressions)
5. Type checking and linting pass on new code
6. No changes to vendored ACP code
7. Roadmap 3.1 marked complete
