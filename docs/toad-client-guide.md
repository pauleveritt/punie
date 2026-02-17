# Toad Client Guide

WebSocket client for browser-based Toad frontend integration with Punie server.

## Quick Start

```python
from punie.client import create_toad_session, send_prompt_stream

# Create session
websocket, session_id = await create_toad_session(
    server_url="ws://localhost:8000/ws",
    cwd="/path/to/workspace"
)

# Define callback for streaming updates
def on_chunk(update_type, content):
    if update_type == "agent_message_chunk":
        text = content.get("content", {}).get("text", "")
        print(text, end="", flush=True)

# Send prompt with streaming
result = await send_prompt_stream(
    websocket,
    session_id,
    "What is dependency injection?",
    on_chunk
)

# Clean up
await websocket.close()
```

## Core Functions

### `create_toad_session(server_url, cwd)`

Creates a WebSocket connection and performs ACP handshake.

**Args:**
- `server_url` (str): WebSocket URL (e.g., `ws://localhost:8000/ws`)
- `cwd` (str): Current working directory for session

**Returns:**
- `tuple[ClientConnection, str]`: (websocket, session_id)

**Raises:**
- `websockets.exceptions.WebSocketException`: If connection fails
- `RuntimeError`: If handshake fails

**Example:**
```python
try:
    websocket, session_id = await create_toad_session(
        "ws://localhost:8000/ws",
        "/Users/me/my-project"
    )
except ConnectionError as e:
    print(f"Failed to connect: {e}")
```

**Note:** Caller is responsible for closing the websocket when done.

---

### `send_prompt_stream(websocket, session_id, prompt, on_chunk)`

Sends prompt and streams responses via callback.

**Args:**
- `websocket` (ClientConnection): Connected WebSocket from `create_toad_session`
- `session_id` (str): Session ID from `create_toad_session`
- `prompt` (str): User prompt text
- `on_chunk` (Callable): Callback invoked for each update

**Returns:**
- `dict[str, Any]`: Final response result

**Raises:**
- `RuntimeError`: If timeout (5 minutes) or execution fails
- `ConnectionError`: If WebSocket disconnects during streaming

**Callback Signature:**
```python
def on_chunk(update_type: str, content: dict[str, Any]) -> None:
    """Called for each session_update notification.

    Args:
        update_type: Type of update (see Update Types below)
        content: Full update dict with type-specific fields
    """
    pass
```

**Example:**
```python
def on_chunk(update_type, content):
    if update_type == "agent_message_chunk":
        # Streaming text from agent
        text = content.get("content", {}).get("text", "")
        print(text, end="")
    elif update_type == "tool_call":
        # Tool execution started
        print(f"\n[Tool: {content.get('title')}]")
    elif update_type == "tool_call_update":
        # Tool execution progress
        status = content.get("status")
        print(f"[Status: {status}]")

result = await send_prompt_stream(ws, sid, "Analyze this code", on_chunk)
```

---

### `handle_tool_update(update, on_tool_call)`

Parses tool execution updates and dispatches to callback.

**Args:**
- `update` (dict): session_update notification dict (from on_chunk)
- `on_tool_call` (Callable): Callback invoked for tool execution

**Callback Signature:**
```python
def on_tool_call(tool_call_id: str, tool_data: dict[str, Any]) -> None:
    """Called for tool_call and tool_call_update notifications.

    Args:
        tool_call_id: Unique identifier for this tool execution
        tool_data: Dict with title, kind, status, content, locations, etc.
    """
    pass
```

**Example:**
```python
def on_chunk(update_type, content):
    if update_type in ("tool_call", "tool_call_update"):
        await handle_tool_update(content, on_tool_call)

def on_tool_call(tool_call_id, tool_data):
    print(f"Tool {tool_call_id}:")
    print(f"  Title: {tool_data['title']}")
    print(f"  Kind: {tool_data['kind']}")
    print(f"  Status: {tool_data['status']}")

    for location in tool_data.get('locations', []):
        print(f"  File: {location['path']}")
```

**Tool Data Fields:**
- `title` (str): Human-readable tool description
- `kind` (str): Tool type ("read", "edit", "execute", "search", etc.)
- `status` (str): Execution status ("pending", "in_progress", "completed", "failed")
- `content` (list): List of ContentBlock (text, code, diff, etc.)
- `locations` (list): List of {path, line} for affected files
- `raw_input` (Any): Tool input arguments
- `raw_output` (Any): Tool execution result

---

### `run_toad_client(server_url, cwd, on_update)`

Maintains persistent WebSocket connection with event loop.

**Args:**
- `server_url` (str): WebSocket URL
- `cwd` (str): Current working directory
- `on_update` (Callable): Callback for all session_update notifications

