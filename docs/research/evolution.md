# Project Evolution

## Overview

Punie evolved from a simple wrapper around the python-acp-sdk pip package to a full-featured AI coding agent that
bridges Pydantic AI with PyCharm through the Agent Communication Protocol. The project progressed through 10
specification phases over 3 days (2026-02-07 to 2026-02-08), transforming from an external dependency to a vendored
protocol implementation with dual-protocol support (ACP stdio + HTTP), a complete Pydantic AI agent bridge, and 7
production-ready tools for IDE integration.

## From ACP SDK to Vendored Protocol (Phases 1-2)

### Phase 1: Project Foundation

Punie started with four foundational tasks:

1. **Project structure** matching existing patterns (svcs-di, tdom-svcs)
2. **Comprehensive examples** (10 examples: 01-09 + hello_world)
3. **Documentation research** on python-sdk and Pydantic AI
4. **Pytest setup** proving python-sdk works correctly

The project initially depended on the `agent-client-protocol` pip package as an external dependency.

### Phase 2: Test-Driven Refactoring

Phase 2 (completed 2026-02-07) transformed the project's relationship with the ACP SDK:

**2.1 Vendoring the SDK**

- Copied 29 files from `~/PycharmProjects/python-acp-sdk/src/acp/` to `src/punie/acp/`
- Version: approximately v0.7.1 (schema ref v0.10.5)
- Enabled future modifications for Pydantic AI integration
- Provided independence from upstream release schedule

**Modifications to vendored files:**

| File                   | Change                                                       | Reason                                    |
|------------------------|--------------------------------------------------------------|-------------------------------------------|
| `router.py:11`         | `from acp.utils` → `from .utils`                             | Fix absolute import for vendored location |
| `interfaces.py:3`      | Added `runtime_checkable` import                             | Enable isinstance() checks                |
| `interfaces.py:73,143` | Added `@runtime_checkable` to `Client` and `Agent` protocols | Enable protocol satisfaction tests        |
| `schema.py:1-5`        | Added vendoring provenance comment                           | Document source and policy                |

**2.2 Import Transition**

- Updated 12 files (~16 import lines): `acp` → `punie.acp`
- Removed `agent-client-protocol` pip dependency
- Added `pydantic>=2.0` as direct dependency (previously transitive)

**2.3 Test Refactoring**

Created `src/punie/testing/` package with reusable test infrastructure:

- `FakeAgent` — Configurable fake implementing ACP Agent protocol
- `FakeClient` — Configurable fake implementing ACP Client protocol
- `LoopbackServer` — In-process test helper

**Test organization transformation:**

| Before                         | After                             |
|--------------------------------|-----------------------------------|
| 1 file (`test_acp_sdk.py`)     | 5 focused modules by concern      |
| 7 tests                        | 65 tests (+58 new)                |
| Hardcoded fakes in test file   | Reusable `punie.testing` package  |
| No protocol satisfaction tests | Runtime isinstance() verification |

New test modules:

- `test_protocol_satisfaction.py` — Runtime protocol checks
- `test_schema.py` — ACP schema roundtrip
- `test_rpc.py` — Initialize and bidirectional communication
- `test_notifications.py` — Cancel and session updates
- `test_tool_calls.py` — Tool call lifecycle
- `test_concurrency.py` — Concurrent file reads
- `test_fakes.py` — 39 comprehensive fake tests (100% coverage on `punie.testing`)

**Results:**

- Test coverage: 76% → 82%
- Type safety: All examples pass ty checking
- Ruff: Cleaned 5 unused type: ignore directives
- Public API: Added exports to `src/punie/__init__.py`

## HTTP Dual-Protocol Server (Phase 3.1)

Completed 2026-02-07. Established foundation for parallel web interface alongside ACP stdio.

**Architecture:**

```text
asyncio.wait(FIRST_COMPLETED):
  - Task 1: run_acp() → run_agent() → conn.listen()
  - Task 2: run_http() → uvicorn.Server.serve()
```

**Technology choices:**

- Starlette — Matches Pydantic AI's ASGI patterns (`to_a2a()`, `to_ag_ui()`, `to_web()`)
- uvicorn — ASGI server for Starlette
- httpx — TestClient for unit tests

**New package:** `src/punie/http/`

- `types.py` — `HttpAppFactory` protocol
- `app.py` — `/health` and `/echo` endpoints
- `runner.py` — `run_dual()` function for concurrent operation

