# WebSocket API Documentation

Phase 28 adds WebSocket support to Punie, enabling multiple clients to connect simultaneously over persistent connections.

## Overview

The WebSocket endpoint (`/ws`) provides full ACP (Agent Communication Protocol) support over WebSocket, allowing:

- **Multiple simultaneous clients** (Toad frontend, multiple IDE instances, browser tools)
- **Independent sessions per client** with automatic routing
- **Real-time bidirectional communication** (requests, responses, notifications)
- **Persistent connections** for multi-turn conversations
- **Automatic cleanup** on disconnect

## Endpoint

```
ws://localhost:8000/ws
```

Default port is 8000 (configurable via `--port` flag).

## Message Format

All messages use JSON-RPC 2.0 over WebSocket text frames.

### Request (Client → Server)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "method_name",
  "params": {
    // method parameters
  }
}
```

### Response (Server → Client)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    // method result
  }
}
```

### Error Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": "error details"
  }
}
```

### Notification (Server → Client, no response expected)

```json
{
  "jsonrpc": "2.0",
  "method": "session_update",
  "params": {
    "session_id": "punie-session-0",
    "update": {
      "type": "agent_message_chunk",
      "chunk": "Response text..."
    }
  }
}
```

## Connection Lifecycle

1. **Connect** - Client opens WebSocket connection to `/ws`
2. **Initialize** - Client sends `initialize` request
3. **Create Session** - Client sends `new_session` request
4. **Send Prompts** - Client sends `prompt` requests, receives `session_update` notifications
5. **Disconnect** - Connection closes, server cleans up all client sessions

## Available Methods

### initialize

Initialize the ACP connection.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocol_version": 1,
    "client_capabilities": null,
    "client_info": null
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocol_version": 1,
    "agent_capabilities": {},
    "agent_info": {
      "name": "punie-agent",
      "title": "Punie AI Coding Agent",
      "version": "0.1.0"
    }
  }
}
```

### new_session

Create a new session.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "new_session",
  "params": {
    "cwd": "/path/to/workspace",
    "mcp_servers": []
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "session_id": "punie-session-0"
  }
}
```

### prompt

Send a prompt to the agent.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "prompt",
  "params": {
    "session_id": "punie-session-0",
    "prompt": [
      {
        "type": "text",
        "text": "What is dependency injection?"
      }
    ]
  }
}
```

**Notifications (streaming):**
```json
{
  "jsonrpc": "2.0",
  "method": "session_update",
  "params": {
    "session_id": "punie-session-0",
    "update": {
      "type": "agent_message_chunk",
      "chunk": "Dependency injection is..."
    }
  }
}
```

**Final Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "stop_reason": "end_turn"
  }
}
```

### Other Methods

All ACP protocol methods are supported:
- `load_session`
- `list_sessions`
- `set_session_mode`
- `set_session_model`
- `fork_session`
- `resume_session`
- `authenticate`
- `cancel`

See [ACP Protocol Specification](https://github.com/jetbrains/agent-protocol) for details.

## Example Client (Python)

```python
import asyncio
import json
import websockets

async def main():
    uri = "ws://localhost:8000/ws"

    async with websockets.connect(uri) as websocket:
        # Initialize
        await websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocol_version": 1}
        }))
        response = json.loads(await websocket.recv())
        print(f"Initialized: {response}")

        # Create session
        await websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "new_session",
            "params": {"cwd": "/tmp", "mcp_servers": []}
        }))
        response = json.loads(await websocket.recv())
        session_id = response["result"]["session_id"]
        print(f"Session created: {session_id}")

        # Send prompt
        await websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "prompt",
            "params": {
                "session_id": session_id,
                "prompt": [{"type": "text", "text": "Hello!"}]
            }
        }))

        # Receive updates and response
        while True:
            msg = json.loads(await websocket.recv())
            if "method" in msg and msg["method"] == "session_update":
                # Notification
                print(f"Update: {msg['params']['update']}")
            elif "result" in msg and msg.get("id") == 3:
                # Final response
                print(f"Done: {msg['result']}")
                break

asyncio.run(main())
```

## Example Client (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

let requestId = 0;

function sendRequest(method, params) {
  const id = ++requestId;
  ws.send(JSON.stringify({
    jsonrpc: '2.0',
    id,
    method,
    params
  }));
  return id;
}

ws.onopen = () => {
  // Initialize
  sendRequest('initialize', { protocol_version: 1 });
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  if (msg.method === 'session_update') {
    // Notification from server
    console.log('Update:', msg.params);
  } else if (msg.result) {
    // Response to request
    console.log('Result:', msg.result);

    if (msg.id === 1) {
      // After initialize, create session
      sendRequest('new_session', { cwd: '/tmp', mcp_servers: [] });
    } else if (msg.id === 2) {
      // After new_session, send prompt
      const sessionId = msg.result.session_id;
      sendRequest('prompt', {
        session_id: sessionId,
        prompt: [{ type: 'text', text: 'Hello!' }]
      });
    }
  }
};
```

## Error Handling

### Parse Error (-32700)

Invalid JSON received.

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32700,
    "message": "Parse error"
  },
  "id": null
}
```

### Internal Error (-32603)

Method execution failed.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": "Unknown method: foo"
  }
}
```

## Multi-Client Behavior

### Independent Sessions

Each WebSocket client maintains independent sessions. Sessions are automatically tracked and routed to the owning client.

```python
# Client 1
session1 = create_session()  # → "punie-session-0"

# Client 2
session2 = create_session()  # → "punie-session-1"

# Prompts route to correct client
prompt(session1, "Hello")  # Updates go to Client 1
prompt(session2, "Hi")     # Updates go to Client 2
```

### Cleanup on Disconnect

When a client disconnects, all its sessions are automatically cleaned up:

1. Find all sessions owned by disconnecting client
2. Remove sessions from agent state
3. Remove client from connection registry
4. Close WebSocket connection

No manual cleanup required!

## Testing

Run the server:

```bash
uv run punie serve --port 8000
```

Test with `websocat`:

```bash
# Install websocat
brew install websocat

# Connect and send initialize
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocol_version":1}}' | websocat ws://localhost:8000/ws
```

Test with Python test client:

```bash
uv run python scripts/test_websocket_client.py ws://localhost:8000/ws
```

## Integration with Toad Frontend

Phase 29 will integrate Toad frontend with this WebSocket API:

1. Toad connects to `ws://localhost:8000/ws`
2. Initializes ACP protocol
3. Creates session for user workspace
4. Sends user prompts via `prompt` method
5. Displays streaming responses from `session_update` notifications
6. Handles tool calls and permission requests

See Phase 29 documentation for details.

## Security Notes

**Current limitations (development mode):**

- ❌ No TLS/SSL (plaintext WebSocket)
- ❌ No authentication
- ❌ No authorization
- ❌ No rate limiting
- ❌ Localhost only (127.0.0.1)

**Production considerations:**

For production deployment, add:
- ✅ TLS (wss:// instead of ws://)
- ✅ Authentication (API keys, JWT tokens)
- ✅ Authorization (session access control)
- ✅ Rate limiting (requests per minute)
- ✅ CORS configuration
- ✅ Load balancing (multiple agent instances)

These will be addressed in future phases.
