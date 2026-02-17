# Phase 29: Toad Frontend WebSocket Client - Implementation Plan

## Context

**Why:** Phase 28 separated Punie into server-only mode (HTTP/WebSocket) with thin clients. Phase 29 builds a Toad-compatible WebSocket client in the Punie repo to enable browser-based frontend integration.

**Problem Solved:** Currently, Toad (browser UI) has no way to connect to Punie server. This phase adds the missing client infrastructure so Toad can:
- Connect to `punie server` via WebSocket
- Send prompts and receive streaming responses
- Display tool execution in real-time
- Manage session lifecycle (create, reconnect, cleanup)

**Scope Decision:** Work in **Punie repo** (not Toad repo). Build client utilities that Toad will consume, following the same pattern as Phase 28's `stdio_bridge.py` and `ask_client.py`.

**Expected Outcome:**
- Toad UI connects to punie server (WebSocket handshake works)
- Full prompt lifecycle (send prompt → stream response → complete)
- Tool calling displays in UI (tool start/progress/completion)
- Session management (create, reconnect, proper cleanup)

**Spec Folder:** `agent-os/specs/2026-02-16-2100-toad-frontend-websocket/`

---

## Task 1: Save Spec Documentation ✅

Create `agent-os/specs/2026-02-16-2100-toad-frontend-websocket/` with:
- plan.md (this file)
- shape.md (scope, success criteria, decisions, context)
- standards.md (agent-verification, function-based-tests, protocol-first-design, fakes-over-mocks)
- references.md (key implementation patterns from exploration)

---

## Task 2: Create Toad WebSocket Client Module

**File:** `src/punie/client/toad_client.py` (~200 lines)

**Purpose:** WebSocket client optimized for browser-based Toad frontend with streaming support.

**Key Functions:**

### 1. `run_toad_client(server_url, cwd, callback)`
Main entry point for Toad integration.

**Pattern from ask_client.py (lines 24-80):**
```python
async def run_toad_client(
    server_url: str,
    cwd: str,
    on_update: Callable[[dict[str, Any]], None],
) -> None:
    """Run Toad WebSocket client.

    Args:
        server_url: WebSocket URL (ws://localhost:8000/ws)
        cwd: Current working directory
        on_update: Callback for session_update notifications

    Pattern:
        1. Connect using punie_session context manager
        2. Register callback for streaming updates
        3. Maintain connection until explicitly closed
    """
```

### 2. `send_prompt_stream(websocket, session_id, prompt, on_chunk)`
Send prompt and stream responses via callback.

**Pattern from ask_client.py (lines 82-141):**
```python
async def send_prompt_stream(
    websocket: ClientConnection,
    session_id: str,
    prompt: str,
    on_chunk: Callable[[str, dict[str, Any]], None],
) -> dict[str, Any]:
    """Send prompt, stream updates via callback.

    Args:
        websocket: Connected WebSocket client
        session_id: Active session ID
        prompt: User prompt text
        on_chunk: Callback(update_type, content) for each chunk

    Returns:
        Final response result

    Streaming Pattern:
        1. Send prompt request with UUID request_id
        2. Loop receive messages with 5min timeout
        3. For each session_update notification:
           - Extract update_type from params.update.sessionUpdate
           - Call on_chunk(update_type, content)
        4. Exit on response with matching request_id
        5. Return final result
    """
```

### 3. `handle_tool_update(update, on_tool_call)`
Parse and dispatch tool execution updates.

**Pattern from helpers.py and schema.py:**
```python
async def handle_tool_update(
    update: dict[str, Any],
    on_tool_call: Callable[[str, dict[str, Any]], None],
) -> None:
    """Handle tool call updates.

    Update types to handle:
        - "tool_call" (ToolCallStart) - tool execution begins
        - "tool_call_update" (ToolCallProgress) - tool progress

    Extract from update:
        - tool_call_id (string)
        - title (string)
        - kind (string: "read", "edit", "execute", etc.)
        - status (string: "pending", "in_progress", "completed", "failed")
        - content (list of ContentBlock)
        - locations (list of {path, line})

    Pattern:
        1. Check update["sessionUpdate"] type
        2. Extract tool call fields
        3. Call on_tool_call(tool_call_id, tool_data)
    """
```

### 4. `create_toad_session(server_url, cwd)`
Convenience wrapper for session creation.

**Pattern from connection.py punie_session (lines 159-193):**
```python
async def create_toad_session(
    server_url: str,
    cwd: str,
) -> tuple[ClientConnection, str]:
    """Create session and return (websocket, session_id).

    Pattern:
        1. Connect via connect_to_server()
        2. Perform initialize_session() handshake
        3. Return websocket and session_id

    Note: Caller responsible for cleanup (websocket.close())
    """
```

