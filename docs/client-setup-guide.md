# Punie Client Setup Guide

Quick guide to connect to the Punie server from various clients (browsers, Python scripts, command-line tools).

---

## Server Architecture

The Punie server runs on **port 8000** with dual protocol support:

- **HTTP Endpoints** (for browsers, REST clients):
  - `GET http://localhost:8000/health` - Health check
  - `POST http://localhost:8000/echo` - Echo test

- **WebSocket Endpoint** (for agents, real-time clients):
  - `ws://localhost:8000/ws` - ACP protocol over WebSocket

---

## Quick Start

### 1. Start the Servers

```bash
# Terminal 1: Start MLX model server
just mlx-start

# Terminal 2: Start Punie HTTP/WebSocket server
just server-start
```

Or use the combined command:

```bash
# Starts both MLX and Punie in one terminal
just dev-servers
```

### 2. Test the Connection

```bash
# Test HTTP endpoint
curl http://localhost:8000/health

# Test with punie ask (connects to MLX server at localhost:5001)
# Uses local:http://localhost:5001/v1 by default
uv run punie ask "What is dependency injection?"
```

---

## Client Examples

### Toad Frontend Client

For browser-based Toad frontend integration:

```python
from punie.client import run_toad_client, send_prompt_stream, create_toad_session

# Simple streaming example
async def on_chunk(update_type, content):
    if update_type == "agent_message_chunk":
        text = content.get("content", {}).get("text", "")
        print(text, end="", flush=True)

websocket, session_id = await create_toad_session(
    server_url="ws://localhost:8000/ws",
    cwd="/workspace"
)
result = await send_prompt_stream(ws, sid, "Your question", on_chunk)
await websocket.close()

# Persistent connection example
async def on_update(update):
    update_type = update.get("sessionUpdate")
    print(f"Update: {update_type}")

await run_toad_client(
    "ws://localhost:8000/ws",
    "/workspace",
    on_update
)
```

**Features:**
- Streaming responses via callbacks
- Tool execution visibility
- Session management (create, reconnect, cleanup)
- Browser-compatible API

See [Toad Client Guide](toad-client-guide.md) for complete documentation.

### Toad Integration Example

For Toad developers implementing WebSocket transport:

```python
# See examples/toad_websocket_agent.py for reference implementation
from examples.toad_websocket_agent import ToadWebSocketAgent

agent = ToadWebSocketAgent("ws://localhost:8000/ws", "/workspace")
await agent.connect()
await agent.send_prompt("Your question")
await agent.disconnect()
```

**Integration Guide:** See [docs/toad-integration-guide.md](toad-integration-guide.md) for step-by-step instructions on adding WebSocket transport to Toad's ACP agent.

### Python Client (WebSocket)

```python
#!/usr/bin/env python3
"""Simple Python client for Punie WebSocket server."""

import asyncio
import json
from starlette.testclient import TestClient
from punie.http.app import create_app
from punie.agent.adapter import PunieAgent

# For testing with TestClient
agent = PunieAgent(model="test")
app = create_app(agent)

with TestClient(app) as client:
    with client.websocket_connect("/ws") as ws:
        # Initialize connection
        ws.send_json({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocol_version": 1},
        })
        init_response = ws.receive_json()
        print("✓ Initialized:", init_response["result"]["agentInfo"]["name"])

        # Create session
        ws.send_json({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "new_session",
            "params": {"cwd": "/tmp", "mcp_servers": []},
        })
        session_response = ws.receive_json()
        session_id = session_response["result"]["sessionId"]
        resume_token = session_response["result"]["_meta"]["resume_token"]
        print(f"✓ Session created: {session_id}")
        print(f"✓ Resume token: {resume_token[:20]}...")

        # Send prompt
        ws.send_json({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "prompt",
            "params": {
                "session_id": session_id,
                "prompt": [{"type": "text", "text": "What is dependency injection?"}],
            },
        })

        # Receive responses (may be multiple for streaming)
        while True:
            msg = ws.receive_json()
            if "method" == msg.get("method") and msg.get("method") == "session_update":
                update = msg["params"]["update"]
                if update.get("type") == "agentMessage":
                    content = update.get("content", [])
                    for block in content:
                        if block.get("type") == "text":
                            print("\nAgent:", block["text"])
            elif "result" in msg:
                print("\n✓ Prompt completed")
                break
```

### Browser Client (JavaScript)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Punie WebSocket Client</title>
    <style>
        body { font-family: monospace; padding: 20px; }
        #output { border: 1px solid #ccc; padding: 10px; height: 400px; overflow-y: scroll; }
        button { margin: 5px; padding: 10px; }
    </style>
