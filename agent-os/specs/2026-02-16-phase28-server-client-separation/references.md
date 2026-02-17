# References for Phase 28

This document links to existing code patterns and infrastructure that informed the Phase 28 implementation.

## Existing WebSocket Infrastructure

### Server-Side WebSocket Handler

**Location:** `src/punie/http/websocket.py`

**Relevance:** Already implements full ACP protocol over WebSocket on server side.

**Key patterns:**
- Client registration: `await agent.register_client(client)`
- Message dispatch: `_dispatch_method()` routes to agent methods
- Error handling: JSON-RPC error responses with proper codes
- Cleanup: `await agent.unregister_client(client_id)` on disconnect

**Example (client registration):**
```python
async def websocket_endpoint(websocket: WebSocket, agent: PunieAgent) -> None:
    await websocket.accept()
    client = WebSocketClient(websocket)
    client_id = await agent.register_client(client)
    logger.info(f"Registered WebSocket client {client_id}")
    # ... handle messages ...
```

### WebSocketClient Wrapper

**Location:** `src/punie/http/websocket_client.py`

**Relevance:** Shows how to wrap WebSocket with ACP Client protocol.

**Key patterns:**
- Request/response matching with futures
- Notification handling (no response expected)
- Pending request tracking for cleanup

**Example (send request):**
```python
async def send_request(self, request: dict) -> dict:
    request_id = request["id"]
    future = asyncio.Future()
    self._pending_requests[request_id] = future
    await self._websocket.send_text(json.dumps(request))
    return await future
```

### Transport Abstraction

**Location:** `src/punie/acp/transport.py`

**Relevance:** Shows protocol-based abstraction over stdio and WebSocket transports.

**Key patterns:**
- Protocol definition: `async def send(data: str)`, `async def receive() -> str`
- StdioTransport: Wraps asyncio StreamReader/Writer
- WebSocketTransport: Wraps Starlette WebSocket

**Example (WebSocketTransport):**
```python
class WebSocketTransport:
    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket

    async def send(self, data: str) -> None:
        await self._websocket.send_text(data)

    async def receive(self) -> str:
        return await self._websocket.receive_text()
```

## Similar Patterns in Codebase

### run_dual() Function

**Location:** `src/punie/http/runner.py`

**Relevance:** Template for `run_http()` implementation (remove stdio component).

**Key patterns:**
- uvicorn.Server configuration
- Task creation and cancellation
- FIRST_COMPLETED wait pattern (removed in `run_http()`)

**Example (uvicorn setup):**
```python
config = uvicorn.Config(
    app,
    host=host,
    port=port,
    log_level=log_level,
    access_log=False,
)
server = uvicorn.Server(config)
await server.serve()  # Run indefinitely
```

### ACP Agent Stdio Runner

**Location:** `src/punie/acp/__init__.py` (`run_agent()` function)

**Relevance:** Shows stdio transport setup (replaced by WebSocket in clients).

**Key patterns:**
- StreamReader/Writer setup
- Protocol wrapping (AgentSideConnection)
- Message loop with graceful shutdown

**Example (stdio setup):**
```python
reader = asyncio.StreamReader()
protocol = asyncio.StreamReaderProtocol(reader)
await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
```

## External Library References

### websockets Library

**Documentation:** https://websockets.readthedocs.io/en/stable/

**Usage in Phase 28:**
- Client connections: `await websockets.connect(url)`
- Send/receive: `await ws.send(data)`, `data = await ws.recv()`
- Close: `await ws.close()`

**Example:**
```python
import websockets

async def connect_to_server(url: str):
    websocket = await websockets.connect(url)
    await websocket.send('{"jsonrpc":"2.0","id":1,"method":"ping"}')
    response = await websocket.recv()
    await websocket.close()
    return response
```

### asyncio Context Managers

**Documentation:** https://docs.python.org/3/library/contextlib.html#contextlib.asynccontextmanager

**Usage in Phase 28:**
- `punie_session()` context manager for connection lifecycle
- Ensures cleanup (close WebSocket) even on exceptions

**Example:**
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def punie_session(server_url: str, cwd: str):
    websocket = await connect_to_server(server_url)
    try:
        session_id = await initialize_session(websocket, cwd)
        yield websocket, session_id
    finally:
        await websocket.close()
```

### Typer CLI Framework

**Documentation:** https://typer.tiangolo.com/

**Usage in Phase 28:**
- Command definitions: `@app.command()`, `@app.callback()`
- Options and arguments: `typer.Option()`, `typer.Argument()`
- Async support: `asyncio.run()` at CLI entry points

**Example:**
```python
@app.command("ask")
def ask(
    prompt: str = typer.Argument(...),
    server: str = typer.Option("ws://localhost:8000/ws"),
):
    """Ask question via WebSocket."""
    asyncio.run(run_ask_client(server, prompt, Path.cwd()))
```

## JSON-RPC 2.0 Protocol

**Specification:** https://www.jsonrpc.org/specification

**Key concepts used:**
- Request format: `{"jsonrpc": "2.0", "id": <id>, "method": <name>, "params": <dict>}`
- Response format: `{"jsonrpc": "2.0", "id": <id>, "result": <dict>}`
- Error format: `{"jsonrpc": "2.0", "id": <id>, "error": {"code": <int>, "message": <str>}}`
- Notifications: Requests without "id" field (no response expected)

**Application in Phase 28:**
- All client/server communication uses JSON-RPC 2.0
- Clients skip notifications when waiting for specific response
- Error responses use standard error codes (-32700 = Parse error, -32603 = Internal error)

## Agent Communication Protocol (ACP)

**Specification:** Internal protocol defined in `src/punie/acp/schema.py`

**Key methods used:**
- `initialize`: Handshake with protocol version
- `new_session`: Create new session with workspace
- `prompt`: Send prompt to agent, receive session_update notifications

**Handshake sequence:**
```
Client → Server: {"method": "initialize", "params": {"protocol_version": 1}}
Server → Client: {"result": {"protocol_version": 1, "agent_info": {...}}}

Client → Server: {"method": "new_session", "params": {"cwd": "/workspace", "mode": "code"}}
Server → Client: {"result": {"session_id": "punie-session-abc123"}}

Client → Server: {"method": "prompt", "params": {"session_id": "...", "prompt": [...]}}
Server → Client: {"method": "session_update", "params": {"update": {...}}}  (notification)
Server → Client: {"result": {}}  (final response)
```
