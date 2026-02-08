# Phase 4.2: Register IDE Tools Automatically

## Context

Phase 4.1 built the full dynamic tool discovery infrastructure — `discover_tools()`, `ToolCatalog`, three-tier toolset factories, and generic bridges for unknown IDE tools. However, discovery currently happens **on every `prompt()` call**, which means:

- Redundant `discover_tools()` RPC calls within the same session
- A new `PydanticAgent` constructed per prompt (wasteful — instructions, model, retries are identical)
- No session-scoped state for the discovered toolset

Phase 4.2 moves discovery from per-prompt to **session lifecycle** — tools are discovered once during `new_session()`, cached as immutable session state, and reused across all `prompt()` calls for that session.

## Plan Structure

### Task 1: Save spec documentation

Create `agent-os/specs/2026-02-08-1400-session-registration/` with:
- **plan.md** — This full plan
- **shape.md** — Shaping notes (scope, decisions, context)
- **standards.md** — All 5 applicable standards (full content)
- **references.md** — Pointers to 4.1 code and spec

### Task 2: Create `SessionState` frozen dataclass

**New file:** `src/punie/agent/session.py`

A frozen dataclass holding per-session cached state:

```python
@dataclass(frozen=True)
class SessionState:
    catalog: ToolCatalog | None          # None if Tier 2/3 fallback
    toolset: FunctionToolset[ACPDeps]
    agent: PydanticAgent[ACPDeps, str]
    discovery_tier: int                  # 1=catalog, 2=capabilities, 3=default
```

Follows `frozen-dataclass-services` standard. The `discovery_tier` field aids logging/observability.

### Task 3: Extract discovery helper and wire `new_session()`

**Modify:** `src/punie/agent/adapter.py`

1. Add `_sessions: dict[str, SessionState]` to `PunieAgent.__init__()`
2. Extract the three-tier discovery block (current `prompt()` lines 240-274) into `_discover_and_build_toolset(session_id) -> SessionState`
3. Call `_discover_and_build_toolset()` from `new_session()` and store result in `_sessions`
4. Guard: skip if no connection or legacy agent path is active

### Task 4: Simplify `prompt()` to use cached session state

**Modify:** `src/punie/agent/adapter.py`

Replace the 35-line discovery block in `prompt()` with:

```python
if self._legacy_agent:
    pydantic_agent = self._legacy_agent
elif session_id in self._sessions:
    pydantic_agent = self._sessions[session_id].agent
else:
    # Lazy fallback for callers that skip new_session()
    state = await self._discover_and_build_toolset(session_id)
    self._sessions[session_id] = state
    pydantic_agent = state.agent
```

Full backward compatibility: unknown session IDs trigger lazy discovery and cache the result.

### Task 5: Update `FakeClient` with discovery call tracking

**Modify:** `src/punie/testing/fakes.py`

Add `discover_tools_calls: list[str]` to track which session_ids triggered discovery. This lets tests assert discovery is called exactly once per session. Follows `fakes-over-mocks` standard.

### Task 6: Update exports

**Modify:** `src/punie/agent/__init__.py`

Add `SessionState` to public exports.

### Task 7: Write tests

**New file:** `tests/test_session_registration.py`

~16 function-based tests covering:

- **SessionState dataclass:** frozen verification, field storage
- **Registration in new_session():** discovery called, state cached, tier recorded, Tier 2/3 fallback, graceful failure
- **prompt() uses cached state:** no re-discovery, multiple prompts = single discovery call
- **Lazy fallback:** unknown session_id triggers discovery, result cached for reuse
- **Legacy compatibility:** legacy agent path skips registration, still works
- **FakeClient tracking:** `discover_tools_calls` records calls correctly

Key assertion: `test_prompt_does_not_re_discover` — after `new_session()`, multiple `prompt()` calls should NOT call `discover_tools()` again.

### Task 8: Verify existing tests pass

Existing `test_discovery.py` tests call `prompt()` with arbitrary session_ids (without `new_session()`). These hit the lazy fallback path and should pass unchanged. Verify all ~143 existing tests still pass.

### Task 9: Update example

**New file:** `examples/10_session_registration.py`

Demonstrates session-scoped registration: tools discovered once in `new_session()`, reused across multiple `prompt()` calls.

### Task 10: Update roadmap and evolution docs

- Mark 4.2 complete in `agent-os/product/roadmap.md`
- Add Phase 4.2 section to `docs/research/evolution.md`

## Files Summary

| Action | File | Description |
|--------|------|-------------|
| Create | `src/punie/agent/session.py` | `SessionState` frozen dataclass |
| Create | `tests/test_session_registration.py` | ~16 new tests |
| Create | `examples/10_session_registration.py` | Working demo |
| Create | `agent-os/specs/2026-02-08-1400-session-registration/` | Spec docs (4 files) |
| Modify | `src/punie/agent/adapter.py` | `_sessions` dict, `_discover_and_build_toolset()`, wire `new_session()`, simplify `prompt()` |
| Modify | `src/punie/agent/__init__.py` | Export `SessionState` |
| Modify | `src/punie/testing/fakes.py` | Add `discover_tools_calls` tracking |
| Modify | `agent-os/product/roadmap.md` | Mark 4.2 complete |
| Modify | `docs/research/evolution.md` | Add Phase 4.2 narrative |

## Verification

1. Use `astral:ty` skill to check types
2. Use `astral:ruff` skill to check and fix linting
3. Run `uv run pytest tests/` to verify all tests pass
4. Review ty LSP diagnostics for any warnings