**Critical Implementation Details from Exploration:**

- **Use UUID for request IDs** (not integers) - websocket_client.py line 91
- **5-minute timeout for long operations** - ask_client.py line 82
- **Handle asyncio.TimeoutError and ConnectionClosed** - ask_client.py lines 85-86
- **Skip notifications while waiting for response** - ask_client.py line 98
- **Extract sessionUpdate field (camelCase)** - ask_client.py line 103
- **Check message.get("id") == request_id for exit** - ask_client.py line 118

**Dependencies:**
- Reuse `src/punie/client/connection.py` utilities:
  - `connect_to_server(url)`
  - `send_request(websocket, method, params)`
  - `initialize_session(websocket, cwd)`
  - `punie_session(server_url, cwd)` context manager

**Error Handling:**
- Timeout protection (30s per request, 5min for streaming)
- Connection closed during streaming → raise ConnectionError
- Malformed JSON → log warning, skip message
- Missing callback → graceful no-op

---

## Task 3: Add Toad Client Tests

**File:** `tests/test_toad_client.py` (~150 lines)

**Test Categories:**

### 1. Connection Tests (function-based)
```python
def test_create_toad_session_connects_and_handshakes():
    """Test session creation performs ACP handshake."""
    # Uses TestClient + websocket_connect pattern
    # Verify: initialize + new_session requests sent
    # Assert: Returns (websocket, session_id)

def test_create_toad_session_handles_connection_failure():
    """Test graceful handling of server unavailable."""
    # Mock connection failure
    # Assert: Raises ConnectionError with clear message
```

### 2. Streaming Tests (function-based)
```python
def test_send_prompt_stream_calls_callback_for_each_chunk():
    """Test streaming chunks invoke callback."""
    # Setup: Mock websocket with session_update notifications
    # Send: Prompt with callback
    # Assert: Callback called for each agent_message_chunk
    # Assert: Final result returned

def test_send_prompt_stream_handles_timeout():
    """Test timeout protection on long operations."""
    # Setup: Mock websocket that never responds
    # Assert: Raises TimeoutError after 5 minutes

def test_send_prompt_stream_skips_notifications():
    """Test non-response notifications are ignored."""
    # Setup: Mix of session_update and other notifications
    # Assert: Only session_update notifications processed
    # Assert: Other notifications skipped
```

### 3. Tool Update Tests (function-based)
```python
def test_handle_tool_update_parses_tool_call_start():
    """Test tool_call update extraction."""
    # Setup: tool_call notification (ToolCallStart)
    # Assert: Extracts tool_call_id, title, kind, status
    # Assert: Callback called with tool_data

def test_handle_tool_update_parses_tool_call_progress():
    """Test tool_call_update extraction."""
    # Setup: tool_call_update notification (ToolCallProgress)
    # Assert: Extracts updated status
    # Assert: Callback called with progress

def test_handle_tool_update_ignores_non_tool_updates():
    """Test non-tool updates are no-op."""
    # Setup: agent_message_chunk notification
    # Assert: Callback not called
```

### 4. Integration Tests (function-based)
```python
def test_toad_client_full_prompt_lifecycle():
    """Test complete prompt → response flow."""
    # Uses TestClient + real WebSocket endpoint
    # Steps:
    #   1. Create session
    #   2. Send prompt
    #   3. Collect streaming chunks
    #   4. Verify final response
    # Assert: All chunks received in order
    # Assert: Final result matches

def test_toad_client_handles_reconnection():
    """Test reconnection after disconnect."""
    # Setup: Disconnect WebSocket mid-stream
    # Assert: ConnectionError raised
    # Assert: Can reconnect and create new session
```

**Testing Pattern (from Phase 28):**
- Use `TestClient(app)` for integration tests
- Use `client.websocket_connect("/ws")` for WebSocket connections
- Use fake callbacks (simple functions that append to list)
- Use `asyncio.run()` for async test functions
- Follow function-based-tests standard (no test classes)

**Fixtures Needed:**
```python
@pytest.fixture
def fake_callback():
    """Fake callback that records calls."""
    calls = []
    def callback(update_type: str, content: dict):
        calls.append((update_type, content))
    callback.calls = calls
    return callback

@pytest.fixture
def test_websocket():
    """TestClient WebSocket connection."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            yield ws
```

---

## Task 4: Export Toad Client in Package

**File:** `src/punie/client/__init__.py` (modify)