**Testing:**

- 6 unit tests using Starlette TestClient (no real server)
- 2 integration tests with subprocess spawning both protocols
- Verified ACP stdio works after HTTP disconnect

**Key insight:** ACP's `conn.listen()` yields on `await self._reader.readline()` — it doesn't monopolize the event loop,
so `asyncio.wait()` pattern works cleanly without modifying vendored code.

## Pydantic AI Agent Bridge (Phases 3.2-3.3)

### Phase 3.2: Minimal Transition (2026-02-07)

Introduced Pydantic AI as the internal agent engine with a three-layer architecture:

```text
ACP stdio → PunieAgent (adapter) → Pydantic AI Agent.run()
```

**New package:** `src/punie/agent/`

| Module       | Purpose                                                              |
|--------------|----------------------------------------------------------------------|
| `deps.py`    | `ACPDeps` frozen dataclass — dependency container for Pydantic AI    |
| `toolset.py` | `ACPToolset` — Pydantic AI toolset wrapping ACP Client methods       |
| `adapter.py` | `PunieAgent` — Adapter satisfying ACP Agent protocol                 |
| `factory.py` | `create_pydantic_agent()` — Agent factory with default configuration |

**ACPDeps structure:**

```python
@dataclass(frozen=True)
class ACPDeps:
    client_conn: Client  # ACP Client protocol reference
    session_id: str  # Current ACP session ID
    tracker: ToolCallTracker  # Tool call lifecycle manager
```

**Data flow:**

1. ACP stdio receives prompt
2. PunieAgent.prompt() constructs ACPDeps
3. Calls `pydantic_agent.run()` with user message
4. Pydantic AI runs LLM, may call tools
5. ACPToolset delegates tool execution to ACP Client
6. Results flow back through AgentMessageChunk notifications
7. Returns PromptResponse

**Phase 3.2 tool:** `read_file` (wraps `Client.read_text_file`)

**Testing:**

- 8 new unit tests in `tests/test_pydantic_agent.py`
- Updated test fixtures to use PunieAgent instead of MinimalAgent
- Session IDs changed from `"test-session-N"` to `"punie-session-N"`
- All 84 tests passing

### Phase 3.3: Complete Toolset (2026-02-08)

Added 6 remaining tools to complete ACP Client coverage:

**File operations:**

- `read_file` (from Phase 3.2)
- `write_file` — With permission flow via `Client.request_permission()`

**Terminal operations:**

- `run_command` — Compound tool (create → wait → get_output → release)
- `get_terminal_output`
- `release_terminal`
- `wait_for_terminal_exit`
- `kill_terminal`

**Permission flow:**

Tools that modify state (`write_file`, `run_command`) request user permission before execution:

```python
perm_response = await ctx.deps.client_conn.request_permission(...)
if not perm_response.allowed:
    return f"Permission denied: {perm_response.reason}"
```

**Tool call lifecycle:**

All tools use `ToolCallTracker` for visibility:

1. `ToolCallStart` → sent to IDE via `session_update()`
2. Tool executes
3. `ToolCallProgress` → sent to IDE with result
4. `tracker.forget()` in finally block

**FakeClient enhancements:**

Added in-memory terminal state via `FakeTerminal` dataclass:

```python
@dataclass
class FakeTerminal:
    terminal_id: str
    command: str
    output_lines: list[str]
    exit_code: int | None
    active: bool
```

**Testing:**

- 12 Pydantic agent tests (read, write, run, permissions)
- 5 FakeClient terminal tests
- 83 total tests passing

## Best Practices Adoption (Phase 3.4)

Completed 2026-02-08. Migrated from pre-v1 patterns to Pydantic AI v1 idioms.

### Agent Configuration

**Before:**

```python
agent = Agent[ACPDeps, str](
    model,
    system_prompt="You are Punie...",
)
```

**After:**

```python
PUNIE_INSTRUCTIONS = """
You are Punie, an AI coding assistant that works inside PyCharm.

You have access to the following capabilities:
- read_file: Read contents of files in the project
- write_file: Modify or create files (requires user permission)
- run_command: Execute shell commands (requires user permission)

Guidelines:
- Always explain what you're doing before using tools
- Request permission for destructive operations
- Show command output to help users understand results
"""

agent = Agent[ACPDeps, str](
    model,
    deps_type=ACPDeps,
    instructions=PUNIE_INSTRUCTIONS,
    model_settings=ModelSettings(temperature=0.0, max_tokens=4096),
    retries=3,
    output_retries=2,
    toolsets=[create_toolset()],
)
```

