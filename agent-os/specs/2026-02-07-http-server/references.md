# References: HTTP Server Alongside ACP

## Pydantic AI ASGI Patterns

Pydantic AI provides three built-in ASGI serving methods, all returning Starlette apps:

### Agent-to-Agent Communication (A2A)
```python
from pydantic_ai import Agent

agent = Agent("openai:gpt-4")
asgi_app = agent.to_a2a()  # Returns Starlette app
# Mount at /a2a/* for agent-to-agent protocol
```

**Phase:** 3.3 (future)
**URL:** `/a2a/*`
**Purpose:** Machine-to-machine agent communication

### Agent UI
```python
asgi_app = agent.to_ag_ui()  # Returns Starlette app
# Mount at /ag-ui/* for agent management interface
```

**Phase:** 3.3 (future)
**URL:** `/ag-ui/*`
**Purpose:** Agent configuration and management UI

### Web UI
```python
asgi_app = agent.to_web()  # Returns Starlette app
# Mount at /web/* for end-user chat interface
```

**Phase:** 3.4 (future)
**URL:** `/web/*`
**Purpose:** End-user web chat interface

### Why This Matters for 3.1

**Starlette as Foundation:**
- All Pydantic AI serving methods return Starlette `ASGIApp` instances
- By using Starlette in 3.1, we enable seamless mounting in 3.2–3.4
- No adapter layers or framework conversions needed

**Mounting Pattern (Future):**
```python
from starlette.applications import Starlette
from starlette.routing import Mount

app = Starlette(routes=[
    Route("/health", health),  # Our endpoints (3.1)
    Route("/echo", echo),
    Route("/sessions", list_sessions),  # Agent API (3.2)
    Route("/prompt", prompt),
    Mount("/a2a", agent.to_a2a()),  # Pydantic AI (3.3)
    Mount("/ag-ui", agent.to_ag_ui()),
    Mount("/web", agent.to_web()),  # Web UI (3.4)
])
```

## Current ACP Architecture

### Entry Point: `run_agent()`

**Location:** `src/punie/acp/core.py:32–65`

```python
async def run_agent(
    agent: Agent,
    input_stream: Any = None,
    output_stream: Any = None,
    *,
    use_unstable_protocol: bool = False,
    **connection_kwargs: Any,
) -> None:
    """Run an ACP agent over the given input/output streams."""
    from .stdio import stdio_streams

    if input_stream is None and output_stream is None:
        output_stream, input_stream = await stdio_streams()
    conn = AgentSideConnection(
        agent,
        input_stream,
        output_stream,
        listening=False,
        use_unstable_protocol=use_unstable_protocol,
        **connection_kwargs,
    )
    await conn.listen()
```

**Key Properties:**
- **Async coroutine** — Does not block event loop
- **Yields on I/O** — `await conn.listen()` → `await reader.readline()`
- **Default streams** — Uses stdin/stdout if not provided
- **Composable** — Can be wrapped in asyncio tasks

### Connection Lifecycle: `AgentSideConnection.listen()`

**Location:** `src/punie/acp/agent/connection.py:74–76`

```python
async def listen(self) -> None:
    """Start listening for incoming messages."""
    await self._conn.main_loop()
```

**Key Properties:**
- **Async I/O** — `main_loop()` awaits on stdin reads
- **Graceful shutdown** — Returns when stdin closes (EOF)
- **No threads** — Pure asyncio, no thread pool

### Message Loop: `Connection._receive_loop()`

**Location:** `src/punie/acp/agent/connection.py` (internal)

The receive loop blocks on:
```python
line = await self._reader.readline()
```

This is the critical async point — yields control to event loop while waiting for stdin.

## Test Patterns

### Subprocess Test Pattern

**Location:** `tests/fixtures/minimal_agent.py`

```python
class MinimalAgent(Agent):
    """Minimal agent implementation for testing stdio connections."""
    # Implements all required Agent methods minimally

async def main() -> None:
    """Run the minimal agent over stdio."""
    agent = MinimalAgent()
    await run_agent(agent)

if __name__ == "__main__":
    asyncio.run(main())
```

