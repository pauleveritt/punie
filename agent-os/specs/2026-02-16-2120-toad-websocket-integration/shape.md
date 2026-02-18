# Toad WebSocket Integration - Shaping Notes

## Problem Statement

Phase 29 completed the WebSocket client infrastructure in Punie, but there's no working example showing how Toad developers should integrate it with the Toad UI frontend. The gap prevents Toad from moving from stdio/subprocess transport to WebSocket transport.

## Scope Decision

**Work in Punie repo**, not Toad repo:
- Keep integration patterns centralized with WebSocket client utilities
- Create reference implementation that Toad developers can study
- Provide clear documentation and examples
- Don't modify Toad codebase directly

**Why this approach:**
- Punie owns the WebSocket client API
- Integration patterns should live alongside the API they integrate
- Toad developers can reference complete working example
- Keeps Punie and Toad codebases loosely coupled

## Success Criteria

**✅ Complete when:**
1. Working example agent wrapper (`examples/toad_websocket_agent.py`)
2. Integration guide for Toad developers (`docs/toad-integration-guide.md`)
3. Integration tests demonstrating usage patterns
4. Updated client setup guide with quick reference
5. All 620+ existing tests still pass
6. Type checking and linting pass

## Key Decisions

### Decision 1: Example Over Direct Integration

**Options:**
1. ❌ Modify Toad repo directly
2. ✅ Create reference implementation in Punie repo
3. ❌ Write docs only, no working code

**Chosen:** Option 2 - Reference implementation

**Rationale:**
- Respects Toad repo ownership (Paul's other project)
- Provides working, testable code as reference
- Centralizes integration patterns with the API
- Easier to maintain (one codebase)

### Decision 2: Wrapper Class vs Direct Usage

**Options:**
1. Show direct usage of `create_toad_session` and `send_prompt_stream`
2. ✅ Create wrapper class that encapsulates WebSocket lifecycle
3. Provide multiple examples (simple + complex)

**Chosen:** Option 2 - Wrapper class

**Rationale:**
- Demonstrates complete integration pattern
- Shows session lifecycle management
- Easier for Toad developers to understand
- Single reference implementation to maintain

### Decision 3: Testing Approach

**Options:**
1. Manual testing only (no automated tests)
2. ✅ Integration tests using TestClient
3. End-to-end tests requiring real servers

**Chosen:** Option 2 - TestClient integration tests

**Rationale:**
- Tests demonstrate correct usage patterns
- No external dependencies (servers, network)
- Fast, reliable, can run in CI
- Validates the example code works

### Decision 4: Documentation Scope

**Sections included:**
- ✅ Overview of architecture and benefits
- ✅ Quick start code example
- ✅ Integration with Toad (where to modify)
- ✅ Testing instructions
- ✅ Next steps and migration path

**Sections excluded:**
- ❌ Toad UI implementation details (out of scope)
- ❌ ACP protocol deep dive (covered elsewhere)
- ❌ Browser WebSocket implementation (JavaScript)

## Context and References

### Visuals
- No mockups needed - Toad UI already exists
- Architecture diagram would be helpful but not blocking
- Code examples are primary deliverable

### Key References

**Punie side (implemented):**
- `src/punie/client/toad_client.py` - WebSocket client implementation
- `docs/toad-client-guide.md` - Complete API documentation
- `src/punie/client/connection.py` - Low-level WebSocket utilities

**Toad side (to reference):**
- `~/PycharmProjects/toad/src/toad/acp/agent.py` (lines 1-100) - Current stdio agent
- `~/PycharmProjects/toad/src/toad/agent.py` (lines 1-50) - AgentBase interface

**Integration points:**
- Toad's Agent class uses stdio/subprocess currently
- Needs to add WebSocket transport option
- Should reuse existing ACP protocol handling
- Session lifecycle matches Toad's existing patterns

### Product Alignment

**Phase 29 completion:**
- WebSocket client utilities: ✅ Complete
- API documentation: ✅ Complete
- Integration examples: ⏸️ This spec

**Next phases:**
- Phase 30: Thin ACP router (multi-server routing)
- Phase 31: Multi-project support (workspace management)

**User story:**
> As a Toad developer, I want to add WebSocket transport to the Toad Agent class
> so that Toad UI can connect to Punie server without subprocess overhead.

## Implementation Approach

### 1. Create Example Agent Wrapper
- Class: `ToadWebSocketAgent`
- Methods: `connect()`, `send_prompt()`, `disconnect()`
- Wraps `create_toad_session()` and `send_prompt_stream()`
- Demonstrates callback-based streaming
- Shows error handling patterns

### 2. Write Integration Guide
- Overview section: architecture and benefits
- Quick start: minimal working example
- Integration section: how to modify Toad
- Testing section: how to verify it works
- Next steps: migration path and configuration

### 3. Add Integration Tests
- Test connection and handshake
- Test prompt sending and streaming
- Test tool execution visibility
- Test complete lifecycle
- Use function-based tests (no classes)

### 4. Update Client Setup Guide
- Add quick reference to example agent
- Link to integration guide
- Keep minimal (3-4 lines)

## Standards Applied

- **agent-verification** - Use Astral skills for verification
- **function-based-tests** - All tests as functions, no classes

## Risks and Mitigations

**Risk 1: Toad developers don't understand integration**
- Mitigation: Provide complete working example + detailed guide

**Risk 2: Example becomes outdated as API evolves**
- Mitigation: Integration tests will catch API changes

**Risk 3: WebSocket client has bugs not caught by tests**
- Mitigation: Phase 29 already has comprehensive tests

**Risk 4: Documentation is insufficient**
- Mitigation: Step-by-step guide with code snippets

## Out of Scope

- ❌ Modifying Toad codebase directly
- ❌ Implementing JavaScript/browser WebSocket client
- ❌ Building new Toad UI features
- ❌ Adding new WebSocket client features (Phase 29 is done)
- ❌ Multi-server routing (Phase 30)
- ❌ Multi-project support (Phase 31)

## Success Metrics

- ✅ Example code runs without errors
- ✅ All tests pass (new + existing 620)
- ✅ Type checking passes (no new errors)
- ✅ Linting passes (clean code)
- ✅ Documentation is clear and complete

## Timeline

**Estimated effort:** 2-3 hours
- Task 1 (Spec docs): 15 min
- Task 2 (Example agent): 45 min
- Task 3 (Integration guide): 30 min
- Task 4 (Tests): 45 min
- Task 5 (Update guide): 10 min
- Verification: 15 min

**Total:** ~2.5 hours for complete implementation