**Changes:**

| Pattern           | Before           | After                                             |
|-------------------|------------------|---------------------------------------------------|
| Prompt            | `system_prompt=` | `instructions=` (v1 idiom)                        |
| Configuration     | None             | `ModelSettings(temperature=0.0, max_tokens=4096)` |
| Retry policy      | Default          | `retries=3, output_retries=2`                     |
| Output validation | None             | Custom validator rejecting empty responses        |

### Output Validation

```python
@agent.output_validator
def validate_response(ctx: RunContext[ACPDeps], output: str) -> str:
    if not output or not output.strip():
        raise ModelRetry("Response was empty, please provide a substantive answer.")
    return output
```

### Tool Error Handling

**Tracked tools** (read_file, write_file, run_command):

```python
async def read_file(ctx: RunContext[ACPDeps], path: str) -> str:
    tool_call_id = f"read_{path}"
    start = ctx.deps.tracker.start(...)
    await ctx.deps.client_conn.session_update(ctx.deps.session_id, start)
    try:
        response = await ctx.deps.client_conn.read_text_file(...)
        progress = ctx.deps.tracker.progress(...)
        await ctx.deps.client_conn.session_update(ctx.deps.session_id, progress)
        return response.content
    except Exception as exc:
        raise ModelRetry(f"Failed to read {path}: {exc}") from exc
    finally:
        ctx.deps.tracker.forget(tool_call_id)
```

**Key patterns:**

- All 7 tools raise `ModelRetry` on errors (LLM retries with different parameters)
- `tracker.forget()` in finally blocks prevents leaked tool calls
- Permission denials return strings (LLM should know, not retry blindly)

### Adapter Error Handling

Wrapped `agent.run()` in try/except to prevent protocol-level crashes:

```python
try:
    result = await self._pydantic_agent.run(
        user_prompt=message_param["content"],
        deps=deps,
        usage_limits=self._usage_limits,
    )
except UsageLimitExceeded as exc:
    await client.session_update(session_id, text_block(f"Usage limit exceeded: {exc}"))
    return PromptResponse(stop_reason="end_turn")
except Exception as exc:
    logger.exception("Agent run failed")
    await client.session_update(session_id, text_block(f"Agent error: {exc}"))
    return PromptResponse(stop_reason="end_turn")
```

**New capability:** `usage_limits` parameter enables token/request control.

**Testing:**

- 8 new tests (factory config, output validation, adapter errors)
- 20 total agent tests
- 91 tests passing, 81% coverage

## Architecture Review Findings (2026-02-08)

A comprehensive architecture review identified areas for improvement:

### Code Quality Issues

1. **Duplicated tool lifecycle boilerplate** — 3 tracked tools repeat start/progress/forget pattern (context manager
   opportunity)
2. **Tests coupling to private attributes** — Tests access `._pydantic_agent`, `._usage_limits` (brittle)
3. **Missing dedicated tool function tests** — Tools only tested through agent integration
4. **Dead session state in adapter** — `_sessions` dict populated but never read

### Recommendations

**Phase 4 priorities:**

