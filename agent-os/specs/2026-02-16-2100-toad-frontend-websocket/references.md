# Implementation References for Phase 29

Key patterns and implementations to reference when building the Toad WebSocket client.

---

## 1. Connection Management

### Pattern: WebSocket Connection

**Source:** `src/punie/client/connection.py` (lines 24-45)

```python
async def connect_to_server(url: str) -> ClientConnection:
    """Connect to Punie server via WebSocket.

    Returns:
        Connected WebSocket client

    Raises:
        websockets.exceptions.WebSocketException: If connection fails
    """
    logger.debug(f"Connecting to {url}")
    websocket = await websockets.connect(url)
    logger.info(f"Connected to {url}")
    return websocket
```

**Key Points:**
- Use `websockets.connect(url)` directly
- Log connection attempts and success
- Return `ClientConnection` type

---

### Pattern: ACP Handshake

**Source:** `src/punie/client/connection.py` (lines 113-156)

```python
async def initialize_session(websocket: ClientConnection, cwd: str) -> str:
    """Perform ACP handshake (initialize → new_session).

    Args:
        websocket: Connected WebSocket client
        cwd: Current working directory for session

    Returns:
        Session ID
    """
    # Step 1: Initialize
    init_result = await send_request(
        websocket,
        "initialize",
        {
            "protocol_version": 1,
            "client_info": {"name": "punie-client", "version": "0.1.0"},
        },
    )

    # Step 2: Create new session
    session_result = await send_request(
        websocket,
        "new_session",
        {"cwd": cwd, "mode": "code", "mcp_servers": []},
    )
    session_id = session_result["sessionId"]  # camelCase in response
    return session_id
```

**Key Points:**
- Two-step handshake: initialize → new_session
- Response uses camelCase (sessionId, not session_id)
- Return session_id as string

---

### Pattern: Session Context Manager

**Source:** `src/punie/client/connection.py` (lines 159-193)

```python
@asynccontextmanager
async def punie_session(
    server_url: str, cwd: str
) -> AsyncIterator[tuple[ClientConnection, str]]:
    """Context manager for session lifecycle.

    Yields:
        (websocket, session_id) tuple
    """
    websocket = await connect_to_server(server_url)
    try:
        session_id = await initialize_session(websocket, cwd)
        yield websocket, session_id
    finally:
        try:
            await websocket.close()
        except Exception as exc:
            logger.debug(f"Error closing WebSocket: {exc}")
```