</head>
<body>
    <h1>Punie WebSocket Client</h1>
    <button onclick="connect()">Connect</button>
    <button onclick="initialize()">Initialize</button>
    <button onclick="createSession()">Create Session</button>
    <button onclick="sendPrompt()">Send Prompt</button>
    <button onclick="disconnect()">Disconnect</button>
    <div id="output"></div>

    <script>
        let ws = null;
        let requestId = 1;
        let sessionId = null;
        let resumeToken = null;

        function log(msg) {
            const output = document.getElementById('output');
            output.innerHTML += msg + '<br>';
            output.scrollTop = output.scrollHeight;
        }

        function connect() {
            ws = new WebSocket('ws://localhost:8000/ws');
            ws.onopen = () => log('✓ Connected to Punie server');
            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                log('← ' + JSON.stringify(msg, null, 2));

                // Handle session creation
                if (msg.id === 2 && msg.result) {
                    sessionId = msg.result.sessionId;
                    resumeToken = msg.result._meta.resume_token;
                    log(`✓ Session: ${sessionId}`);
                }
            };
            ws.onerror = (error) => log('✗ Error: ' + error);
            ws.onclose = () => log('✗ Disconnected');
        }

        function initialize() {
            const msg = {
                jsonrpc: "2.0",
                id: requestId++,
                method: "initialize",
                params: { protocol_version: 1 }
            };
            ws.send(JSON.stringify(msg));
            log('→ ' + JSON.stringify(msg));
        }

        function createSession() {
            const msg = {
                jsonrpc: "2.0",
                id: requestId++,
                method: "new_session",
                params: { cwd: "/tmp", mcp_servers: [] }
            };
            ws.send(JSON.stringify(msg));
            log('→ ' + JSON.stringify(msg));
        }

        function sendPrompt() {
            if (!sessionId) {
                log('✗ Create session first!');
                return;
            }
            const msg = {
                jsonrpc: "2.0",
                id: requestId++,
                method: "prompt",
                params: {
                    session_id: sessionId,
                    prompt: [{ type: "text", text: "What is dependency injection?" }]
                }
            };
            ws.send(JSON.stringify(msg));
            log('→ ' + JSON.stringify(msg));
        }

        function disconnect() {
            if (ws) {
                ws.close();
                ws = null;
            }
        }
    </script>
</body>
</html>
```

Save as `client.html` and open in browser, then:
1. Click "Connect"
2. Click "Initialize"
3. Click "Create Session"
4. Click "Send Prompt"

### curl (HTTP)

```bash
# Health check
curl http://localhost:8000/health

# Echo test
curl -X POST http://localhost:8000/echo \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Punie"}'
```

### Python Requests (HTTP)

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())  # {"status": "ok"}

# Echo test
response = requests.post(
    "http://localhost:8000/echo",
    json={"message": "Hello Punie"}
)
print(response.json())  # {"echo": {"message": "Hello Punie"}}
```

---

## Reconnection Support

The Punie server supports automatic session recovery after disconnections:

```javascript
// Save these when creating a session
let sessionId = response.result.sessionId;
let resumeToken = response.result._meta.resume_token;

// After reconnecting (within 5 minutes)
ws.send(JSON.stringify({
    jsonrpc: "2.0",
    id: 1,
    method: "resume_session",
    params: {
        cwd: "/tmp",
        session_id: sessionId,
        resume_token: resumeToken
    }
}));
```

**Features:**
- **5-minute grace period** - Sessions persist for 5 minutes after disconnect
- **Secure tokens** - 32-byte tokens prevent unauthorized access
- **Full recovery** - Complete conversation history preserved

---

## Testing

### Manual Testing

1. **Start servers:**
   ```bash
   just dev-servers
   ```

2. **Open browser to:**
   - `http://localhost:8000/health` - Should return `{"status": "ok"}`

3. **Test WebSocket:**
   ```bash
   # Run Python client example above
   python client.py
   ```

### Automated Testing

```bash
# Run WebSocket integration tests
uv run pytest tests/test_websocket_integration.py -v

# Run reconnection tests
uv run pytest tests/test_websocket_reconnection.py -v
```

---

## Troubleshooting

### Connection Refused

**Problem:** `curl: (7) Failed to connect to localhost port 8000`

**Solution:**
```bash
# Check if server is running
lsof -ti:8000 || echo "Server not running"

# Start server
just server-start
```

### MLX Model Not Found

**Problem:** `❌ Production model not found at fused_model_qwen3_phase27_cleaned_5bit`

**Solution:**
```bash
# Check available models
ls -d fused_model*

# Update justfile if needed
# Or use test model:
uv run punie ask "test question" --model test
```

### WebSocket Connection Failed

**Problem:** Browser console shows `WebSocket connection to 'ws://localhost:8000/ws' failed`

**Solution:**
1. Verify server is running: `lsof -ti:8000`
2. Check browser allows WebSocket to localhost
3. Try the test client script to isolate the issue

### punie ask Connection Error

**Problem:** `Error: Connection error.`

**Solution:**
```bash
# Default uses production model - start MLX server first
just mlx-start
punie ask "your question"

# Or use test model (no server needed)
punie ask "your question" --model test
```

---

## Protocol Reference

### ACP over WebSocket

Punie uses the Agent Communication Protocol (ACP) over WebSocket with JSON-RPC 2.0 format.

**Request Format:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "method_name",
  "params": { /* method parameters */ }
}
```

**Response Format:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { /* result data */ }
}
```

**Notification Format (server → client):**
```json
{
  "jsonrpc": "2.0",
  "method": "session_update",
  "params": { /* update data */ }
}
```

### Available Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `initialize` | Initialize connection | `protocol_version` |
| `new_session` | Create new session | `cwd`, `mcp_servers` |
| `resume_session` | Resume after disconnect | `session_id`, `resume_token` |
| `prompt` | Send prompt to agent | `session_id`, `prompt` |
| `cancel` | Cancel running prompt | `session_id` |

---

## Production Deployment

### Security Considerations

1. **Use TLS/WSS** - Always use `wss://` (secure WebSocket) in production
2. **Authentication** - Add auth middleware before exposing publicly
3. **Rate limiting** - Limit requests per client
4. **CORS** - Configure CORS for browser clients

### Example nginx Configuration

```nginx
server {
    listen 443 ssl;
    server_name punie.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # HTTP endpoints
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket endpoint
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 300s;  # 5-minute timeout
    }
}
```

---

## Next Steps

- **Explore examples:** Check `examples/13_serve_dual.py`
- **Read API docs:** See `docs/phase28-server-architecture.md`
- **Build a client:** Use templates above as starting point
- **Deploy to production:** Follow security guidelines above
