# Toad WebSocket Integration - Implementation Plan

## Context

**Why we're building this:**

Phase 29 (completed 2026-02-16) built WebSocket client infrastructure in the Punie repo to enable browser-based Toad frontend integration. The Punie side is complete with 4 core functions (`create_toad_session`, `send_prompt_stream`, `handle_tool_update`, `run_toad_client`) plus comprehensive documentation.

**Current state:**
- ✅ Punie server runs HTTP/WebSocket on port 8000 (Phase 28)
- ✅ Punie WebSocket client utilities complete (Phase 29)
- ✅ Complete API documentation in `docs/toad-client-guide.md`
- ✅ All 620 tests passing
- Toad UI exists at `~/PycharmProjects/toad` with stdio-based ACP agent (`toad/acp/agent.py`)

**The gap:**

Toad currently uses stdio/subprocess to communicate with agents. We need to create **reference integration code in the Punie repo** that shows how Toad can use WebSocket transport instead of stdio.

**Scope decision:**

Work in **Punie repo** to create example/bridge code that Toad developers can reference when adding WebSocket support to Toad's Agent class. This keeps the integration patterns centralized with the WebSocket client utilities.

**Expected outcome:**

Punie repo will have working example code demonstrating how to wrap the WebSocket client utilities in a Toad-compatible interface, plus documentation guiding Toad developers through the integration.

## Success Criteria

**✅ Complete when:**

1. Example WebSocket agent wrapper created showing Toad integration patterns
2. Working reference implementation that can be tested end-to-end
3. Integration guide for Toad developers
4. All tests pass (new + existing 620 tests)
5. Type checking and linting pass

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-16-2120-toad-websocket-integration/` with:

**1. plan.md** - This complete implementation plan

**2. shape.md** - Shaping decisions:
- Scope: Create Toad integration examples in Punie repo (not in Toad repo)
- Success criteria: Working reference implementation
- Decisions:
  - Work in Punie repo to keep integration patterns centralized
  - Create example WebSocket agent wrapper
  - Show how to adapt WebSocket client API to Toad's Agent interface
- Context:
  - Visuals: Use existing Toad UI (no mockups needed)
  - References:
    - `docs/toad-client-guide.md` - Integration patterns
    - `src/punie/client/toad_client.py` - WebSocket client implementation
    - `~/PycharmProjects/toad/src/toad/acp/agent.py` - Current stdio agent (lines 1-100)
    - `~/PycharmProjects/toad/src/toad/agent.py` - AgentBase interface (lines 1-50)
  - Product alignment: Complete Phase 29 (enable Toad frontend)

**3. standards.md** - Full content of:
- **agent-verification** (always included)
- **function-based-tests** (testing patterns)

**4. references.md** - Key implementation references

## Task 2: Create Toad WebSocket Agent Example

**File:** `examples/toad_websocket_agent.py` (~150 lines)

**Purpose:** Reference implementation showing how to integrate Punie's WebSocket client with Toad's Agent interface.

**Class Structure:**

```python
class ToadWebSocketAgent:
    """Example WebSocket agent for Toad integration.

    This demonstrates how to use Punie's WebSocket client utilities
    to create a Toad-compatible agent that connects over WebSocket
    instead of stdio/subprocess.

    Toad developers can use this as a reference for implementing
    WebSocket transport in toad/acp/agent.py.

    Key differences from stdio agent:
    - No subprocess management
    - Persistent WebSocket connection
    - Built-in reconnection support
    - Streaming via callbacks
    """
```

**Key Methods:**

1. `__init__(server_url, project_root)` - Initialize with WebSocket URL
2. `async connect()` - Establish WebSocket connection and ACP handshake
3. `async send_prompt(prompt)` - Send prompt and handle streaming response
4. `async disconnect()` - Clean up WebSocket connection
5. `_handle_update(update_type, content)` - Internal callback for streaming

**Integration Pattern:**

- Wraps `create_toad_session()` and `send_prompt_stream()` from `punie.client`
- Provides async interface similar to Toad's `AgentBase.send_prompt()`
- Shows callback pattern for streaming updates
- Demonstrates tool update handling

**Error Handling:**

- Connection failures → clear error messages
- Timeout protection (5 minutes)
- WebSocket disconnect → graceful recovery

## Task 3: Create Integration Documentation

**File:** `docs/toad-integration-guide.md` (~100 lines)

**Sections:**

### 1. Overview
- How Punie WebSocket client works with Toad
- Architecture: Toad UI → WebSocket → Punie Server
- Benefits: no subprocess, persistent connection, reconnection support

### 2. Quick Start

```python
from examples.toad_websocket_agent import ToadWebSocketAgent

