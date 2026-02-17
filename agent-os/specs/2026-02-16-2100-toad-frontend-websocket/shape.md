# Phase 29: Toad Frontend WebSocket Client - Shaping Notes

## Scope

**In Scope:**
- WebSocket client utilities in Punie repo (`src/punie/client/toad_client.py`)
- Streaming prompt execution with callback pattern
- Tool execution update parsing and dispatch
- Session lifecycle management (create, reconnect, cleanup)
- Comprehensive test coverage (connection, streaming, tool updates, integration)
- Documentation for Toad integration

**Out of Scope:**
- Toad UI implementation (handled in Toad repo)
- Browser-specific WebSocket wrapper (Toad's responsibility)
- HTTP REST endpoints (already in Phase 28)
- Multi-session management (Phase 31)
- Authentication/authorization (future phase)

## Success Criteria

**Phase 29 is complete when:**

1. **Connection Management** ✅
   - `create_toad_session()` performs ACP handshake
   - Returns (websocket, session_id) tuple
   - Handles connection failures gracefully

2. **Prompt Lifecycle** ✅
   - `send_prompt_stream()` sends prompt with UUID request_id
   - Streams agent_message_chunk updates via callback
   - Returns final response result
   - 5-minute timeout protection

3. **Tool Execution** ✅
   - `handle_tool_update()` parses tool_call and tool_call_update
   - Extracts tool_call_id, title, kind, status, locations
   - Dispatches to on_tool_call callback

4. **Integration** ✅
   - `run_toad_client()` maintains persistent connection
   - Processes all session_update notifications
   - Clean disconnect on exit

5. **Quality** ✅
   - All tests pass (new + existing 609)
   - Type checking passes (astral:ty)
   - Linting passes (astral:ruff)
   - Documentation complete

## Key Decisions

### Decision 1: Work in Punie Repo (Not Toad Repo)

**Rationale:**
- Punie owns the ACP client implementation
- Toad consumes these utilities (just like stdio_bridge.py)
- Keeps protocol knowledge centralized
- Easier to version and test

**Alternative Considered:**
- Build client in Toad repo
- **Rejected:** Would duplicate ACP protocol knowledge across repos

### Decision 2: Callback-Based Streaming (Not Async Iterators)

**Rationale:**
- Matches ask_client.py pattern (proven in Phase 28)
- Browser-compatible (callbacks work in JS/TS)
- Toad can integrate with any UI framework (React, Vue, etc.)
- Simple to test with fake callbacks

**Alternative Considered:**
- Use `async for` generators
- **Rejected:** More complex to consume in browser context

### Decision 3: Reuse connection.py Utilities (Not New WebSocket Layer)

**Rationale:**
- `connect_to_server()` and `initialize_session()` already exist
- Proven handshake pattern
- No need to duplicate WebSocket connection logic
- Consistent with ask_client.py

**Alternative Considered:**
- Build custom WebSocket wrapper
- **Rejected:** Unnecessary duplication

### Decision 4: Separate Tool Update Handler (Not Inline Parsing)

**Rationale:**
- Tool updates have complex structure (ToolCallStart vs ToolCallProgress)
- Toad may want different UI for different tool types
- Easier to test in isolation
- Follows single-responsibility principle

**Alternative Considered:**
- Parse tool updates inline in send_prompt_stream()
- **Rejected:** Would make streaming function too complex

### Decision 5: 5-Minute Timeout for Streaming (Not 30 Seconds)

**Rationale:**
- Complex queries can take minutes (model generation, multi-tool workflows)
- Matches ask_client.py timeout (300s)
- Server-side operations may be slow

**Alternative Considered:**
- Use 30-second timeout (like send_request())
- **Rejected:** Too short for real-world agent operations

## Context

### Product Alignment

**Roadmap Phase 29:**
> Build Toad WebSocket client to enable browser-based frontend integration with streaming support and tool execution visibility.

**Why Now:**
- Phase 28 separated server/client architecture
- Toad UI exists but cannot connect to Punie server
- Blocking Phase 30 (Thin ACP Router) and Phase 31 (Multi-Project)

### Technical Context

**From Phase 28:**
- Server runs HTTP/WebSocket on port 8000
- ACP protocol for all communication
- Session handshake: initialize → new_session
- Streaming via session_update notifications

**For Phase 30:**
- Thin ACP router will sit between Toad and Punie
- Router needs same client utilities we're building
- Reusability is critical

### References

**Implementation Patterns:**
- `src/punie/client/connection.py` - WebSocket utilities, session handshake
- `src/punie/client/ask_client.py` - Reference streaming client (lines 24-141)
- `src/punie/http/websocket.py` - Server-side handler (lines 28-114, 210-264)
- `src/punie/acp/helpers.py` - Message construction (lines 87-299)
- `src/punie/acp/schema.py` - Protocol types (ToolCallStart, ToolCallProgress)

**Testing Patterns (from Phase 28):**
- Use `TestClient(app)` for integration
- Use `client.websocket_connect("/ws")` for WebSocket
- Use fake callbacks (not mocks)
- Follow function-based-tests standard

### Visuals

**No visuals needed** - Toad UI already exists with mockups. This phase builds the client infrastructure only.

## Open Questions

**None** - All design decisions made during exploration:
- Callback pattern chosen
- Timeout values established (30s per request, 5min for streaming)
- Error handling strategy defined
- Integration pattern with connection.py confirmed

## Next Steps After Phase 29

**Phase 30: Thin ACP Router**
- Build router that sits between Toad and Punie
- Reuse toad_client.py utilities we're building
- Add multi-server routing logic

**Phase 31: Multi-Project Support**
- Extend router to manage multiple Punie servers
- One server per project/workspace
- Session routing by workspace ID

## Dependencies

**Upstream (must exist before Phase 29):**
- ✅ Phase 28 server infrastructure (HTTP/WebSocket endpoints)
- ✅ connection.py utilities (connect, initialize_session)
- ✅ ACP schema types (session_update, tool_call, etc.)

**Downstream (depends on Phase 29):**
- Phase 30: Thin ACP Router (uses toad_client.py)
- Phase 31: Multi-Project (extends router)
- Toad frontend integration (consumes client API)

## Risk Mitigation

**Risk 1: Browser WebSocket Compatibility**
- **Mitigation:** Build in Python first, Toad wraps in JS/TS
- **Fallback:** Provide REST polling API if WebSocket fails

**Risk 2: Callback Pattern Doesn't Work in Browser**
- **Mitigation:** Callbacks are universal (work in all languages)
- **Fallback:** Add async iterator wrapper if needed

**Risk 3: Message Parsing Breaks on Protocol Changes**
- **Mitigation:** Use Pydantic schema types from acp/schema.py
- **Fallback:** Version check in initialize handshake

**Risk 4: Connection Drops Mid-Stream**
- **Mitigation:** Raise ConnectionError, Toad can retry
- **Fallback:** Add exponential backoff in Phase 30

## Lessons from Phase 28

**What Worked:**
- TestClient + websocket_connect for integration tests
- Fake callbacks (simple, no mock framework)
- 5-minute timeout for long operations
- UUID request IDs (no collision)

**What to Avoid:**
- Mixing sync/async (stick to async throughout)
- Complex mock frameworks (use fakes)
- Short timeouts (broke long operations)
- Integer request IDs (caused collisions)

## Definition of Done

- [ ] All 4 functions implemented (run_toad_client, send_prompt_stream, handle_tool_update, create_toad_session)
- [ ] 10-12 tests written (connection, streaming, tool updates, integration)
- [ ] All tests pass (new + existing 609)
- [ ] Type checking passes (astral:ty)
- [ ] Linting passes (astral:ruff)
- [ ] Documentation complete (toad-client-guide.md)
- [ ] Exports added to __init__.py
- [ ] Integration test validates full lifecycle
- [ ] Spec documentation complete (this file + plan.md + standards.md + references.md)