- Extract tool lifecycle to reusable context manager
- Add direct tool function tests (use FakeClient, don't spawn agent)
- Remove unused session tracking from adapter
- Make tests resilient to internal API changes

**Long-term:**

- Dynamic tool discovery via ACP (Phase 4.1)
- Web UI for multi-agent tracking (Phase 5)
- Performance benchmarking (Phase 6)
- Advanced features: free-threaded Python, parallel agents (Phase 7)

## Dynamic Tool Discovery (Phase 4.1)

Completed 2026-02-08. Transformed Punie from static 7-tool agent to dynamic IDE-capability-driven architecture.

### The Problem

**Mission statement:** "PyCharm's existing machinery — refactoring, linting, type checking, code navigation — becomes the agent's tool runtime."

**Reality:** Agent hardcoded exactly 7 tools at construction time, no way to discover IDE capabilities.

**Gap:** `initialize()` received `client_capabilities` but ignored them completely.

### The Solution: Three-Tier Discovery

```python
# Tier 1: Catalog-based (IDE advertises tools)
catalog = await conn.discover_tools(session_id)
toolset = create_toolset_from_catalog(catalog)

# Tier 2: Capability-based (fallback)
toolset = create_toolset_from_capabilities(client_capabilities)

# Tier 3: Default (backward compat)
toolset = create_toolset()  # All 7 static tools
```

### Protocol Extension

Added `discover_tools()` as first-class Client protocol method:

```python
# src/punie/acp/interfaces.py
class Client(Protocol):
    async def discover_tools(
        self, session_id: str, **kwargs: Any
    ) -> dict[str, Any]: ...
```

**Design choice:** Protocol method (not `ext_method`) signals this is core functionality. Returns raw dict to keep protocol layer schema-agnostic.

### Discovery Schema

**New module:** `src/punie/agent/discovery.py`

```python
@dataclass(frozen=True)
class ToolDescriptor:
    name: str                          # e.g. "read_file", "refactor_rename"
    kind: str                          # ToolKind: "read", "edit", "execute", etc.
    description: str                   # Human-readable for LLM
    parameters: dict[str, Any]         # JSON Schema for parameters
    requires_permission: bool = False  # Permission gate
    categories: tuple[str, ...] = ()   # e.g. ("file", "io"), ("refactoring",)

@dataclass(frozen=True)
class ToolCatalog:
    tools: tuple[ToolDescriptor, ...]  # Immutable sequence

    def by_name(self, name: str) -> ToolDescriptor | None: ...
    def by_kind(self, kind: str) -> tuple[ToolDescriptor, ...]: ...
    def by_category(self, category: str) -> tuple[ToolDescriptor, ...]: ...
```

**Key decisions:**
- Frozen dataclasses (per `frozen-dataclass-services` standard)
- Tuples for immutability
- Agent layer owns these types (protocol stays generic)

### Dynamic Toolset Factories

**Modified:** `src/punie/agent/toolset.py`

**Three factory functions:**

1. `create_toolset()` — All 7 static tools (backward compat, Tier 3)
2. `create_toolset_from_capabilities(caps)` — Build from capability flags (Tier 2)
3. `create_toolset_from_catalog(catalog)` — Build from discovery (Tier 1)

**Catalog factory logic:**
- Match known tools by name (read_file, write_file, etc.)
- For unknown tools, create generic bridge using `ext_method`
- Return `FunctionToolset[ACPDeps]` with matched tools only

**Unknown tool handling:**
```python
def create_generic_bridge(descriptor: ToolDescriptor):
    async def bridge(ctx: RunContext[ACPDeps], **kwargs: Any) -> Any:
        conn = ctx.deps.conn
        return await conn.ext_method(
            descriptor.name,
            session_id=ctx.deps.session_id,
            **kwargs
        )
    bridge.__name__ = descriptor.name
    bridge.__doc__ = descriptor.description
    return bridge
```

This enables IDE to provide custom tools (e.g., `refactor_rename`) without agent code changes.

### Session Lifecycle Integration

**Modified:** `src/punie/agent/adapter.py`

**Changes:**

1. Store `client_capabilities` and `client_info` during `initialize()`
2. Build session-specific toolset in `prompt()`:
   ```python
   if hasattr(self._conn, "discover_tools"):
       catalog_dict = await self._conn.discover_tools(session_id)
       catalog = parse_tool_catalog(catalog_dict)
       toolset = create_toolset_from_catalog(catalog)
   elif self._client_capabilities:
       toolset = create_toolset_from_capabilities(self._client_capabilities)
   else:
       toolset = create_toolset()
   ```
3. Construct Pydantic AI agent per-session with dynamic toolset
4. Clean up dead `_sessions` set (identified in arch review)

**Modified:** `src/punie/agent/factory.py`

- `create_pydantic_agent()` now accepts optional `toolset` parameter
- Enables per-session agent construction with session-specific tools

### Testing Infrastructure

**Modified:** `src/punie/testing/fakes.py`

Added to `FakeClient`:
```python
class FakeClient:
    tool_catalog: list[dict]  # Configurable tool descriptors
    capabilities: ClientCapabilities | None

    async def discover_tools(self, session_id, **kwargs) -> dict:
        return {"tools": self.tool_catalog}
```

**New tests:** `tests/test_discovery.py` (14 function-based tests)

1. Frozen dataclass verification (ToolDescriptor, ToolCatalog)
2. Catalog query methods (by_name, by_kind, by_category)
3. Toolset factories (known tools, unknown bridges, capabilities fallback)
4. Adapter integration (stores caps, uses discovery, fallback chain)
5. FakeClient protocol satisfaction

### Examples Update

**Modified:** `examples/09_dynamic_tool_discovery.py`

Converted from aspirational Tier 3 (future vision, commented out) to working Tier 1 (demonstrates actual functionality):

- Create `ToolDescriptor` and `ToolCatalog`
- Query catalog (by_name, by_kind, by_category)
- Build `FunctionToolset` from catalog
- Show all three fallback tiers

### Results

**Files created:**
- `src/punie/agent/discovery.py` — Discovery types
- `tests/test_discovery.py` — 14 comprehensive tests
- `agent-os/specs/2026-02-08-1030-dynamic-tool-discovery/` — Full spec docs

**Files modified:**
- `src/punie/acp/interfaces.py` — Protocol extension
- `src/punie/agent/adapter.py` — Capability storage, discovery wiring, dead code cleanup
- `src/punie/agent/toolset.py` — Dynamic factories
- `src/punie/agent/factory.py` — Optional toolset parameter
- `src/punie/testing/fakes.py` — Discovery support
- `examples/09_dynamic_tool_discovery.py` — Working demo

**Test results:**
- Total tests: 91 → 105 (+14)
- Coverage: ≥80% (verified)
- Type checking: astral:ty passes
- Linting: astral:ruff passes

**Architectural impact:**
- Agent is no longer limited to 7 hardcoded tools
- IDE can advertise custom capabilities (refactoring, linting, etc.)
- Per-session toolsets enable different tools for different contexts
- Generic bridge enables forward compatibility with IDE innovation
- `client_capabilities` now used (no longer ignored)

### Standards Applied

This phase followed 7 Agent OS standards:

1. **agent-verification** — astral:ty + astral:ruff before completion
2. **protocol-first-design** — `discover_tools()` added to Client protocol first
3. **frozen-dataclass-services** — ToolDescriptor, ToolCatalog are frozen
4. **protocol-satisfaction-test** — Verify FakeClient satisfies protocol
5. **fakes-over-mocks** — Extended FakeClient, no mock frameworks
6. **function-based-tests** — All 14 tests are functions, not classes
7. **sybil-doctest** — Docstring examples in ToolCatalog methods

Full spec documentation in `agent-os/specs/2026-02-08-1030-dynamic-tool-discovery/`

## Phase 4.2: Session Registration (2026-02-08)

### Context

Phase 4.1 implemented dynamic tool discovery, but discovery happened **on every `prompt()` call**. This caused:

- Redundant RPC calls to `discover_tools()` within the same session
- A new `PydanticAgent` constructed per prompt (wasteful — model, instructions, retries identical)
- No session-scoped caching of discovered tools

Phase 4.2 moves discovery from per-prompt to **session lifecycle** — tools are discovered once during `new_session()`, cached as immutable session state, and reused across all `prompt()` calls for that session.

### Implementation

**New Module: `src/punie/agent/session.py`**

```python
@dataclass(frozen=True)
class SessionState:
    """Immutable session-scoped cached state."""
    catalog: ToolCatalog | None  # None if Tier 2/3 fallback
    agent: PydanticAgent[ACPDeps, str]  # Configured agent
    discovery_tier: int  # 1=catalog, 2=capabilities, 3=default
```

**Adapter Changes: `src/punie/agent/adapter.py`**

1. Added `_sessions: dict[str, SessionState]` to store per-session state
2. Extracted `_discover_and_build_toolset(session_id)` helper method (from prompt())
3. Wired `new_session()` to call discovery and cache result
4. Simplified `prompt()` to use cached agent from `_sessions[session_id]`
5. Implemented lazy fallback for unknown session IDs (backward compatibility)

**Before (Phase 4.1):**
```python
async def prompt(...):
    # 35 lines of discovery logic here (Tier 1 → 2 → 3)
    pydantic_agent = create_pydantic_agent(...)
    result = await pydantic_agent.run(...)
```

**After (Phase 4.2):**
```python
async def new_session(...):
    state = await self._discover_and_build_toolset(session_id)
    self._sessions[session_id] = state

async def prompt(...):
    if session_id in self._sessions:
        pydantic_agent = self._sessions[session_id].agent
    else:
        # Lazy fallback for tests that skip new_session()
        state = await self._discover_and_build_toolset(session_id)
        self._sessions[session_id] = state
        pydantic_agent = state.agent
```

**Testing Infrastructure: `src/punie/testing/fakes.py`**

Added `discover_tools_calls: list[str]` to `FakeClient` to track which session_ids triggered discovery. This lets tests assert discovery happens exactly once per session.

### Performance Impact

**Before:** `prompt()` called 3 times → `discover_tools()` called 3 times
**After:** `new_session()` called once + `prompt()` called 3 times → `discover_tools()` called 1 time

The agent is now constructed once per session, not once per prompt.

### Backward Compatibility

**Lazy Fallback:** Tests calling `prompt()` without `new_session()` still work. Unknown session IDs trigger on-demand discovery and cache the result. No breaking changes.

**Legacy Agent Mode:** Tests passing a pre-constructed `PydanticAgent` to `PunieAgent.__init__()` skip registration entirely (preserves existing behavior).

### Test Coverage

**New Tests: `tests/test_session_registration.py` (16 tests)**

- SessionState dataclass (frozen verification, field storage)
- Registration in new_session() (discovery called, state cached, tier recorded)
- Tier 2/3 fallback in new_session()
- Graceful failure handling
- prompt() uses cached agent (no re-discovery)
- Multiple prompt() calls use single discovery
- Lazy fallback for unknown session IDs
- Legacy agent compatibility
- FakeClient tracking verification

**Test Suite:** 124 tests passing (107 → 124, +16 new tests, +1 example test)

### Example

**New Example: `examples/10_session_registration.py`**

Demonstrates:
- Tools discovered once in `new_session()`
- Multiple `prompt()` calls reuse cached agent
- Lazy fallback for sessions without `new_session()`
- Three-tier fallback behavior (Tier 1/2/3)

### Code Changes

| Action | File | Lines Changed |
|--------|------|---------------|
| Create | `src/punie/agent/session.py` | +50 (new module) |
| Modify | `src/punie/agent/adapter.py` | +70, -35 (extract helper, wire new_session, simplify prompt) |
| Modify | `src/punie/agent/__init__.py` | +2 (export SessionState) |
| Modify | `src/punie/testing/fakes.py` | +4 (add discover_tools_calls tracking) |
| Create | `tests/test_session_registration.py` | +400 (16 new tests) |
| Create | `examples/10_session_registration.py` | +170 (working demo) |

**Net Impact:** ~660 lines added, 35 lines removed

### Architecture Improvement

Before Phase 4.2, the adapter was **stateless** at the session level. After Phase 4.2, it's **stateful** with immutable session caches:

```text
PunieAgent (Adapter)
    _sessions: dict[str, SessionState]  # <-- New
        SessionState (frozen)
            catalog: ToolCatalog | None
            agent: PydanticAgent[ACPDeps, str]  # <-- Cached per session
            discovery_tier: int
```

This aligns with ACP's session semantics: once a session is created, its tool capabilities are fixed for the session lifetime.

### Standards Applied

This phase followed 5 Agent OS standards:

1. **frozen-dataclass-services** — SessionState is frozen
2. **function-based-tests** — All 16 tests are functions, not classes
3. **fakes-over-mocks** — Extended FakeClient tracking, no mock frameworks
4. **sybil-doctest** — Docstring examples in SessionState
5. **agent-verification** — astral:ty + astral:ruff before completion

Full spec documentation in `agent-os/specs/2026-02-08-1400-session-registration/`

### Design Deviations from Plan

**Removed `toolset` field from `SessionState`**

The initial plan included a `toolset` field in `SessionState`:

```python
# Original plan (not implemented)
@dataclass(frozen=True)
class SessionState:
    catalog: ToolCatalog | None
    toolset: FunctionToolset[ACPDeps]  # Redundant
    agent: PydanticAgent[ACPDeps, str]
    discovery_tier: int
```

**Design Improvement:** The `toolset` field was removed because it's already encapsulated within the `PydanticAgent`. The agent owns its toolset and there's no need to expose it separately in the session state. This simplifies the API and reduces coupling.

**Final implementation:**

```python
@dataclass(frozen=True)
class SessionState:
    catalog: ToolCatalog | None        # For observability
    agent: PydanticAgent[ACPDeps, str] # Contains toolset
    discovery_tier: int                # For logging
```

**Rationale:**
- **Single source of truth:** The agent is the authority on which tools are available
- **Encapsulation:** Toolset is an implementation detail of the agent
- **Simpler API:** Fewer fields to understand and maintain
- **No functional loss:** The toolset is still used (via the agent), just not exposed

This deviation aligns with the principle of **information hiding** — SessionState exposes only what callers need (the agent), not how it works internally (the toolset).

## Current Architecture Summary

### Three-Layer Bridge

```text
PyCharm (ACP Client)
    ↕ JSON-RPC over stdio
PunieAgent (Adapter)
    - Satisfies ACP Agent protocol (14 methods)
    - Constructs ACPDeps
    - Handles errors
    ↕
Pydantic AI Agent
    - LLM inference
    - Tool selection
    - Output validation
    ↕
ACPToolset
    - 7 tools wrapping ACP Client methods
    - Permission flow
    - Tool call tracking
    ↕ ACP Client protocol
PyCharm (execution)
```

### Package Structure

| Package         | Purpose                     | Key Modules                                         |
|-----------------|-----------------------------|-----------------------------------------------------|
| `punie.acp`     | Vendored ACP SDK (29 files) | `interfaces`, `core`, `schema`, `agent/`, `client/` |
| `punie.agent`   | Pydantic AI bridge          | `adapter`, `toolset`, `deps`, `factory`             |
| `punie.http`    | HTTP server                 | `app`, `runner`, `types`                            |
| `punie.testing` | Test infrastructure         | `fakes`, `server`                                   |

### Test Statistics

- **Total tests:** 124
- **Coverage:** 81% (exceeds 80% requirement)
- **Test distribution:**
    - Protocol satisfaction: 2
    - Schema/RPC: 8
    - Tool calls/concurrency: 8
    - Fakes: 39
    - Pydantic agent: 20
    - Discovery: 16
    - Session registration: 16
    - HTTP: 6
    - Dual protocol: 2
    - Examples: 10 (including 10_session_registration)

### Tool Coverage

| Tool                     | ACP Client Method                                                                  | Permission Required |
|--------------------------|------------------------------------------------------------------------------------|---------------------|
| `read_file`              | `read_text_file`                                                                   | No                  |
| `write_file`             | `write_text_file`                                                                  | Yes                 |
| `run_command`            | `create_terminal`, `wait_for_terminal_exit`, `terminal_output`, `release_terminal` | Yes                 |
| `get_terminal_output`    | `terminal_output`                                                                  | No                  |
| `release_terminal`       | `release_terminal`                                                                 | No                  |
| `wait_for_terminal_exit` | `wait_for_terminal_exit`                                                           | No                  |
| `kill_terminal`          | `kill_terminal`                                                                    | No                  |

## New Dependencies

| Dependency                | Added     | Purpose                                                         |
|---------------------------|-----------|-----------------------------------------------------------------|
| `pydantic>=2.0`           | Phase 2.2 | Previously transitive through agent-client-protocol, now direct |
| `pydantic-ai-slim>=0.1.0` | Phase 3.2 | Agent framework with type-safe tools and DI                     |
| `starlette>=0.45.0`       | Phase 3.1 | ASGI web framework for HTTP server                              |
| `uvicorn>=0.34.0`         | Phase 3.1 | ASGI server for Starlette                                       |
| `httpx>=0.28.0` (dev)     | Phase 3.1 | TestClient for HTTP unit tests                                  |

**Removed:** `agent-client-protocol>=0.7.1` (Phase 2.2, replaced by vendored code)

## Timeline

| Date       | Phases  | Description                                                                                  |
|------------|---------|----------------------------------------------------------------------------------------------|
| 2026-02-07 | 1.1-1.4 | Project foundation (structure, examples, docs, pytest)                                       |
| 2026-02-07 | 2.1-2.4 | Vendor SDK, refactor tests, create `punie.testing` package                                   |
| 2026-02-07 | 3.1     | Add HTTP server alongside ACP (dual-protocol)                                                |
| 2026-02-07 | 3.2     | Pydantic AI bridge with ACPDeps and first tool (read_file)                                   |
| 2026-02-08 | 3.3     | Complete toolset (7 tools, permission flow, terminal support)                                |
| 2026-02-08 | 3.4     | Adopt Pydantic AI v1 best practices (instructions, ModelRetry, output validation)            |
| 2026-02-08 | Review  | Architecture review identifying next improvements                                            |
| 2026-02-08 | 4.1     | Dynamic tool discovery (protocol extension, catalog schema, three-tier fallback, 14 tests)   |
| 2026-02-08 | 4.2     | Session registration (tool caching, lazy fallback, SessionState frozen dataclass, 16 tests)  |
