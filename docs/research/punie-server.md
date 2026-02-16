# Punie server architecture sketch (hybrid with subinterpreters)

## Goal

Run a single Punie server per machine that can host multiple project sessions, while still keeping per-project isolation
and lifecycle control. Use Python 3.14 subinterpreters to make per-project workers cheap, managed, and independent.

## Summary

- One Punie server process per machine.
- Each project session runs in its own subinterpreter ("project worker").
- The main interpreter is a thin manager: routing, auth, scheduling, and persistence.
- ACP clients (PyCharm/Toad or a tiny ACP shim) connect by WebSocket.
- Tool execution policy is explicit: frontend tools vs backend tools.

## Components

### 1) Manager (main interpreter)

- Accepts WS connections and authenticates clients.
- Owns session registry: session id, project root, client identity, capabilities.
- Routes JSON-RPC to the right project worker.
- Enforces allowlists and validates paths per session.
- Handles persistence (sessions, metadata, transcripts, indexes).

### 2) Project worker (subinterpreter)

- One per project root (or per session, if desired).
- Runs the agent loop and model orchestration.
- Owns caches scoped to project root (embeddings, context summaries, prompt history).
- Optionally runs tools if backend tools are enabled.

### 3) Model backends

- mlx-lm server (or other LLM servers) per machine or per worker.
- Worker selects backend based on session config and availability.

### 4) Client transport

- WebSocket JSON-RPC using ACP schema.
- Can be used directly by Toad/PyCharm or via a shim.

## Toad WebSocketAgent sketch (ACP over WS)

### Goal

Allow Toad to speak ACP over a WebSocket transport without changing its ACP logic. This should be reusable by a thin
PyCharm executable so both clients share the same ACP-over-WS behavior.

### Placement

- New module: `src/toad/acp/ws_agent.py`
- New agent data fields (in `toad.agent_schema` and agent data files):
    - `transport`: `"subprocess"` (default) or `"websocket"`
    - `ws_url`: `ws://localhost:PORT/acp` (or `wss://`)
    - `headers`: optional map for auth
    - `auth`: optional token or named auth method
- Launcher: choose agent implementation based on `transport`.

### Reuse from existing ACP agent

Reuse the ACP code paths from `src/toad/acp/agent.py`:

- `jsonrpc.Server()` with `@jsonrpc.expose(...)` handlers
- `API.request(self.send)` for outbound calls
- `acp_initialize`, `acp_new_session`, `acp_load_session`, `acp_session_prompt`

### Transport responsibilities

- Connect to `ws_url` with optional headers/auth.
- Read JSON-RPC frames and dispatch to `self.server.call(...)`.
- Send JSON-RPC responses back over the socket.
- Provide `send(request)` to serialize JSON-RPC requests to WS.
- Handle reconnect/backoff and surface failures via `AgentFail`.

### Minimal class shape (pseudocode)

```python
class WebSocketAgent(AgentBase):
    def __init__(...):
        self.server = jsonrpc.Server()
        self.server.expose_instance(self)
        self.ws = None

    async def start(self, message_target=None):
        self._message_target = message_target
        self.ws = await connect(self.ws_url, headers=self.headers)
        self._task = asyncio.create_task(self._ws_loop())
        await self.acp_initialize()
        await self.acp_new_session()

    async def _ws_loop(self):
        async for message in self.ws:
            data = json.loads(message)
            if is_response(data):
                API.process_response(data)
                continue
            result = await self.server.call(data)
            if result is not None:
                await self.ws.send(json.dumps(result))

    def send(self, request):
        self.ws.send(request.body_json)
```

### Shared with PyCharm thin executable

Two options for maximum reuse:

1) Shared Python package: move `WebSocketAgent` and ACP transport logic into a small `punie-acp-client` package consumed
   by Toad and the PyCharm shim.
2) Shared shim executable: a single `punie-acp` binary that Toad and PyCharm both spawn; it connects to the Punie server
   by WS and implements ACP over stdio for compatibility.

Recommendation: prefer the shared shim executable as the default. It keeps Toad/PyCharm thin and identical, centralizes
auth/reconnect/backoff in one place, and makes transport evolution independent of UI releases.

### Shim responsibilities (punie-acp)

