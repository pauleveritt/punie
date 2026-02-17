# Phase 29: Toad WebSocket Client Implementation

**Date:** February 16, 2026
**Status:** ✅ Complete
**Branch:** `toad-frontend`
**Commit:** `6da02b8`

## Goal

Build WebSocket client infrastructure in the Punie repo to enable browser-based Toad frontend integration with streaming support and tool execution visibility.

## Context

Phase 28 separated Punie into server-only mode (HTTP/WebSocket) with thin clients. Phase 29 completes the client-side infrastructure by adding Toad-compatible WebSocket utilities that the browser UI can consume.

**Scope Decision:** Work in Punie repo (not Toad repo) to keep ACP protocol knowledge centralized and provide reusable utilities.

## Implementation

### Core Functions (4)

**1. `create_toad_session(server_url, cwd)`**
- Creates WebSocket connection to Punie server
- Performs ACP handshake (initialize → new_session)
- Returns (websocket, session_id) tuple
- Caller responsible for cleanup (explicit control)

**2. `send_prompt_stream(websocket, session_id, prompt, on_chunk)`**
- Sends prompt request with UUID request_id
- Streams session_update notifications via callback
- 5-minute timeout for long operations
- Returns final response result

**3. `handle_tool_update(update, on_tool_call)`**
- Parses tool_call and tool_call_update notifications
- Extracts tool metadata (title, kind, status, locations)
- Dispatches to dedicated callback
- Handles both ToolCallStart and ToolCallProgress

**4. `run_toad_client(server_url, cwd, on_update)`**
- Maintains persistent WebSocket connection
- Event loop for receiving messages
- Routes all session_update notifications to callback
- Graceful shutdown on disconnect or interrupt

### Architecture Decisions

**1. Callback-Based Streaming (Not Async Iterators)**
- Matches ask_client.py pattern (proven in Phase 28)
- Browser-compatible (callbacks work in JS/TS)
- Simple to test with fake callbacks
- Integrates with any UI framework (React, Vue, etc.)

**2. Reuse connection.py Utilities**
- `connect_to_server()` - WebSocket connection
- `initialize_session()` - ACP handshake
- `punie_session()` - Context manager for lifecycle
- No duplication of WebSocket logic

**3. Separate Tool Update Handler**
- Tool updates have complex structure (ToolCallStart vs ToolCallProgress)
- Toad may want different UI for different tool types
- Easier to test in isolation
- Follows single-responsibility principle

**4. 5-Minute Timeout for Streaming**
- Complex queries can take minutes (model generation, multi-tool workflows)
- Matches ask_client.py timeout (300s)
- 30-second timeout for simple requests (send_request)

### Files Created

**Implementation:**
- `src/punie/client/toad_client.py` (345 lines)
  - 4 core functions with comprehensive docstrings
  - Error handling (timeout, disconnect, malformed JSON)
  - Type hints throughout

**Tests:**
- `tests/test_toad_client.py` (457 lines, 11 tests)
  - Connection tests (2)
  - Streaming tests (3)
  - Tool update tests (4)
  - Integration tests (2)
  - Uses fake callbacks (no mock framework)
  - All tests pass in 0.17s

**Documentation:**
- `docs/toad-client-guide.md` (573 lines)
  - Quick start examples
  - Function reference with signatures
  - Update type reference
  - Connection management patterns
  - Error handling strategies
  - Browser integration examples (JavaScript)

**Spec Documentation:**
- `agent-os/specs/2026-02-16-2100-toad-frontend-websocket/plan.md` (484 lines)
- `agent-os/specs/2026-02-16-2100-toad-frontend-websocket/shape.md` (230 lines)
- `agent-os/specs/2026-02-16-2100-toad-frontend-websocket/standards.md` (233 lines)
- `agent-os/specs/2026-02-16-2100-toad-frontend-websocket/references.md` (514 lines)

**Package Updates:**
- `src/punie/client/__init__.py` - Exported 4 new functions
- `docs/client-setup-guide.md` - Added Toad client section

### Test Results

**New Tests:** 11 tests, all passing (0.17s total)
- ✅ Connection management (handshake, failure handling)
- ✅ Streaming with callbacks
- ✅ Timeout protection (mocked for speed)
- ✅ Tool update parsing (ToolCallStart + ToolCallProgress)
- ✅ Integration with real WebSocket endpoint

**Total Test Suite:** 620 tests passing (609 from Phase 28 + 11 new)
- 11 skipped
- 6 deselected
- 1 xfailed
- 2 xpassed

