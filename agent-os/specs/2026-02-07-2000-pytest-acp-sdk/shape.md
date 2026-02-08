# Shape: Pytest ACP SDK Integration

## Scope

**In Scope:**
- Add `agent-client-protocol>=0.7.1` as production dependency
- Add `pytest-asyncio>=0.24.0` to dev dependencies
- Port test infrastructure (_Server, FakeAgent, FakeClient) from python-acp-sdk
- Write 7 focused integration tests proving ACP SDK works under Python 3.14.2t
- Configure pytest with `asyncio_mode = "auto"` for automatic async test handling
- Verify with Astral tools (ruff, ty) per agent-verification standard

**Out of Scope:**
- Exhaustive SDK test coverage (only critical paths)
- Punie's own ACP implementation (comes in Phase 2)
- Terminal operations testing (not needed yet)
- Extension method/notification testing (beyond basic examples)
- Process spawning tests (proven in SDK itself)

## Design Decisions

### 1. Two-file test structure
**Decision:** `tests/acp_helpers.py` for reusable classes, `tests/conftest.py` for fixtures

**Rationale:**
- Keeps fake implementations importable for future tests
- Separates fixture wiring from class definitions
- Follows pytest best practices

### 2. Rename TestAgent/TestClient → FakeAgent/FakeClient
**Decision:** Use "Fake" prefix instead of "Test" prefix

**Rationale:**
- Avoids pytest collection (though `__test__ = False` also prevents this)
- Clearer semantic meaning: these are fakes, not tests
- Consistent with testing nomenclature (Test Double → Fake)

### 3. pytest-asyncio auto mode
**Decision:** Set `asyncio_mode = "auto"` in pyproject.toml

**Rationale:**
- Removes `@pytest.mark.asyncio` boilerplate from every test
- No conflict with Sybil (only affects async test functions)
- Cleaner test code

### 4. Seven focused tests
**Decision:** Cover RPC, file ops, notifications, tool calls, concurrency—not everything

**Rationale:**
- Goal is to prove SDK works under 3.14t, not test the SDK itself
- SDK already has comprehensive tests
- Focus on integration points Punie will use
- Keep test maintenance burden low

### 5. Production dependency
**Decision:** Add `agent-client-protocol` to main dependencies, not dev-only

**Rationale:**
- Punie will use SDK's schema models and protocols during Phase 2 exploration
- Phase 3 replaces SDK with Punie's own implementation
- Temporary production use justifies main dependencies placement

## Context

### Why Now?
- Roadmap 1.4 requires proving ACP SDK works under Python 3.14.2t
- Phase 2 (Punie exploration) depends on SDK integration
- Need baseline test suite before building own ACP implementation

### Python 3.14t Concerns
- Free-threaded mode could expose concurrency issues
- Pydantic models need validation under 3.14t
- asyncio behavior verification critical

### Future Path
- Phase 2: Use SDK for exploration and learning
- Phase 3: Replace SDK with Punie's own ACP implementation
- These tests serve as regression suite during replacement

## Testing Strategy

### Test 1: Schema Model Roundtrip (Sync)
- No fixtures needed
- Proves Pydantic serialization works under 3.14t
- Foundation for all protocol messages

### Tests 2-5: RPC and Notifications (Async)
- Use TCP loopback via _Server
- Cover both directions: agent→client and client→agent
- Prove request-response and one-way notifications work

### Test 6: Tool Call Lifecycle (Async)
- Full permission flow: start → update → completion
- Critical for Punie's PyCharm integration
- Proves complex multi-message protocols work

### Test 7: Concurrent File Reads (Async)
- `asyncio.gather` over 5 parallel operations
- Directly tests free-threading safety
- Simulates real-world concurrent tool usage

## Non-Goals

- **Not testing edge cases** — SDK already does this
- **Not testing terminal operations** — Not needed for Phase 2
- **Not testing process spawning** — SDK handles this, not our concern yet
- **Not testing all extension methods** — Basic coverage sufficient

## Success Criteria

1. All 7 tests pass under Python 3.14.2t
2. `astral:ruff` reports no issues
3. `astral:ty` reports no type errors
4. `uv sync` completes successfully with new dependencies
5. Test output shows async fixtures working correctly
6. Roadmap 1.4 marked complete