**Raises:**
- `websockets.exceptions.WebSocketException`: If connection fails
- `RuntimeError`: If handshake fails

**Callback Signature:**
```python
def on_update(update: dict[str, Any]) -> None:
    """Called for each session_update notification.

    Args:
        update: Full update dict with sessionUpdate type and fields
    """
    pass
```

**Example:**
```python
def on_update(update):
    update_type = update.get("sessionUpdate")

    if update_type == "agent_message_chunk":
        content = update.get("content")
        if content and content.get("type") == "text":
            print(content["text"], end="")

    elif update_type == "tool_call":
        print(f"\n[Tool: {update.get('title')}]")

await run_toad_client(
    "ws://localhost:8000/ws",
    "/workspace",
    on_update
)
```

**Note:** This function does not return until the connection is closed. Use `asyncio.create_task()` if you need background execution.

---

## Update Types

The `sessionUpdate` field can be one of:

### `agent_message_chunk`

Streaming text from agent response.

**Fields:**
- `content` (dict): ContentBlock with type="text" and text field

**Example:**
```python
{
    "sessionUpdate": "agent_message_chunk",
    "content": {"type": "text", "text": "Hello world"}
}
```

### `tool_call`

Tool execution started (ToolCallStart).

**Fields:**
- `tool_call_id` (str): Unique tool execution ID
- `title` (str): Human-readable description
- `kind` (str): Tool type (read/edit/execute/search/etc.)
- `status` (str): pending/in_progress/completed/failed
- `content` (list): List of ContentBlock
- `locations` (list): List of {path, line}

**Example:**
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

### `tool_call_update`

Tool execution progress (ToolCallProgress).

**Fields:**
- `tool_call_id` (str): Tool execution ID (matches tool_call)
- `status` (str): Updated status
- Other fields as needed (title, content, etc.)

**Example:**
```python
{
    "sessionUpdate": "tool_call_update",
    "tool_call_id": "tool-123",
    "status": "completed"
}
```

### Other Update Types

- `agent_thought_chunk`: Internal agent reasoning (streaming)
- `plan`: Agent plan updates
- `available_commands_update`: Available slash commands changed
- `current_mode_update`: Mode changed (e.g., code → chat)
- `user_message_chunk`: User message echo (streaming)

See `src/punie/acp/schema.py` for complete type definitions.

---

## Connection Management

### Creating Sessions

```python
# Option 1: Manual session management
websocket, session_id = await create_toad_session(server_url, cwd)
try:
    # Use websocket...
finally:
    await websocket.close()

# Option 2: Context manager (from connection module)
from punie.client import punie_session

async with punie_session(server_url, cwd) as (websocket, session_id):
    # Use websocket...
    # Automatically closed on exit
```

### Reconnection Strategies

```python
async def connect_with_retry(server_url, cwd, max_retries=3):
    """Connect with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await create_toad_session(server_url, cwd)
        except (ConnectionError, websockets.exceptions.WebSocketException) as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Connection failed, retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
```

### Cleanup on Disconnect

```python
try:
    websocket, session_id = await create_toad_session(server_url, cwd)
    result = await send_prompt_stream(ws, sid, prompt, on_chunk)
except ConnectionError as e:
    print(f"Connection lost: {e}")
    # Handle reconnection or notify user
finally:
    if websocket:
        await websocket.close()
```

---

## Error Handling

### Timeout Scenarios

```python
try:
    result = await send_prompt_stream(ws, sid, prompt, on_chunk)
except RuntimeError as e:
    if "No response from server" in str(e):
        print("Operation timed out after 5 minutes")
        # Reconnect or notify user
    else:
        raise
```

### Connection Failures

```python
try:
    websocket, session_id = await create_toad_session(server_url, cwd)
except websockets.exceptions.WebSocketException as e:
    print(f"Failed to connect to {server_url}: {e}")
    # Try different URL or notify user
except RuntimeError as e:
    print(f"Handshake failed: {e}")
    # Server may be incompatible version
```

### Malformed Responses

The client automatically handles malformed JSON by logging warnings and skipping invalid messages. Your callbacks will not be invoked for malformed data.

### Callback Errors

Exceptions in callbacks are caught and logged, but do not crash the streaming loop:

```python
def on_chunk(update_type, content):
    try:
        # Your processing logic
        process_update(update_type, content)
    except Exception as e:
        # Callback errors are logged but don't crash streaming
        logger.error(f"Error processing update: {e}")
```

---

## Integration with Toad

### Expected Callback Signatures

**For `send_prompt_stream`:**
```typescript
// TypeScript signature
type OnChunkCallback = (updateType: string, content: any) => void;
```

