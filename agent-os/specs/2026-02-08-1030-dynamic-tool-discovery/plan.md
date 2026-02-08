# Plan: Dynamic Tool Discovery via ACP (Roadmap 4.1)

## Context

The current tool pipeline is fully static — `create_toolset()` in `src/punie/agent/toolset.py` hardcodes 7 tools, `create_pydantic_agent()` in `factory.py` wires them at construction time, and `PunieAgent.initialize()` in `adapter.py` ignores `client_capabilities` entirely. The mission says "PyCharm's existing machinery — refactoring, linting, type checking, code navigation — becomes the agent's tool runtime." To get there, the agent must discover what the IDE can do at runtime rather than assuming a fixed set.

**Scope:** Full dynamic protocol — extend the vendored ACP protocol with a first-class `discover_tools()` method. Support IDE-provided tool descriptors with JSON Schema, and build Pydantic AI toolsets dynamically from the catalog.

**Branch:** `feature/4.1-dynamic-tool-discovery` (already created)

## Key Design Decisions

1. **New protocol method, not ext_method** — Add `discover_tools()` to the Client protocol in `interfaces.py`. This is a first-class capability, not an extension hack. The SDK is vendored so we can modify it.
2. **New schema types** — `ToolDescriptor` (frozen dataclass: name, kind, description, parameter JSON Schema, requires_permission, categories) and `ToolCatalog` (frozen dataclass: list of ToolDescriptors).
3. **Capability-aware + catalog-aware** — Store `ClientCapabilities` during `initialize()`, call `discover_tools()` during `new_session()`, build toolset from the intersection.
4. **Dynamic toolset factory** — `create_toolset(catalog: ToolCatalog)` replaces the static `create_toolset()`. Known tools (read_file, write_file, etc.) match by name; unknown tools use a generic `call_ide_tool()` bridge.
5. **Per-session Pydantic AI agent** — Since tools vary by session, the Pydantic AI agent is constructed per-session in `new_session()` or `prompt()`, not at PunieAgent construction time.
6. **Backward compatible** — If `discover_tools()` returns empty or the client doesn't support it, fall back to capability-flag-based toolset (current behavior minus the hardcoding).

## Tasks

### Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-08-1030-dynamic-tool-discovery/` with:
- **plan.md** — This full plan
- **shape.md** — Shaping notes (scope, decisions, context)
- **standards.md** — All 7 applicable standards (agent-verification, protocol-first-design, frozen-dataclass-services, protocol-satisfaction-test, fakes-over-mocks, function-based-tests, sybil-doctest)
- **references.md** — Pointers to reference implementations

### Task 2: Add Discovery Schema Types

**Create:** `src/punie/agent/discovery.py` — New module for discovery types

```python
@dataclass(frozen=True)
class ToolDescriptor:
    name: str                          # e.g. "read_file", "refactor_rename"
    kind: str                          # ToolKind value: "read", "edit", "execute", etc.
    description: str                   # Human-readable description for LLM
    parameters: dict[str, Any]         # JSON Schema for tool parameters
    requires_permission: bool = False  # Whether tool needs user permission
    categories: tuple[str, ...] = ()   # e.g. ("file", "io"), ("refactoring",)

@dataclass(frozen=True)
class ToolCatalog:
    tools: tuple[ToolDescriptor, ...]  # Immutable sequence of available tools

    def by_name(self, name: str) -> ToolDescriptor | None: ...
    def by_kind(self, kind: str) -> tuple[ToolDescriptor, ...]: ...
    def by_category(self, category: str) -> tuple[ToolDescriptor, ...]: ...
```

Use frozen dataclasses per `frozen-dataclass-services` standard. Tuples instead of lists for immutability.

### Task 3: Add `discover_tools()` to Client Protocol

**Modify:** `src/punie/acp/interfaces.py`

Add to Client protocol:
```python
async def discover_tools(
    self, session_id: str, **kwargs: Any
) -> dict[str, Any]: ...
```

Returns a dict (raw JSON) that gets parsed into `ToolCatalog` by the agent layer. This keeps the protocol layer schema-agnostic while the agent layer owns the typed model.

**Note:** No `@param_model` decorator needed since this is a Punie extension, not an upstream ACP method. We keep the raw dict return to avoid coupling protocol to agent types.

### Task 4: Store ClientCapabilities in PunieAgent

**Modify:** `src/punie/agent/adapter.py`

In `PunieAgent.initialize()`:
- Store `client_capabilities` and `client_info` on `self`
- Use stored capabilities in later methods

```python
async def initialize(self, protocol_version, client_capabilities=None, client_info=None, **kwargs):
    self._client_capabilities = client_capabilities
    self._client_info = client_info
    # ... existing response
```

### Task 5: Build Dynamic Toolset Factory

**Modify:** `src/punie/agent/toolset.py`

Add `create_toolset_from_catalog(catalog: ToolCatalog) -> FunctionToolset[ACPDeps]`:
- For each `ToolDescriptor` in catalog, match by name to known tool functions (read_file, write_file, etc.)
- For unrecognized tools, generate a generic bridge function using `ext_method`
- Return `FunctionToolset` with only the matched tools

