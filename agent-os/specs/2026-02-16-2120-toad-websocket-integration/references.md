# Implementation References

Key files and patterns to reference during implementation.

## Punie WebSocket Client API

### Core Functions

**File:** `src/punie/client/toad_client.py`

```python
async def create_toad_session(
    server_url: str,
    cwd: str,
) -> tuple[ClientConnection, str]:
    """Create session and return (websocket, session_id)."""

async def send_prompt_stream(
    websocket: ClientConnection,
    session_id: str,
    prompt: str,
    on_chunk: Callable[[str, dict[str, Any]], None],
) -> dict[str, Any]:
    """Send prompt and stream updates via callback."""

async def handle_tool_update(
    update: dict[str, Any],
    on_tool_call: Callable[[str, dict[str, Any]], None],
) -> None:
    """Handle tool call updates and dispatch to callback."""

async def run_toad_client(
    server_url: str,
    cwd: str,
    on_update: Callable[[dict[str, Any]], None],
) -> None:
    """Run Toad WebSocket client with persistent connection."""
```

**Documentation:** `docs/toad-client-guide.md`

### Connection Management

**File:** `src/punie/client/connection.py`

```python
async def connect_to_server(server_url: str) -> ClientConnection:
    """Connect to WebSocket server."""

async def initialize_session(websocket: ClientConnection, cwd: str) -> str:
    """Perform ACP handshake and create session."""

@asynccontextmanager
async def punie_session(
    server_url: str,
    cwd: str,
) -> AsyncIterator[tuple[ClientConnection, str]]:
    """Context manager for WebSocket session."""
```

### Callback Signatures

```python
# For send_prompt_stream
def on_chunk(update_type: str, content: dict[str, Any]) -> None:
    """Called for each session_update notification.

    Args:
        update_type: "agent_message_chunk", "tool_call", "tool_call_update", etc.
        content: Full update dict with type-specific fields
    """

# For handle_tool_update
def on_tool_call(tool_call_id: str, tool_data: dict[str, Any]) -> None:
    """Called for tool execution updates.

    Args:
        tool_call_id: Unique identifier for this tool execution
        tool_data: Dict with title, kind, status, content, locations, etc.
    """
```

## Toad Agent Interface (Reference Only)

### Current Stdio Agent

**File:** `~/PycharmProjects/toad/src/toad/acp/agent.py` (lines 1-100)

**Key patterns:**
- Uses `asyncio.create_subprocess_exec` to start agent process
- Communicates via stdin/stdout (stdio transport)
- Implements ACP protocol handling
- Manages agent lifecycle (start, send, stop)

**Interface to match:**
```python
class Agent:
    async def start(self) -> None:
        """Start the agent process."""

    async def send_prompt(self, prompt: str) -> AsyncIterator[dict]:
        """Send prompt and yield updates."""

    async def stop(self) -> None:
        """Stop the agent process."""
```

### AgentBase Interface

**File:** `~/PycharmProjects/toad/src/toad/agent.py` (lines 1-50)

**Base class that defines:**
- Common agent interface
- Configuration handling
- Session management patterns

## Update Types

From `src/punie/acp/schema.py`:

### Agent Message Chunks

```python
{
    "sessionUpdate": "agent_message_chunk",
    "content": {"type": "text", "text": "Hello world"}
}
```

### Tool Calls

```python
{
    "sessionUpdate": "tool_call",
    "tool_call_id": "tool-123",
    "title": "Read /tmp/test.py",
    "kind": "read",
    "status": "pending",
    "locations": [{"path": "/tmp/test.py"}]
}
```

### Tool Call Updates

```python
{
    "sessionUpdate": "tool_call_update",
    "tool_call_id": "tool-123",
    "status": "completed"
}
```

## Testing Patterns

### TestClient Pattern

**From existing tests:**

```python
from starlette.testclient import TestClient
from punie.http.app import create_app

def test_example():
    """Test using TestClient."""
    agent = PunieAgent(model="test")
    app = create_app(agent)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            # Initialize
            ws.send_json({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocol_version": 1},
            })
            response = ws.receive_json()

            # Create session
            ws.send_json({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "new_session",
                "params": {"cwd": "/tmp", "mcp_servers": []},
            })
            session_response = ws.receive_json()
            session_id = session_response["result"]["sessionId"]

            # Send prompt
            ws.send_json({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "prompt",
                "params": {
                    "session_id": session_id,
                    "prompt": [{"type": "text", "text": "Hello"}],
                },
            })
```

### Callback Testing Pattern

```python
def test_streaming_callback():
    """Test streaming via callback."""
    received = []

    def on_chunk(update_type, content):
        received.append((update_type, content))

    # Use callback
    result = await send_prompt_stream(ws, sid, "Hello", on_chunk)

    # Assert callbacks were invoked
    assert len(received) > 0
    assert received[0][0] == "agent_message_chunk"
```

## Error Handling Patterns

### Connection Errors

```python
try:
    websocket, session_id = await create_toad_session(url, cwd)
except websockets.exceptions.WebSocketException as e:
    logger.error(f"Failed to connect: {e}")
    raise ConnectionError(f"Cannot reach Punie server at {url}")
```

### Timeout Handling

```python
try:
    result = await send_prompt_stream(ws, sid, prompt, on_chunk)
except RuntimeError as e:
    if "No response from server" in str(e):
        logger.error("Prompt timed out after 5 minutes")
        # Handle timeout...
```

### Disconnect Handling

```python
try:
    result = await send_prompt_stream(ws, sid, prompt, on_chunk)
except ConnectionError as e:
    logger.error(f"Connection lost: {e}")
    # Attempt reconnection...
```

## Related Documentation

- **Client Setup Guide:** `docs/client-setup-guide.md`
- **Toad Client Guide:** `docs/toad-client-guide.md`
- **WebSocket API:** `docs/websocket-api.md`
- **ACP Schema:** `src/punie/acp/schema.py`
- **Phase 28 Architecture:** `docs/phase28-server-architecture.md`
- **Phase 29 Diary:** `docs/diary/2026-02-16-phase29-toad-websocket-client.md`

## Example Code to Reference

### Ask Client Example

**File:** `src/punie/client/ask_client.py`

Shows similar pattern:
- Creates session
- Sends prompt with streaming
- Handles callbacks
- Cleanup on exit

### Serve Example

**File:** `examples/13_serve_dual.py`

Shows:
- Server startup
- HTTP/WebSocket dual protocol
- Application creation

## Key Takeaways

1. **Reuse existing functions** - Don't duplicate WebSocket logic
2. **Follow callback pattern** - Map Punie callbacks to Toad messages
3. **Handle errors gracefully** - Connection, timeout, disconnect
4. **Test with TestClient** - Fast, reliable, no external dependencies
5. **Keep it simple** - Wrapper should be thin layer over client utilities