**Usage:**
```python
# In test
process = await asyncio.create_subprocess_exec(
    sys.executable, "-m", "tests.fixtures.minimal_agent",
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
```

**Pattern for 3.1:**
- Create `tests/fixtures/dual_agent.py` with same structure
- Replace `run_agent()` with `run_dual(agent, app, port=...)`
- Subprocess now serves both ACP stdio and HTTP

### Integration Test Pattern

**Location:** `tests/test_stdio_integration.py`

```python
@pytest.mark.slow
async def test_stdio_basic_flow(minimal_agent: tuple[Process, asyncio.Queue]):
    """Test basic ACP flow over stdio."""
    process, output_queue = minimal_agent
    conn = connect_to_agent(process.stdin, output_queue)

    # Send initialize
    response = await conn.send_request("initialize", {...})
    assert response["protocol_version"] == PROTOCOL_VERSION

    # Send new_session
    response = await conn.send_request("new_session", {...})
    session_id = response["session_id"]

    # Send prompt
    response = await conn.send_request("prompt", {...})
    assert response["stop_reason"] == "end_turn"
```

**Pattern for 3.1:**
- Same ACP verification via `connect_to_agent()`
- Add HTTP verification via `httpx.AsyncClient`
- Both against same subprocess
- Marked `@pytest.mark.slow`

## External Documentation

### Starlette
- **Docs:** https://www.starlette.io/
- **TestClient:** https://www.starlette.io/testclient/
- **Routing:** https://www.starlette.io/routing/

### uvicorn
- **Docs:** https://www.uvicorn.org/
- **Server API:** https://www.uvicorn.org/deployment/#running-programmatically
- **Config:** https://www.uvicorn.org/settings/

### ASGI Spec
- **ASGI 3.0:** https://asgi.readthedocs.io/en/latest/specs/main.html
- **Lifespan Protocol:** https://asgi.readthedocs.io/en/latest/specs/lifespan.html

### asyncio Patterns
- **Task Management:** https://docs.python.org/3/library/asyncio-task.html
- **wait():** https://docs.python.org/3/library/asyncio-task.html#asyncio.wait
- **Cancellation:** https://docs.python.org/3/library/asyncio-task.html#task-cancellation

## Implementation Notes

### Port Finding
Use socket binding to find free port:
```python
def _find_free_port() -> int:
    """Find a free port for testing."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
```

### HTTP Readiness Polling
Poll `/health` until server is ready:
```python
async def _wait_for_http(port: int, timeout: float = 5.0) -> None:
    """Wait for HTTP server to be ready."""
    import httpx
    start = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout:
            try:
                response = await client.get(f"http://127.0.0.1:{port}/health")
                if response.status_code == 200:
                    return
            except httpx.ConnectError:
                await asyncio.sleep(0.1)
    raise TimeoutError(f"HTTP server not ready after {timeout}s")
```

### Graceful Shutdown
```python
done, pending = await asyncio.wait(
    {acp_task, http_task},
    return_when=asyncio.FIRST_COMPLETED
)

# Cancel remaining tasks
for task in pending:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
```

## Related Roadmap Items

- **3.1 (this spec)** — HTTP server alongside ACP (minimal endpoints)
- **3.2** — Agent API over HTTP (`/sessions`, `/prompt`, etc.)
- **3.3** — Mount Pydantic AI ASGI apps (`to_a2a()`, `to_ag_ui()`)
- **3.4** — Web UI for browser-based agent interaction

## Future Considerations

### Configuration (Post-3.1)
- CLI args: `punie serve --host 0.0.0.0 --port 8000`
- Env vars: `PUNIE_HOST`, `PUNIE_PORT`
- Config file: `punie.toml`

### Authentication (Post-3.1)
- API key middleware
- JWT token validation
- OAuth integration

### Monitoring (Post-3.1)
- Prometheus `/metrics` endpoint
- Structured logging
- Request tracing

### Production Deployment (Post-3.1)
- Docker images
- systemd units
- Reverse proxy examples (nginx, Traefik)
- TLS configuration