**Key Points:**
- Use `@asynccontextmanager` for clean resource management
- Ensure websocket.close() in finally block
- Catch and log close errors (don't propagate)

---

## 2. Request/Response Pattern

### Pattern: JSON-RPC Request

**Source:** `src/punie/client/connection.py` (lines 48-110)

```python
async def send_request(
    websocket: ClientConnection, method: str, params: dict[str, Any]
) -> dict[str, Any]:
    """Send JSON-RPC request and wait for response.

    Returns:
        Response result dict (raises if error present)

    Raises:
        RuntimeError: If response contains error or timeout
        ConnectionError: If WebSocket disconnects
    """
    # Generate unique request ID (Issue #4: use UUID to prevent collision)
    request_id = str(uuid.uuid4())

    # Send request
    request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    await websocket.send(json.dumps(request))

    # Wait for response (Issue #1: add timeout protection)
    while True:
        try:
            data = await asyncio.wait_for(websocket.recv(), timeout=30.0)
        except asyncio.TimeoutError:
            raise RuntimeError(f"Timeout waiting for {method} response after 30s")
        except websockets.exceptions.ConnectionClosed as exc:
            raise ConnectionError(f"Server disconnected during {method}: {exc}")

        # Parse JSON (Issue #2: handle malformed data)
        try:
            message = json.loads(data)
        except json.JSONDecodeError as exc:
            logger.warning(f"Invalid JSON from server: {exc}")
            continue  # Skip and wait for next message

        # Skip notifications
        if "method" in message:
            logger.debug(f"Skipping notification: {message['method']}")
            continue

        # Check if this is our response
        if message.get("id") == request_id:
            if "error" in message:
                error = message["error"]
                raise RuntimeError(f"{method} failed: {error.get('message')}")
            return message.get("result", {})
```

**Critical Patterns:**
1. **UUID request IDs** - Prevents collision in concurrent requests
2. **30-second timeout** - Protection against hung connections
3. **Skip notifications** - Only process response with matching ID
4. **Handle malformed JSON** - Log and continue, don't crash
5. **Check error field** - Raise RuntimeError if server returns error

---

## 3. Streaming Pattern

### Pattern: Prompt with Streaming Response

**Source:** `src/punie/client/ask_client.py` (lines 24-141)

```python
async def run_ask_client(server_url: str, prompt: str, workspace: Path) -> str:
    """Send prompt to server and return response."""
    async with punie_session(server_url, str(workspace)) as (websocket, session_id):
        # Send prompt request (UUID for request_id)
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "prompt",
            "params": {
                "session_id": session_id,
                "prompt": [{"type": "text", "text": prompt}],
            },
        }
        await websocket.send(json.dumps(request))

        # Listen for session_update notifications
        response_text = ""

        while True:
            # 5-minute timeout for long operations
            try:
                data = await asyncio.wait_for(websocket.recv(), timeout=300.0)
            except asyncio.TimeoutError:
                raise RuntimeError("No response from server after 5 minutes")
            except websockets.exceptions.ConnectionClosed as exc:
                raise ConnectionError(f"Server disconnected during prompt: {exc}")

            # Handle malformed JSON
            try:
                message = json.loads(data)
            except json.JSONDecodeError as exc:
                logger.warning(f"Invalid JSON from server: {exc}")
                continue

            # Handle session_update notifications (streaming response chunks)
            if message.get("method") == "session_update":
                update = message["params"]["update"]

                # Agent message content (text block)
                if update.get("sessionUpdate") == "agent_message_chunk":
                    content = update.get("content")
                    if content and content.get("type") == "text":
                        chunk = content["text"]
                        response_text += chunk

            # Handle final response (comes AFTER all notifications)
            elif message.get("id") == request_id:
                if "error" in message:
                    error = message["error"]
                    raise RuntimeError(f"Prompt failed: {error.get('message')}")
                break  # Exit loop

            # Ignore other notifications
            elif "method" in message:
                logger.debug(f"Ignoring notification: {message['method']}")
                continue

        return response_text
```

**Critical Patterns:**
1. **5-minute timeout** - Long operations need more time than send_request
2. **Check message.get("method") == "session_update"** - Identify notifications
3. **Extract update["sessionUpdate"]** - Type of update (agent_message_chunk, tool_call, etc.)
4. **Exit on message.get("id") == request_id** - Final response signals completion
5. **Accumulate chunks** - Streaming means multiple agent_message_chunk notifications

---

## 4. Tool Update Handling

### Pattern: Tool Call Updates

**Source:** `src/punie/acp/helpers.py` (lines 211-298)

```python
def start_tool_call(
    tool_call_id: str,
    title: str,
    *,
    kind: ToolKind | None = None,
    status: ToolCallStatus | None = None,
    content: Sequence[ToolCallContentVariant] | None = None,
    locations: Sequence[ToolCallLocation] | None = None,
    raw_input: Any | None = None,
    raw_output: Any | None = None,
) -> ToolCallStart:
    return ToolCallStart(
        session_update="tool_call",  # Update type
        tool_call_id=tool_call_id,
        title=title,
        kind=kind,
        status=status,
        content=list(content) if content is not None else None,
        locations=list(locations) if locations is not None else None,
        raw_input=raw_input,
        raw_output=raw_output,
    )

def update_tool_call(
    tool_call_id: str,
    *,
    title: str | None = None,
    kind: ToolKind | None = None,
    status: ToolCallStatus | None = None,
    content: Sequence[ToolCallContentVariant] | None = None,
    locations: Sequence[ToolCallLocation] | None = None,
    raw_input: Any | None = None,
    raw_output: Any | None = None,
) -> ToolCallProgress:
    return ToolCallProgress(
        session_update="tool_call_update",  # Update type
        tool_call_id=tool_call_id,
        title=title,
        kind=kind,
        status=status,
        content=list(content) if content is not None else None,
        locations=list(locations) if locations is not None else None,
        raw_input=raw_input,
        raw_output=raw_output,
    )
```

**Key Fields:**
- `session_update`: "tool_call" or "tool_call_update"
- `tool_call_id`: Unique identifier for this tool execution
- `title`: Human-readable description
- `kind`: ToolKind literal ("read", "edit", "execute", "search", etc.)
- `status`: ToolCallStatus literal ("pending", "in_progress", "completed", "failed")
- `content`: List of ContentBlock (text, code, diff, etc.)
- `locations`: List of {path, line} for affected files
- `raw_input`: Tool input arguments
- `raw_output`: Tool execution result

---

### Pattern: Update Type Discrimination

**Source:** `src/punie/client/ask_client.py` (lines 98-116)

```python
# Handle session_update notifications
if message.get("method") == "session_update":
    update = message["params"]["update"]

    # Check sessionUpdate field (camelCase!)
    update_type = update.get("sessionUpdate")

    if update_type == "agent_message_chunk":
        # Handle text streaming
        content = update.get("content")
        if content and content.get("type") == "text":
            chunk = content["text"]
            # Process chunk...

    elif update_type == "tool_call":
        # Tool execution started
        tool_call_id = update.get("tool_call_id")
        title = update.get("title")
        kind = update.get("kind")
        # Process tool start...

    elif update_type == "tool_call_update":
        # Tool execution progress
        tool_call_id = update.get("tool_call_id")
        status = update.get("status")
        # Process tool progress...
```

**Key Points:**
1. **Check sessionUpdate field** - This is camelCase (not session_update)
2. **Multiple update types** - agent_message_chunk, tool_call, tool_call_update, etc.
3. **Extract nested fields** - update.get("content"), update.get("tool_call_id")
4. **Type-specific handling** - Different logic for each update type

---

## 5. Error Handling Patterns

### Pattern: Timeout Protection

**Source:** `src/punie/client/connection.py` (lines 78-86)

```python
# Wait for response with timeout
while True:
    try:
        data = await asyncio.wait_for(websocket.recv(), timeout=30.0)
    except asyncio.TimeoutError:
        raise RuntimeError(f"Timeout waiting for response after 30s")
    except websockets.exceptions.ConnectionClosed as exc:
        raise ConnectionError(f"Server disconnected: {exc}")
```

**Key Points:**
- Use `asyncio.wait_for()` with timeout parameter
- 30 seconds for request/response
- 300 seconds (5 min) for streaming operations
- Raise RuntimeError on timeout (user-facing error)
- Raise ConnectionError on disconnect (recoverable)

---

### Pattern: Malformed JSON Handling

**Source:** `src/punie/client/connection.py` (lines 89-94)

```python
# Parse JSON with error handling
try:
    message = json.loads(data)
except json.JSONDecodeError as exc:
    logger.warning(f"Invalid JSON from server: {exc}")
    continue  # Skip and wait for next message
```

**Key Points:**
- Wrap `json.loads()` in try/except
- Log warning but don't crash
- Continue loop to wait for next message
- Malformed data is unexpected but shouldn't kill connection

---

## 6. Testing Patterns

### Pattern: Fake Callbacks

**Testing Pattern:**

```python
@pytest.fixture
def fake_callback():
    """Fake callback that records calls."""
    calls = []
    def callback(update_type: str, content: dict):
        calls.append((update_type, content))
    callback.calls = calls
    return callback

def test_streaming_calls_callback(fake_callback):
    """Test streaming invokes callback for each chunk."""
    # Setup: Mock websocket with notifications
    # Send: Prompt with fake_callback
    # Assert: fake_callback.calls contains expected updates
    assert len(fake_callback.calls) == 3
    assert fake_callback.calls[0][0] == "agent_message_chunk"
```

**Key Points:**
- Use simple functions with closure over `calls` list
- Attach `calls` attribute to callback function
- No mock framework (follows fakes-over-mocks standard)
- Easy to assert on call count and arguments

---

### Pattern: Integration Tests

**Source:** Phase 28 test patterns

```python
def test_full_lifecycle():
    """Test complete prompt → response flow."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            # Perform handshake
            # Send prompt
            # Collect chunks
            # Verify response
            pass
```

**Key Points:**
- Use `TestClient(app)` from Starlette
- Use `client.websocket_connect("/ws")` for WebSocket
- Context managers ensure cleanup
- Real server, real WebSocket (not mocked)

---

## 7. Type Definitions

### Pattern: Callback Types

```python
from typing import Callable, Any

# Update callback - receives full session_update notification
OnUpdateCallback = Callable[[dict[str, Any]], None]

# Chunk callback - receives update_type and content
OnChunkCallback = Callable[[str, dict[str, Any]], None]

# Tool call callback - receives tool_call_id and tool_data
OnToolCallCallback = Callable[[str, dict[str, Any]], None]
```

**Key Points:**
- Document expected signature in docstring
- Use `dict[str, Any]` for flexible JSON data
- No return value (None) - callbacks are side-effects only

---

## Summary of Key Patterns

**Connection:**
- Use `websockets.connect(url)` directly
- Two-step handshake: initialize → new_session
- UUID request IDs to prevent collision

**Streaming:**
- 5-minute timeout for long operations
- Check `message.get("method") == "session_update"`
- Extract `update["sessionUpdate"]` for update type
- Exit on `message.get("id") == request_id`

**Tool Updates:**
- `session_update="tool_call"` - Tool execution started
- `session_update="tool_call_update"` - Tool progress
- Extract tool_call_id, title, kind, status, locations

**Error Handling:**
- `asyncio.wait_for()` for timeout protection
- Try/except on `json.loads()` for malformed data
- Raise RuntimeError for timeouts (user error)
- Raise ConnectionError for disconnects (recoverable)

**Testing:**
- Fake callbacks (functions with closure)
- TestClient + websocket_connect for integration
- No mock framework (fakes-over-mocks standard)