**For `handle_tool_update`:**
```typescript
// TypeScript signature
type OnToolCallCallback = (toolCallId: string, toolData: any) => void;
```

### Browser WebSocket Wrapper

Toad frontend should wrap the Python client patterns in JavaScript:

```javascript
// Example browser integration
class ToadClient {
    constructor(serverUrl, cwd) {
        this.ws = new WebSocket(serverUrl);
        this.sessionId = null;
    }

    async connect() {
        // Perform ACP handshake
        await this.initialize();
        this.sessionId = await this.createSession();
    }

    async sendPrompt(prompt, onChunk) {
        const requestId = crypto.randomUUID();
        this.ws.send(JSON.stringify({
            jsonrpc: "2.0",
            id: requestId,
            method: "prompt",
            params: {
                session_id: this.sessionId,
                prompt: [{type: "text", text: prompt}]
            }
        }));

        // Listen for session_update notifications
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.method === "session_update") {
                const update = message.params.update;
                onChunk(update.sessionUpdate, update);
            } else if (message.id === requestId) {
                // Final response
                return message.result;
            }
        };
    }
}
```

### Session Lifecycle

1. **Connect**: Create WebSocket connection
2. **Initialize**: Send initialize request with protocol version
3. **Create Session**: Send new_session request with cwd
4. **Send Prompts**: Use session_id for all prompt requests
5. **Stream Updates**: Process session_update notifications
6. **Disconnect**: Close WebSocket when done

**Lifecycle Diagram:**
```
[Browser] → connect(ws://localhost:8000/ws)
[Browser] → initialize(protocol_version=1)
[Server] → initialize response
[Browser] → new_session(cwd="/workspace")
[Server] → new_session response (sessionId)
[Browser] → prompt(session_id, "query")
[Server] → session_update (streaming chunks)
[Server] → session_update (tool calls)
[Server] → prompt response (final result)
[Browser] → close()
```

---

## Performance Tips

### Connection Pooling

For multiple concurrent requests, reuse the same WebSocket connection:

```python
# Good: Reuse connection for multiple prompts
websocket, session_id = await create_toad_session(url, cwd)
for prompt in prompts:
    result = await send_prompt_stream(ws, sid, prompt, on_chunk)
await websocket.close()

# Bad: Create new connection for each prompt
for prompt in prompts:
    ws, sid = await create_toad_session(url, cwd)
    result = await send_prompt_stream(ws, sid, prompt, on_chunk)
    await ws.close()
```

### Backpressure Handling

If your UI cannot keep up with streaming updates, consider buffering:

```python
from collections import deque

class BufferedCallback:
    def __init__(self, max_buffer=100):
        self.buffer = deque(maxlen=max_buffer)

    def __call__(self, update_type, content):
        self.buffer.append((update_type, content))

    def drain(self):
        """Process buffered updates in UI thread."""
        while self.buffer:
            update_type, content = self.buffer.popleft()
            # Update UI...
```

### Timeout Tuning

Default timeout is 5 minutes (300 seconds). Adjust for your use case:

- Short queries: 30-60 seconds
- Complex analysis: 5-10 minutes
- Long-running operations: 15+ minutes

**Note:** Timeout is not configurable in current API. Consider using `asyncio.wait_for()` wrapper if needed.

---

## Troubleshooting

### "No response from server after 5 minutes"

**Cause:** Operation timed out (model generation taking too long)

**Solutions:**
- Check server logs for errors
- Try simpler prompt
- Increase timeout (requires code modification)

### "Server disconnected during prompt"

**Cause:** WebSocket connection closed unexpectedly

**Solutions:**
- Check server is running (`punie serve`)
- Verify WebSocket URL is correct
- Check network connectivity
- Review server logs for crashes

### Callbacks not being invoked

**Cause:** Update type mismatch or callback error

**Solutions:**
- Log all `update_type` values to see what's being received
- Check for exceptions in callback (logged but not raised)
- Verify `sessionUpdate` field extraction (camelCase!)

### Handshake fails

**Cause:** Protocol version mismatch or server error

**Solutions:**
- Check server is Phase 28+ (supports ACP protocol)
- Verify `protocol_version: 1` in initialize request
- Review server logs for handshake errors

---

## Next Steps

- **Phase 30**: Thin ACP Router (multi-server routing)
- **Phase 31**: Multi-Project Support (workspace management)
- **Toad Integration**: Browser UI consuming this client API

## Related Documentation

- [Client Setup Guide](client-setup-guide.md) - Overview of all client types
- [WebSocket API](websocket-api.md) - Complete ACP protocol reference
- [ACP Schema](../src/punie/acp/schema.py) - Protocol type definitions