**Quality Verification:**
- ✅ Type checking passed (ty)
- ✅ Linting passed (ruff)
- ✅ All standards applied (agent-verification, function-based-tests, protocol-first-design, fakes-over-mocks)

### Key Patterns

**WebSocket Connection:**
```python
websocket, session_id = await create_toad_session(
    "ws://localhost:8000/ws",
    "/path/to/workspace"
)
```

**Streaming with Callbacks:**
```python
def on_chunk(update_type, content):
    if update_type == "agent_message_chunk":
        print(content.get("content", {}).get("text", ""))

result = await send_prompt_stream(ws, sid, "Query", on_chunk)
```

**Tool Execution:**
```python
def on_tool_call(tool_call_id, tool_data):
    print(f"Tool: {tool_data['title']}")
    print(f"Status: {tool_data['status']}")

await handle_tool_update(update, on_tool_call)
```

### Critical Implementation Details

**From Phase 28 Experience:**
- UUID request IDs (prevent collision in concurrent requests)
- 5-minute timeout for streaming (300s)
- 30-second timeout for simple requests
- Skip notifications while waiting for response
- Extract `sessionUpdate` field (camelCase!)
- Handle malformed JSON gracefully (log + continue)
- Callback exceptions logged but don't crash streaming

**Error Handling:**
- `asyncio.TimeoutError` → RuntimeError ("No response from server")
- `websockets.exceptions.ConnectionClosed` → ConnectionError
- `json.JSONDecodeError` → log warning + continue
- Callback exceptions → log error + continue (don't crash)

### Browser Integration Path

**For Toad UI developers:**

1. Use native WebSocket API in browser
2. Follow patterns in `docs/toad-client-guide.md`
3. Example JavaScript wrapper:
```javascript
class ToadClient {
    async connect() {
        this.ws = new WebSocket('ws://localhost:8000/ws');
        await this.initialize();
        this.sessionId = await this.createSession();
    }

    async sendPrompt(prompt, onChunk) {
        // Use patterns from toad-client-guide.md
    }
}
```

## What's Ready

**✅ Punie Server (Phase 28):**
- HTTP/WebSocket server on port 8000
- ACP protocol over WebSocket
- Session management with keep-alive
- Multi-client support

**✅ Punie Client (Phase 29):**
- WebSocket connection utilities
- Session creation and handshake
- Streaming prompt execution
- Tool update parsing
- Complete documentation

## What's Next

**Phase 30: Thin ACP Router (Optional)**
- Router sits between Toad and Punie
- Multi-server routing logic
- Reconnection and diagnostics

**Phase 31: Multi-Project Support**
- One Punie server per project
- Router manages multiple connections
- Workspace-based session routing

**Toad Integration (Next Step):**
- Implement WebSocket client in Toad UI
- Use patterns from toad-client-guide.md
- Connect to running Punie server
- Test end-to-end: Browser → Toad → Punie → Agent

## Deliverables Summary

| Item | Lines | Status |
|------|-------|--------|
| Implementation | 345 | ✅ |
| Tests | 457 | ✅ (11 tests, all passing) |
| API Documentation | 573 | ✅ |
| Spec Documentation | 1,461 | ✅ (4 files) |
| **Total** | **2,836** | ✅ |

**9 files changed, 2,893 insertions(+), 1 deletion(-)**

## Success Criteria Met

- ✅ Connection management works (handshake, cleanup)
- ✅ Prompt lifecycle complete (send → stream → finish)
- ✅ Tool updates parse correctly (start + progress)
- ✅ Session lifecycle manages properly
- ✅ All tests pass (new + existing 620 total)
- ✅ Type checking passes
- ✅ Linting passes
- ✅ Documentation complete

## Standards Applied

- **agent-verification:** Used astral:ty and astral:ruff (not justfile)
- **function-based-tests:** All tests as functions, no classes
- **protocol-first-design:** Callback protocols documented with type hints
- **fakes-over-mocks:** Used fake callbacks, no unittest.mock

## Conclusion

Phase 29 successfully built the missing WebSocket client infrastructure for Toad frontend integration. The Punie side is now complete:

- ✅ Server runs HTTP/WebSocket (Phase 28)
- ✅ Client utilities ready for consumption (Phase 29)
- ✅ Complete API documentation with examples
- ✅ Browser-compatible callback pattern

**Next step:** Toad UI implements WebSocket client using our utilities.

**Architecture:** Server-only Punie + thin clients (stdio bridge, ask client, Toad frontend)

**Status:** Ready for Toad browser UI integration! 🚀
