# Phase 28 Server/Client Separation - Shaping Notes

## Scope

Refactor Punie architecture to separate server (HTTP/WebSocket only) from clients (thin WebSocket wrappers).

## Problem Identified

Current `run_dual()` function runs stdio + HTTP in same process. When stdin closes (background mode), stdio task completes → triggers server shutdown via `FIRST_COMPLETED` cancellation.

**Impact:**
- Cannot run server in background (`punie serve &` immediately exits)
- Cannot use justfile recipes (`dev-servers-bg`) reliably
- Blocked Phase 29 (Toad frontend) and Phase 30 (thin ACP router)

## Solution Chosen

Replace dual-protocol runner with pure server/client separation:

1. **Server:** HTTP/WebSocket only (`run_http()`)
   - No stdin dependency
   - Runs indefinitely until explicitly stopped
   - Handles multiple WebSocket clients

2. **Clients:** Thin WebSocket wrappers
   - `punie` (default) - Stdio bridge for PyCharm
   - `punie ask` - CLI question client
   - Toad (future) - Browser frontend

## Decisions Made

### Decision 1: Server-Only Mode as Default

**Options considered:**
- A: Fix `run_dual()` to ignore stdin EOF
- B: Keep dual mode for PyCharm, server-only for `punie serve`
- C: Pure server/client separation (CHOSEN)

**Rationale for C:**
- Clearest architecture (single responsibility)
- Enables multi-client naturally
- Prepares for Toad frontend (Phase 29)
- No confusing mode switching

### Decision 2: Deprecate run_dual() (Don't Remove Yet)

**Rationale:**
- Keep for backward compatibility
- Mark with `.. deprecated::` directive
- Remove in future PR after user migration period

### Decision 3: Stdio Bridge is Stateless Proxy

**Options considered:**
- A: Bridge maintains local session state
- B: Bridge is stateless proxy (CHOSEN)

**Rationale for B:**
- Simpler implementation (just forward messages)
- Server owns all session state
- Easier to debug (single source of truth)

### Decision 4: Use websockets Library (Not Starlette Client)

**Rationale:**
- `websockets` is the standard Python WebSocket client
- Starlette's WebSocket is server-side only
- Clean separation: Starlette (server) + websockets (client)

### Decision 5: Ask Client Creates Session Per Invocation

**Options considered:**
- A: Reuse persistent session
- B: Create new session per invocation (CHOSEN)

**Rationale for B:**
- Simpler (no session persistence logic)
- `punie ask` is for one-shot questions
- Future: Add `--session-id` flag for persistence

## Alternative Approaches Considered

### Alternative A: Fix run_dual() to Ignore stdin EOF

```python
# Detect if stdin is closed (background mode)
if sys.stdin.isatty():
    run stdio task
else:
    skip stdio task
```

**Rejected because:**
- Violates clean architecture principles
- Still has dual-mode complexity
- Doesn't enable multi-client naturally

### Alternative B: Keep Dual Mode for PyCharm

**Scenario:**
- `punie` (default) - Dual mode (stdio + HTTP)
- `punie serve` - Server-only mode

**Rejected because:**
- Confusing to have two modes
- Harder to document and support
- Doesn't solve background mode problem for `punie` command

## Migration Strategy

### Phase 1: Implementation (This PR)
- Add new `run_http()`, client modules, update CLI
- Keep `run_dual()` deprecated for backward compatibility
- Update tests and documentation

### Phase 2: User Migration (Docs + Support)
- Publish migration guide
- Update PyCharm integration docs (via `punie init`)
- Provide support for users upgrading

### Phase 3: Cleanup (Future PR)
- Remove deprecated `run_dual()` function
- Remove old `--model` flag from `punie` (default command)

## Open Questions (Resolved)

### Q1: Should ask client support persistent sessions?
**Resolution:** No, create new session per invocation. Add `--session-id` flag in future if needed.

### Q2: Should stdio bridge validate JSON before forwarding?
**Resolution:** Yes, validate but don't fail - log warning and continue. This helps debugging without breaking the proxy.

### Q3: How to handle server connection failures?
**Resolution:** Fail fast with clear error message. Don't retry automatically (user should check server status).

## Constraints

1. **Backward compatibility:** Keep `run_dual()` temporarily
2. **Stdout purity:** Stdio bridge must not corrupt JSON-RPC on stdout
3. **Clean shutdown:** All clients must close WebSocket gracefully
4. **Error handling:** Connection failures must show helpful error messages

## Future Considerations

### Phase 29: Toad Frontend
- Browser-based UI connects via WebSocket
- Uses same `punie_session()` utilities as CLI clients
- Adds file upload, rich rendering, multi-session UI

### Phase 30: Thin ACP Router
- Remove PydanticAI from client (just ACP router)
- Server handles all AI model interactions
- Enables multi-model support (local + cloud)

### Phase 31: Multi-Project Support
- Single server, multiple workspace sessions
- Clients specify project in `new_session` params
- Server manages isolated sessions per project
