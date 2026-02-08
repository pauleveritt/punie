# Shape: Dynamic Tool Discovery via ACP

## Problem Statement

Punie's mission is "PyCharm's existing machinery becomes the agent's tool runtime." Currently, the agent knows exactly 7 hardcoded tools at construction time. It has no way to discover IDE capabilities at runtime. This blocks the path to IDE-powered refactoring, linting, type checking, and code navigation tools.

## Current State

### Static Tool Pipeline
- `create_toolset()` in `toolset.py` returns a fixed set of 7 tools
- `create_pydantic_agent()` in `factory.py` wires these at agent construction
- `PunieAgent.initialize()` receives `client_capabilities` but ignores it
- No runtime discovery mechanism

### What Works
- File I/O tools (read_file, write_file, list_files)
- Terminal tools (run_command, get_shell_info)
- Git tools (git_status, git_add_commit)
- Static toolset is reliable and predictable

### What's Missing
- No way to discover IDE-provided tools
- No way to vary toolset per session
- `client_capabilities` is received but unused
- No path to IDE-powered tools (refactoring, linting, etc.)

## Desired End State

### Dynamic Discovery
- Agent calls `discover_tools()` on IDE connection
- IDE returns JSON catalog of available tools with schemas
- Agent builds Pydantic AI toolset from catalog
- Toolset varies per session based on IDE capabilities

### Three-Tier Fallback
1. **Catalog-based** — If `discover_tools()` succeeds, build from catalog
2. **Capability-based** — If no catalog, use `client_capabilities` flags
3. **Default** — If no capabilities, use all 7 static tools

### Protocol Extension
- `discover_tools()` is a first-class Client protocol method
- Returns `{"tools": [{"name": ..., "kind": ..., "parameters": ...}]}`
- IDE can advertise custom tools beyond the 7 static ones

## Key Design Decisions

### Decision 1: Protocol Method vs ext_method

**Options:**
- A: Use existing `ext_method("discover_tools")` pattern
- B: Add `discover_tools()` to Client protocol

**Chosen:** B — First-class protocol method

**Rationale:**
- Tool discovery is core functionality, not an extension
- Protocol is vendored, we can modify it
- Cleaner interface than `ext_method` generic dict passing
- Signals to IDE implementers that discovery is expected

### Decision 2: Schema Type Location

**Options:**
- A: Put ToolDescriptor/ToolCatalog in `acp/schema.py`
- B: Put them in `agent/discovery.py`
- C: Put them in `agent/toolset.py`

**Chosen:** B — New `agent/discovery.py` module

**Rationale:**
- Discovery is agent-layer concern, not protocol-layer
- Keeps `acp/schema.py` focused on upstream ACP types
- Gives discovery types a clear home
- Follows single-responsibility principle

### Decision 3: Frozen Dataclasses vs Pydantic

**Options:**
- A: Use Pydantic models (like ACP schema)
- B: Use frozen dataclasses

**Chosen:** B — Frozen dataclasses

**Rationale:**
- Matches `frozen-dataclass-services` standard
- Simpler than Pydantic for internal types
- No validation needed (already validated at protocol layer)
- Immutability enforced by frozen=True

### Decision 4: Per-Session Agent vs Shared Agent

**Options:**
- A: Construct Pydantic AI agent once, update tools dynamically
- B: Construct Pydantic AI agent per session with session-specific toolset

**Chosen:** B — Per-session agent construction

**Rationale:**
- Pydantic AI doesn't support dynamic tool updates
- Simpler to rebuild than to mutate
- Each session gets exactly the tools it needs
- Clearer lifecycle: session starts → discover → build agent

### Decision 5: Unknown Tool Handling

**Options:**
- A: Ignore tools not in the known set
- B: Create generic bridge functions for unknown tools
- C: Error if unknown tools appear

**Chosen:** B — Generic bridge functions

**Rationale:**
- Enables IDE to provide custom tools without agent changes
- Generic bridge uses `ext_method` to forward to IDE
- Forward-compatible with IDE innovation
- Follows open/closed principle

## Scope

### In Scope
- `discover_tools()` protocol method
- ToolDescriptor and ToolCatalog types
- `create_toolset_from_catalog()` factory
- `create_toolset_from_capabilities()` fallback
- Per-session Pydantic AI agent construction
- FakeClient discovery support
- Comprehensive tests
- Working example (09_dynamic_tool_discovery.py)

### Out of Scope
- Actual IDE-side tool implementations (PyCharm feature)
- Tool permission system (future: 4.2)
- Tool usage analytics (future: 4.3)
- Tool composition/chaining (future: 4.4)
- Tool versioning (not needed yet)

### Future Extensions
- **4.2:** Permission-aware tool execution
- **4.3:** Tool usage tracking and optimization
- **4.4:** Tool composition pipelines
- **4.5:** Tool marketplace/registry

## Risk Assessment

### Low Risk
- Protocol is vendored (safe to modify)
- Backward compatible (fallback to static tools)
- Tests guard against regressions

### Medium Risk
- IDE needs to implement `discover_tools()` (coordination needed)
- JSON Schema validation complexity (keep simple for v1)
- Generic tool bridge might be fragile (limit to simple cases)

### Mitigation
- Start with IDE returning empty catalog (graceful degradation)
- Use minimal JSON Schema (just type + description)
- Generic bridge logs clearly when used (debugging visibility)

## Success Metrics

### Implementation Complete
- [ ] All 11 tasks completed
- [ ] Type checking passes (astral:ty)
- [ ] Linting passes (astral:ruff)
- [ ] Tests pass with ≥80% coverage
- [ ] Example 09 demonstrates end-to-end discovery

### Integration Ready
- [ ] IDE can return empty catalog (no-op)
- [ ] IDE can return 7 static tools (parity)
- [ ] IDE can return custom tool (extensibility)
- [ ] Agent gracefully handles all three fallback tiers

### Documentation Complete
- [ ] Spec docs capture decisions and rationale
- [ ] Example shows catalog queries and toolset building
- [ ] Roadmap updated with 4.1 complete