- Connect to Punie WS endpoint, with auth headers or token.
- Translate ACP JSON-RPC between stdio and WS (pass-through with id preservation).
- Reconnect with backoff and emit structured failure messages on exhaustion.
- Optional health ping and connection diagnostics.
- Minimal logging for troubleshooting (configurable).

### Shim configuration sketch

CLI flags:

- `--ws-url`: WebSocket endpoint (default `ws://localhost:8765/acp`)
- `--token`: auth token or API key
- `--project-root`: absolute project root for session binding
- `--client-id`: optional stable id for reconnects
- `--log-level`: `error|warn|info|debug`
- `--reconnect`: enable/disable reconnect (default on)
- `--reconnect-max`: max attempts or time budget
- `--health-interval`: ping interval (seconds)

Env vars (optional):

- `PUNIE_WS_URL`
- `PUNIE_TOKEN`
- `PUNIE_PROJECT_ROOT`
- `PUNIE_CLIENT_ID`
- `PUNIE_LOG_LEVEL`

### Example usage

```bash
punie-acp \\
  --ws-url ws://localhost:8765/acp \\
  --token $PUNIE_TOKEN \\
  --project-root /path/to/project \\
  --client-id pycharm-123 \\
  --log-level info
```

### Sample config file (TOML)

```toml
ws_url = "ws://localhost:8765/acp"
token = "env:PUNIE_TOKEN"
project_root = "/path/to/project"
client_id = "toad-456"
log_level = "info"
reconnect = true
reconnect_max = 10
health_interval = 30
```

### Launch notes (Toad/PyCharm)

- Toad and PyCharm launch `punie-acp` as the ACP agent command.
- Each client passes `--project-root` and a stable `--client-id`.
- Auth tokens can be passed via `--token` or env vars.
- The rest of the ACP flow is unchanged (JSON-RPC over stdio).

### Flow with Punie server

1) Client connects to Punie WS endpoint.
2) Client sends `initialize` and `session/new`.
3) Punie server replies with capabilities and session id.
4) Client streams `session/prompt` and listens for `session/update` and tool calls.
5) Tool calls are routed according to frontend/back-end tool mode.

## Session model

Session key fields:

- session_id (server-generated)
- project_root (absolute path)
- client_id (per connection)
- capabilities (client tool support: fs/terminal)
- transport (ws/subprocess)
- auth (token or derived identity)
- worker_id (subinterpreter handle)

Rules:

- A session is always bound to exactly one project_root.
- The manager guarantees that all file and tool paths remain under project_root.
- Multiple sessions can share a worker if they share project_root.

## Routing model

- ACP requests from clients enter the manager.
- Manager selects a worker based on session_id and forwards the JSON-RPC call.
- Worker processes the call, emits ACP updates, and streams them back through manager.
- Manager handles request/response correlation (keeps JSON-RPC ids intact).

## Subinterpreter plan (Python 3.14)

- Manager uses the subinterpreter API to create a worker per project.
- Communication channel: in-memory queue per worker (manager -> worker, worker -> manager).
- Worker runs an event loop to handle RPC messages.
- Manager can stop/restart workers for resource management.

Process sketch:

1) WS connection -> authenticate -> create session
2) Manager selects or creates worker for project_root
3) Manager forwards ACP initialize/session/new to worker
4) Worker owns agent state and emits updates

## Tool execution modes

### A) Frontend tools (default)

- Manager advertises fs/terminal support if client does.
- Worker requests permission and tool calls via ACP to client.
- Client executes tools and reports back via ACP updates.

### B) Backend tools

- Manager does not advertise fs/terminal.
- Worker runs tool calls locally, with allowlist enforcement.
- Tool execution is logged and permission gated by policy.

## Security and isolation

- Per-session path allowlist rooted at project_root.
- Explicit read/write limits in tool policy.
- Rate limits for tool calls and prompt size.
- Separate per-project logs and data directories.

## Failure and recovery

- Worker crash: manager marks sessions degraded, can respawn worker.
- Client disconnect: session can be persisted for later reconnect.
- Backend unavailable: worker reports ACP update with failure detail.

## Open questions

- Should workers be per project or per session?
- How to share model caches across workers safely?
- What policy for upgrading worker code without dropping sessions?
- How to expose project discovery to clients (server-side registry vs explicit path)?

## Next steps

- Decide the default tool execution mode (frontend vs backend).
- Define ACP-to-worker message envelope and queue format.
- Prototype a minimal worker that can run initialize/session/new/prompt.