# Create agent
agent = ToadWebSocketAgent(
    server_url="ws://localhost:8000/ws",
    project_root="/path/to/project"
)

# Connect and use
await agent.connect()
await agent.send_prompt("What is dependency injection?")
await agent.disconnect()
```

### 3. Integration with Toad

**Where to modify:** `toad/acp/agent.py`

**Approach:**
1. Add WebSocket transport alongside existing stdio transport
2. Add configuration for server URL vs subprocess command
3. Implement transport selection logic
4. Reuse existing ACP protocol handling

**Pattern:**
```python
# In toad/acp/agent.py
if agent_data.use_websocket:
    # Use WebSocket transport
    self._websocket, self._session_id = await create_toad_session(
        agent_data.server_url,
        str(project_root)
    )
else:
    # Use stdio transport (existing code)
    self._process = await asyncio.create_subprocess_exec(...)
```

### 4. Testing
- How to test the example
- Running Punie server
- Connecting from example agent
- Verifying streaming and tool updates

### 5. Next Steps
- Implementing in Toad
- Configuration options
- Migration path from stdio

## Task 4: Add Integration Tests

**File:** `tests/test_toad_integration.py` (~100 lines)

**Test Categories (function-based):**

### 1. Example Agent Tests

```python
def test_toad_websocket_agent_connects():
    """Test example agent can connect to Punie server."""
    # Verifies connection and handshake work

def test_toad_websocket_agent_sends_prompt():
    """Test example agent can send prompt and receive response."""
    # Sends simple prompt, verifies streaming

def test_toad_websocket_agent_handles_tools():
    """Test example agent handles tool execution updates."""
    # Sends prompt that triggers tools, verifies updates
```

### 2. Integration Tests

```python
def test_full_toad_lifecycle():
    """Test complete lifecycle: connect → prompt → response → disconnect."""
    # End-to-end test with real server
```

**Testing Pattern:**
- Use `TestClient(app)` for server
- Use fake callbacks to capture streaming
- Follow function-based-tests standard
- No classes, just functions

## Task 5: Update Client Setup Guide

**File:** `docs/client-setup-guide.md` (modify)

**Add section after existing Toad Frontend Client section:**

```markdown
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

**Integration Guide:** See `docs/toad-integration-guide.md` for step-by-step instructions on adding WebSocket transport to Toad's ACP agent.
```

## Critical Files

**Create:**
- `examples/toad_websocket_agent.py` (~150 lines)
- `docs/toad-integration-guide.md` (~100 lines)
- `tests/test_toad_integration.py` (~100 lines)
- `agent-os/specs/2026-02-16-2120-toad-websocket-integration/` (spec folder)

**Modify:**
- `docs/client-setup-guide.md` (+15 lines)

**Reference (do not modify):**
- `src/punie/client/toad_client.py` - WebSocket client utilities
- `docs/toad-client-guide.md` - API reference
- `~/PycharmProjects/toad/src/toad/acp/agent.py` - Toad's current agent
- `~/PycharmProjects/toad/src/toad/agent.py` - Toad's AgentBase

## Verification

Following **agent-verification** standard:

### 1. Type Checking
```bash
# Use astral:ty skill
```
Expected: All checks pass, no new errors

### 2. Linting
```bash
# Use astral:ruff skill
```
Expected: All checks pass, code formatted

### 3. Testing
```bash
uv run pytest tests/test_toad_integration.py -v
```
Expected: All tests pass (~4-5 tests)

### 4. Integration Testing
```bash
# Start Punie server
uv run punie serve &

# Run example
uv run python examples/toad_websocket_agent.py

# Stop server
kill %1
```
Expected: Example connects, sends prompt, streams response

### 5. Existing Tests
```bash
uv run pytest tests/ -v
```
Expected: All 620 tests still pass

## Implementation Notes

**Reuse Existing Code:**
- Use `punie.client.toad_client` functions directly
- Don't duplicate WebSocket logic
- Follow patterns from `ask_client.py`

**Key Patterns to Demonstrate:**
- Callback-based streaming
- Mapping Punie callbacks to Toad messages
- Tool execution visibility
- Session lifecycle management

**Documentation Focus:**
- Make it easy for Toad developers to understand
- Show complete working example
- Provide step-by-step integration guide
- Reference both codebases (Punie and Toad)

## Standards Applied

- **agent-verification** - Use Astral skills (ruff, ty), not justfile
- **function-based-tests** - All tests as functions, no classes
