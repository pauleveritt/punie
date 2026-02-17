# Standards for Phase 28

This spec applies the following Agent OS standards:

## agent-verification

Always included to ensure proper verification using Astral skills.

**Application in Phase 28:**
- Use `astral:ruff` for linting client modules
- Use `astral:ty` for type checking new code
- Run `astral:uv run pytest` for integration tests

**Verification commands:**
```bash
# Type checking
astral:ty check src/punie/client/

# Linting
astral:ruff check src/punie/client/

# Tests
astral:uv run pytest tests/test_server_client_integration.py -v
```

## function-based-tests

All new tests use function-based approach (no classes).

**Application in Phase 28:**
- Integration tests in `tests/test_server_client_integration.py`
- Client unit tests use `async def test_*()` pattern
- No test classes (follow existing Punie test conventions)

**Example:**
```python
async def test_server_only_mode():
    """Test that server runs without stdio component."""
    agent = PunieAgent(model="test")
    app = create_app(agent)
    server_task = asyncio.create_task(run_http(agent, app, host="127.0.0.1", port=8001))
    await asyncio.sleep(0.5)

    # Connect and verify
    async with punie_session("ws://localhost:8001/ws", str(Path.cwd())) as (ws, sid):
        assert sid.startswith("punie-session-")

    server_task.cancel()
```

## websocket-protocol

WebSocket clients must follow JSON-RPC 2.0 protocol.

**Application in Phase 28:**
- All client requests use JSON-RPC 2.0 format:
  ```json
  {
    "jsonrpc": "2.0",
    "id": <unique-id>,
    "method": "<method-name>",
    "params": {...}
  }
  ```
- Clients handle bidirectional messages (requests + notifications)
- Clients must close connections gracefully
- Error responses follow JSON-RPC error format

**Key patterns:**
1. **Request/Response:**
   ```python
   request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {...}}
   await websocket.send(json.dumps(request))
   response = json.loads(await websocket.recv())
   ```

2. **Notification handling:**
   ```python
   # Skip notifications when waiting for response
   if "method" in message:
       logger.debug(f"Skipping notification: {message['method']}")
       continue
   ```

3. **Graceful close:**
   ```python
   finally:
       await websocket.close()
       logger.info("WebSocket connection closed")
   ```

## async-consistency

All client code uses async/await (no sync wrappers).

**Application in Phase 28:**
- All client functions are `async def`
- Use `asyncio.run()` at CLI entry points only
- No blocking I/O in async functions

**Pattern:**
```python
# ✅ CORRECT: Async all the way
async def run_ask_client(server_url: str, prompt: str, workspace: Path) -> str:
    async with punie_session(server_url, str(workspace)) as (ws, sid):
        # Send prompt, receive response
        ...

# ✅ CORRECT: Call from CLI with asyncio.run()
def ask(prompt: str, server: str, workspace: Path):
    asyncio.run(run_ask_client(server, prompt, workspace))
```

## logging-standards

Use Python logging with appropriate levels.

**Application in Phase 28:**
- `logger.debug()` for protocol messages (JSON-RPC details)
- `logger.info()` for lifecycle events (connect, disconnect, session create)
- `logger.warning()` for recoverable errors (invalid JSON, skip notification)
- `logger.error()` for serious errors (connection failure, server error)

**Example:**
```python
logger = logging.getLogger(__name__)

async def connect_to_server(url: str):
    logger.debug(f"Connecting to {url}")
    websocket = await websockets.connect(url)
    logger.info(f"Connected to {url}")
    return websocket
```

## error-handling

Provide clear error messages with actionable guidance.

**Application in Phase 28:**
- Connection failures show server URL and suggest checking server status
- Invalid responses show JSON-RPC error details
- CLI commands catch exceptions and exit with code 1

**Example:**
```python
try:
    asyncio.run(run_ask_client(server, prompt, workspace))
except Exception as exc:
    typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
    typer.echo("\nMake sure the server is running:")
    typer.echo(f"  punie serve --model <model-name>")
    raise typer.Exit(1)
```

## documentation-standards

All public functions have docstrings with Args, Returns, Raises, Example.

**Application in Phase 28:**
- All client functions have comprehensive docstrings
- Examples show typical usage patterns
- Raises section documents expected exceptions

**Example:**
```python
async def send_request(
    websocket: WebSocketClientProtocol, method: str, params: dict[str, Any]
) -> dict[str, Any]:
    """Send JSON-RPC request and wait for response.

    Args:
        websocket: Connected WebSocket client
        method: JSON-RPC method name
        params: Method parameters dict

    Returns:
        Response result dict (raises if error present)

    Raises:
        RuntimeError: If response contains error
        websockets.exceptions.WebSocketException: If connection fails

    Example:
        result = await send_request(ws, "initialize", {"protocol_version": 1})
        print(result["protocol_version"])
    """
```

## type-annotations

All functions have complete type annotations.

**Application in Phase 28:**
- All parameters and return types annotated
- Use `from __future__ import annotations` for forward references
- Import typing utilities as needed

**Example:**
```python
from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator

from websockets.client import WebSocketClientProtocol

@asynccontextmanager
async def punie_session(
    server_url: str, cwd: str
) -> AsyncIterator[tuple[WebSocketClientProtocol, str]]:
    """Context manager for session lifecycle."""
    ...
```
