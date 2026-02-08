# Standards Applied: HTTP Server Alongside ACP

This spec adheres to the following Agent OS standards:

## agent-verification

**Standard:** Every feature must include automated tests that verify the agent's behavior matches the specification.

**Application:**
- **Unit tests** (`test_http_app.py`) — Verify `/health`, `/echo` endpoint logic with Starlette TestClient
- **Integration tests** (`test_dual_protocol.py`) — Verify ACP stdio + HTTP concurrency in real subprocess
- **Protocol satisfaction test** — Verify `create_app()` satisfies `HttpAppFactory` protocol
- **Error case coverage** — 404, 405, malformed input, clean shutdown
- **All tests automated** — Run via `uv run pytest`, no manual verification

**Critical Tests:**
- `test_dual_protocol_stdio_and_http()` — Both protocols work simultaneously
- `test_http_works_after_acp_disconnects()` — Clean shutdown when ACP disconnects
- `test_health_returns_ok()` — Basic HTTP endpoint functionality
- `test_echo_returns_request_body()` — JSON request/response handling

## protocol-first-design

**Standard:** Define protocols (typing.Protocol) before implementations. Protocols document contracts and enable structural subtyping.

**Application:**
- **`HttpAppFactory` protocol** defined in `src/punie/http/types.py`:
  ```python
  @runtime_checkable
  class HttpAppFactory(Protocol):
      def __call__(self) -> ASGIApp: ...
  ```
- **Implementation** (`create_app()`) comes after protocol definition
- **Runtime checkable** — Enables `isinstance()` checks in tests
- **Clear contract** — Factory returns ASGI app, no required parameters

**Benefits:**
- Type checkers verify `create_app()` satisfies protocol
- Test explicitly verifies protocol satisfaction
- Future implementations (e.g., `create_production_app()`) must match contract

## function-based-tests

**Standard:** Write tests as functions, not classes. Use parametrization and fixtures instead of test class hierarchies.

**Application:**
- All tests in `test_http_app.py` and `test_dual_protocol.py` are functions
- No test classes, no inheritance hierarchies
- Fixtures for shared setup (`dual_agent.py` fixture reuses `MinimalAgent`)
- Descriptive names: `test_dual_protocol_stdio_and_http()`, `test_health_returns_ok()`

**Example:**
```python
async def test_health_returns_ok():
    """GET /health returns 200 with status ok."""
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

## fakes-over-mocks

**Standard:** Prefer real implementations and test doubles (fakes) over mocks. Use mocks only when necessary for isolation.

**Application:**
- **Real Starlette app** — Unit tests use `TestClient` with real `create_app()`, not mocked routes
- **Real subprocess** — Integration tests spawn actual dual agent, not mocked processes
- **Real HTTP client** — `httpx.AsyncClient` makes real requests to subprocess
- **Real ACP connection** — `connect_to_agent()` does full handshake, not mocked messages
- **MinimalAgent fake** — Reuses existing test agent, doesn't mock Agent interface

**No Mocks Used:**
- No `unittest.mock.Mock` or `patch()`
- No mocked asyncio tasks
- No mocked HTTP responses

**Why This Works:**
- Starlette TestClient is fast and doesn't require real sockets
- Subprocess tests are slower but marked `@pytest.mark.slow`
- Real implementations catch integration bugs that mocks hide

## Additional Standards

### Backward Compatibility
- No changes to vendored ACP code in `src/punie/acp/`
- `run_agent()` remains usable for stdio-only mode
- New `run_dual()` is opt-in addition, not replacement

### Type Safety
- All new code includes type annotations
- Verified with `astral:ty` skill before commit
- Protocols enable structural type checking

### Code Organization
- New package `src/punie/http/` for HTTP-specific code
- Clear separation: `types.py` (protocols), `app.py` (endpoints), `runner.py` (lifecycle)
- No HTTP code mixed into ACP modules

### Documentation
- Spec directory with plan, shape, standards, references
- Docstrings on all public functions
- Integration test docstrings explain what's being verified
