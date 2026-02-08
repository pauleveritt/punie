# References: Session Registration

## Phase 4.1 Context

Phase 4.2 builds directly on Phase 4.1's dynamic tool discovery infrastructure:

### Key Phase 4.1 Components

1. **ToolCatalog and ToolDescriptor**
   - File: `src/punie/agent/discovery.py`
   - Frozen dataclasses representing discovered tool metadata
   - Phase 4.2 caches these in `SessionState.catalog`

2. **Three-Tier Discovery**
   - File: `src/punie/agent/adapter.py` (lines 240-274 in `prompt()`)
   - Tier 1: Full `discover_tools()` catalog
   - Tier 2: Fallback to `capabilities` (filesystem-only)
   - Tier 3: Default toolset
   - Phase 4.2 extracts this into `_discover_and_build_toolset()`

3. **Toolset Factories**
   - File: `src/punie/agent/toolset.py`
   - `create_toolset_from_catalog()`, `create_toolset_from_capabilities()`, `create_default_toolset()`
   - Phase 4.2 calls these once per session, caches result

4. **Client Protocol**
   - File: `src/punie/acp/interfaces.py`
   - `async def discover_tools(session_id: str, **kwargs) -> dict[str, Any]`
   - Phase 4.2 calls this in `new_session()`, not `prompt()`

### Phase 4.1 Spec

- Location: `agent-os/specs/2026-02-08-1030-dynamic-tool-discovery/`
- Plan: Full 12-task implementation plan
- Shape: Design decisions and rationale
- Standards: 7 applicable standards (protocol-first, frozen-dataclass, etc.)

## Relevant Phase 4.1 Code

### Discovery Block (To Be Extracted)

```python
# Current location: src/punie/agent/adapter.py, lines ~240-274
# Phase 4.2 extracts this into _discover_and_build_toolset()

if self._connection:
    discovery_result = await self._connection.discover_tools(
        session_id=session_id
    )
    catalog = parse_tool_catalog(discovery_result)
    if catalog and catalog.tools:
        toolset = create_toolset_from_catalog(
            catalog, self._connection
        )
        discovery_tier = 1
    elif self._connection.capabilities:
        toolset = create_toolset_from_capabilities(
            self._connection.capabilities, self._connection
        )
        catalog = None
        discovery_tier = 2
    else:
        toolset = create_default_toolset(self._connection)
        catalog = None
        discovery_tier = 3
else:
    # No connection fallback
    toolset = FunctionToolset[ACPDeps](...)
    catalog = None
    discovery_tier = 3
```

### new_session() Current Implementation

```python
# Current location: src/punie/agent/adapter.py
# Phase 4.2 adds discovery call here

async def new_session(self, session_id: str) -> None:
    """Start a new agent session."""
    if self._connection:
        await self._connection.new_session(session_id)
    # Phase 4.2 adds:
    # state = await self._discover_and_build_toolset(session_id)
    # self._sessions[session_id] = state
```

## Testing Infrastructure

### FakeClient

- File: `src/punie/testing/fakes.py`
- Already implements `discover_tools()` method
- Phase 4.2 adds `discover_tools_calls: list[str]` tracking
- Follows `fakes-over-mocks` standard

### Existing Discovery Tests

- File: `tests/test_discovery.py`
- ~14 tests covering three-tier discovery logic
- Call `prompt()` directly without `new_session()` — hit lazy fallback path
- Should pass unchanged after Phase 4.2

## Related Documentation

### Pydantic AI Agent

- Phase 4.2 caches `PydanticAgent[ACPDeps, str]` instances per session
- Agents are constructed with model, system_prompt, deps, retries
- Immutable — safe to reuse across multiple `prompt()` calls

### ACP Protocol

- Session IDs are strings, opaque to agent layer
- No built-in session lifecycle management in ACP itself
- Agent layer owns session state caching

## Backward Compatibility

Phase 4.2 maintains full backward compatibility via **lazy fallback**:

- Tests calling `prompt()` without `new_session()` still work
- Unknown session IDs trigger on-demand discovery
- Result is cached for reuse
- No breaking changes to public API