Add `create_toolset_from_capabilities(caps: ClientCapabilities) -> FunctionToolset[ACPDeps]`:
- Fallback when `discover_tools()` is unavailable
- Include read_file if `caps.fs.read_text_file`
- Include write_file if `caps.fs.write_text_file`
- Include terminal tools if `caps.terminal`

Keep existing `create_toolset()` as the "all tools" default for backward compat.

### Task 6: Wire Discovery into Session Lifecycle

**Modify:** `src/punie/agent/adapter.py`

In `PunieAgent.prompt()` (or a new helper):
1. If `self._conn` supports `discover_tools()`, call it and parse into `ToolCatalog`
2. Else if `self._client_capabilities` is set, use `create_toolset_from_capabilities()`
3. Else fall back to `create_toolset()` (current behavior)
4. Construct Pydantic AI agent with the session-specific toolset

**Modify:** `src/punie/agent/factory.py`

Change `create_pydantic_agent()` to accept an optional `toolset` parameter instead of always calling `create_toolset()`.

### Task 7: Update FakeClient for Discovery

**Modify:** `src/punie/testing/fakes.py`

Add to `FakeClient`:
- `tool_catalog: list[dict]` — configurable tool descriptors
- `async def discover_tools(self, session_id, **kwargs) -> dict` — returns configured catalog
- Constructor parameter: `capabilities: ClientCapabilities | None = None`

### Task 8: Write Tests

**Create:** `tests/test_discovery.py`

Tests (function-based, protocol-satisfaction):

1. `test_tool_descriptor_is_frozen()` — frozen dataclass verification
2. `test_tool_catalog_is_frozen()` — frozen dataclass verification
3. `test_tool_catalog_by_name()` — lookup by name
4. `test_tool_catalog_by_kind()` — filter by kind
5. `test_tool_catalog_by_category()` — filter by category
6. `test_create_toolset_from_catalog_known_tools()` — known tools matched
7. `test_create_toolset_from_catalog_unknown_tools()` — generic bridge for unknowns
8. `test_create_toolset_from_capabilities_fs_only()` — only file tools when terminal=False
9. `test_create_toolset_from_capabilities_all()` — all tools when everything enabled
10. `test_adapter_stores_client_capabilities()` — initialize stores caps
11. `test_adapter_uses_discovery_when_available()` — prompt uses catalog
12. `test_adapter_falls_back_to_capabilities()` — prompt uses caps when no discovery
13. `test_adapter_falls_back_to_defaults()` — prompt uses all tools when no caps
14. `test_fake_client_discover_tools()` — FakeClient returns configured catalog

### Task 9: Update Example 09

**Modify:** `examples/09_dynamic_tool_discovery.py`

Convert from aspirational Tier 3 to working Tier 1:
- Demonstrate creating `ToolDescriptor` and `ToolCatalog`
- Show catalog queries (by_name, by_kind, by_category)
- Show `create_toolset_from_catalog()` producing a Pydantic AI toolset
- Remove commented-out aspirational code

### Task 10: Clean Up Dead Code

**Modify:** `src/punie/agent/adapter.py`
- Remove unused `_sessions` set (identified in architecture review)

### Task 11: Verification and Roadmap Update

1. Use `astral:ty` skill — no type errors on new code
2. Use `astral:ruff` skill — no lint issues
3. `uv run pytest` — all tests pass (existing + new)
4. Coverage ≥ 80%
5. Update `agent-os/product/roadmap.md` — mark 4.1 complete

## Files Summary

| Action | Files |
|--------|-------|
| **Create (spec)** | `agent-os/specs/2026-02-08-1030-dynamic-tool-discovery/{plan,shape,standards,references}.md` |
| **Create** | `src/punie/agent/discovery.py` |
| **Create** | `tests/test_discovery.py` |
| **Modify** | `src/punie/acp/interfaces.py` — add `discover_tools()` to Client |
| **Modify** | `src/punie/agent/adapter.py` — store capabilities, wire discovery, remove dead `_sessions` |
| **Modify** | `src/punie/agent/toolset.py` — add `create_toolset_from_catalog()`, `create_toolset_from_capabilities()` |
| **Modify** | `src/punie/agent/factory.py` — accept optional toolset parameter |
| **Modify** | `src/punie/agent/__init__.py` — export new types |
| **Modify** | `src/punie/testing/fakes.py` — FakeClient discovery support |
| **Modify** | `examples/09_dynamic_tool_discovery.py` — Tier 3 → Tier 1 |
| **Modify** | `agent-os/product/roadmap.md` — mark 4.1 complete |

## Critical Files to Reference

| File | Why |
|------|-----|
| `src/punie/acp/interfaces.py` | Client protocol — adding discover_tools() |
| `src/punie/agent/toolset.py` | Current static toolset — adding dynamic factories |
| `src/punie/agent/adapter.py` | PunieAgent — wiring discovery into lifecycle |
| `src/punie/agent/factory.py` | Agent factory — accepting optional toolset |
| `src/punie/agent/deps.py` | ACPDeps — may need catalog reference |
| `src/punie/testing/fakes.py` | FakeClient — adding discovery support |
| `examples/09_dynamic_tool_discovery.py` | Aspirational → working |
| `src/punie/acp/schema.py:19` | ToolKind Literal type |
| `src/punie/acp/schema.py:183` | FileSystemCapability |
| `src/punie/acp/schema.py:1080` | ClientCapabilities |