**Add exports:**
```python
from punie.client.toad_client import (
    run_toad_client,
    send_prompt_stream,
    handle_tool_update,
    create_toad_session,
)

__all__ = [
    # Existing exports
    "connect_to_server",
    "send_request",
    "initialize_session",
    "punie_session",
    "run_stdio_bridge",
    "run_ask_client",
    # New Toad exports
    "run_toad_client",
    "send_prompt_stream",
    "handle_tool_update",
    "create_toad_session",
]
```

---

## Task 5: Add Toad Client Documentation

**File:** `docs/toad-client-guide.md` (~100 lines)

**Sections:**

### 1. Quick Start
```python
from punie.client import create_toad_session, send_prompt_stream

# Create session
websocket, session_id = await create_toad_session(
    server_url="ws://localhost:8000/ws",
    cwd="/path/to/workspace"
)

# Define callback
def on_chunk(update_type, content):
    if update_type == "agent_message_chunk":
        print(content["text"])

# Send prompt with streaming
result = await send_prompt_stream(
    websocket, session_id, "Hello!", on_chunk
)
```

### 2. Tool Execution Handling
```python
def on_tool_call(tool_call_id, tool_data):
    print(f"Tool: {tool_data['title']}")
    print(f"Kind: {tool_data['kind']}")
    print(f"Status: {tool_data['status']}")

# Handle tool updates
await handle_tool_update(update, on_tool_call)
```

### 3. Connection Management
- How to create sessions
- Reconnection strategies
- Cleanup on disconnect

### 4. Error Handling
- Timeout scenarios
- Connection failures
- Malformed responses

### 5. Integration with Toad
- Expected callback signatures
- Update type reference
- Session lifecycle

---

## Task 6: Update Phase 28 Docs

**File:** `docs/client-setup-guide.md` (modify)

**Add section:**
```markdown
## Toad Frontend Client

For browser-based Toad integration:

```python
from punie.client import run_toad_client

await run_toad_client(
    server_url="ws://localhost:8000/ws",
    cwd="/workspace",
    on_update=handle_update  # Your callback
)
```

See `docs/toad-client-guide.md` for complete reference.
```

---

## Critical Files

**Create:**
- `src/punie/client/toad_client.py` (~200 lines)
- `tests/test_toad_client.py` (~150 lines)
- `docs/toad-client-guide.md` (~100 lines)
- `agent-os/specs/2026-02-16-2100-toad-frontend-websocket/` (spec folder with 4 files)

**Modify:**
- `src/punie/client/__init__.py` (+8 lines for exports)
- `docs/client-setup-guide.md` (+10 lines for Toad section)

**Reference (do not modify):**
- `src/punie/client/connection.py` - Reuse WebSocket utilities
- `src/punie/client/ask_client.py` - Pattern reference (lines 24-141)
- `src/punie/http/websocket.py` - Server patterns (lines 28-114, 210-264)
- `src/punie/acp/helpers.py` - Message helpers (lines 87-299)

---

## Verification

Following **agent-verification** standard:

### 1. Type Checking
```bash
# Use astral:ty skill to check types
```
Expected: All type checks pass, no new errors

### 2. Linting
```bash
# Use astral:ruff skill to check and fix linting
```
Expected: All ruff checks pass, code formatted correctly

### 3. Testing
```bash
uv run pytest tests/test_toad_client.py -v
```
Expected: All tests pass (~10-12 tests)

### 4. Integration Testing
```bash
# Start server in background
uv run punie serve &

# Run integration tests
uv run pytest tests/test_toad_client.py::test_toad_client_full_prompt_lifecycle -v

# Stop server
kill %1
```
Expected: Full prompt lifecycle works end-to-end

### 5. Existing Tests
```bash
uv run pytest tests/ -v
```
Expected: All existing tests still pass (609 tests from Phase 28)

---

## Success Criteria

**✅ Phase 29 Complete When:**

1. `toad_client.py` implements all 4 core functions
2. All tests pass (new + existing 609 tests)
3. Documentation complete (toad-client-guide.md)
4. Type checking passes (astral:ty)
5. Linting passes (astral:ruff)
6. Integration test validates:
   - WebSocket connection works
   - Prompt streaming works
   - Tool updates parse correctly
   - Session lifecycle manages properly

**Ready for:** Phase 30 (Thin ACP Router) or integration with actual Toad frontend

---

## Standards Applied

This implementation follows:
- **agent-verification** - Use Astral skills (ruff, ty), not justfile
- **function-based-tests** - All tests as functions, no classes
- **protocol-first-design** - Define callback protocols before implementation
- **fakes-over-mocks** - Use fake callbacks, not mock frameworks

Full standards content saved in `agent-os/specs/2026-02-16-2100-toad-frontend-websocket/standards.md`
