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

## Phase 5.1: CLI Development (2026-02-08)

### Context

Punie had no CLI entry point — no `[project.scripts]`, no `__main__.py`. The only way to run the agent was programmatically via test fixtures (`tests/fixtures/minimal_agent.py`). PyCharm needs to launch Punie as a subprocess via `acp.json`, which requires a `punie` command that starts the ACP stdio agent.

Phase 5.1 adds a Typer-based CLI with a critical constraint: **stdout is reserved for ACP JSON-RPC.** The ACP stdio transport writes raw bytes to `sys.stdout.buffer` (see `src/punie/acp/stdio.py`). Any logging or output to stdout corrupts the protocol. All logging MUST go to files only. Even `--version` must write to stderr.

### Implementation

**New Module: `src/punie/cli.py`**

Structure:
- `app = typer.Typer()` — The Typer app instance (also the entry point)
- `resolve_model(model_flag) -> str` — Pure function: CLI flag > `PUNIE_MODEL` env var > `"test"` default
- `setup_logging(log_dir, log_level)` — Pure function: configures `RotatingFileHandler` to `~/.punie/logs/punie.log`, never touches stdout
- `run_acp_agent(model, name)` — Async function: creates `PunieAgent(model=model, name=name)`, calls `run_agent(agent)` from `punie.acp`
- `main()` — Typer callback (`@app.callback(invoke_without_command=True)`): parses flags, calls `setup_logging()`, calls `asyncio.run(run_acp_agent(...))`

**CLI Flags:**
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--model` | `str \| None` | None (resolves via env/default) | Model name, overrides PUNIE_MODEL env var |
| `--name` | `str` | `"punie-agent"` | Agent name for identification |
| `--log-dir` | `Path` | `~/.punie/logs/` | Directory for log files |
| `--log-level` | `str` | `"info"` | Logging level |
| `--version` | `bool` | False | Print version to **stderr** and exit |

**Logging Strategy:**
- `RotatingFileHandler` with 10MB max, 3 backups
- Stderr handler at CRITICAL level only (for startup failures)
- **No stdout handler** — ACP requires exclusive stdout access

**Version Flag:**
```python
if version:
    typer.echo(f"punie {__version__}", err=True)  # stderr, not stdout
    raise typer.Exit(0)
```

**Entry Point: `pyproject.toml`**

```toml
[project.scripts]
punie = "punie.cli:app"
```

Points to the Typer app instance, not a function. Typer's runtime handles invocation.

**Python Module Support: `src/punie/__main__.py`**

```python
"""Support for `python -m punie` invocation."""
from punie.cli import app
app()
```

Enables `python -m punie` alongside `punie` script.

**Modern Agent Construction:**

```python
agent = PunieAgent(model=model, name=name)  # Not PydanticAgent(agent=...)
await run_agent(agent)
```

Uses the modern constructor from Phase 3.4, not the legacy `PydanticAgent` wrapping.

### Test Coverage

**New Tests: `tests/test_cli.py` (10 function-based tests)**

**Pure function tests (no Typer, no async):**
- `test_resolve_model_flag_takes_priority` — CLI flag wins
- `test_resolve_model_env_var_fallback` — PUNIE_MODEL env var used when no flag
- `test_resolve_model_default` — returns "test" when nothing set
- `test_setup_logging_creates_directory` — creates log_dir and punie.log
- `test_setup_logging_configures_file_handler` — root logger gets RotatingFileHandler
- `test_setup_logging_no_stdout_handler` — no handler points to stdout
- `test_setup_logging_sets_level` — root logger level matches config
- `test_setup_logging_expands_user_path` — tilde paths are expanded

**Typer CliRunner tests:**
- `test_cli_version` — `--version` prints version to stderr, exits 0
- `test_cli_help` — `--help` shows help text

**Fixture:** `clean_root_logger` — removes all handlers after tests that call `setup_logging()` to prevent leaks.

**Test Suite:** 144 tests passing (134 existing + 10 new CLI tests)

### Example

**New Example: `examples/11_cli_usage.py`**

Demonstrates `resolve_model()` and `setup_logging()` programmatically. Shows model resolution order and logging setup. Can be used outside the CLI context.

### Verification

```bash
# Python module invocation
uv run python -m punie --version
# Output to stderr: punie 0.1.0

# Script entry point
uv run punie --version
# Output to stderr: punie 0.1.0

# Help text
uv run punie --help
# Shows all flags with descriptions

# uvx invocation (future)
uvx punie --version
# Works once published to PyPI
```

### Code Changes

| Action | File | Lines |
|--------|------|-------|
| Create | `src/punie/cli.py` | +137 (CLI module) |
| Create | `src/punie/__main__.py` | +5 (python -m support) |
| Create | `tests/test_cli.py` | +120 (10 tests) |
| Create | `examples/11_cli_usage.py` | +50 (CLI demo) |
| Create | `agent-os/specs/2026-02-08-cli-development/` | +800 (4 spec docs) |
| Modify | `pyproject.toml` | +4 (typer dep, entry point) |

**Net Impact:** ~1116 lines added

### Architecture Impact

**Before Phase 5.1:**
- No CLI entry point
- Agent only usable programmatically in tests
- PyCharm couldn't launch Punie via `acp.json`

**After Phase 5.1:**
- `punie` command available as subprocess
- `python -m punie` works
- `uvx punie` works (after PyPI publish)
- All logging goes to files (stdout preserved for ACP)
- PyCharm can launch Punie via `acp.json` (Phase 5.2)

### Key Design Decisions

**1. Pure Functions First**

Separated pure logic (`resolve_model()`, return value) from side effects (`setup_logging()`, I/O). Makes code testable without mocking async/IO.

**2. File-Only Logging**

No stdout handler. ACP stdio transport owns `sys.stdout.buffer`. Any other output corrupts JSON-RPC messages.

**3. Version to stderr**

```python
typer.echo(f"punie {__version__}", err=True)  # Not stdout
```

**4. Entry Point Points to App**

```toml
punie = "punie.cli:app"  # Typer app instance, not main() function
```

Idiomatic Typer pattern. Enables future subcommands (`punie init`, `punie serve`).

**5. `@app.callback(invoke_without_command=True)`**

Makes bare `punie` run the ACP agent. Future phases add subcommands:
- Phase 5.2: `punie init` (config generation)
- Phase 5.3: `punie tools list` (tool discovery)
- Phase 5.4: `punie serve` (HTTP + ACP dual server)

### Standards Applied

This phase followed 5 Agent OS standards:

1. **function-based-tests** — All 10 tests are functions, not classes
2. **agent-verification** — astral:ty + astral:ruff before completion
3. **sybil-doctest** — Docstring examples in resolve_model()
4. **no-rich-yet** — Avoided Rich dependency (waits for Phase 5.2 where stdout available)
5. **single-source-version** — `__version__` in `__init__.py`, imported by CLI

Full spec documentation in `agent-os/specs/2026-02-08-cli-development/`

### Future Phases

**Phase 5.2: Configuration Management**
- `punie init` — create `~/.punie/config.toml`
- `punie status` — show config/logs (can use stdout, Rich enabled)
- Config file parsing

**Phase 5.3: IDE Tool Integration**
- Dynamic tool discovery via filesystem
- `punie tools list` command

## Phase 5.2: Config Generation (2026-02-08)

### Context

PyCharm discovers agents via `~/.jetbrains/acp.json` configuration file. Phase 5.1 added `punie` command but no way to generate the discovery config. Users would need to manually create JSON with correct Punie executable path and environment settings.

Phase 5.2 adds `punie init` subcommand to generate acp.json automatically, with intelligent executable detection (system PATH vs uvx fallback) and config merging to preserve other agents.

### Key Insight

**Subcommands can write to stdout freely** — unlike bare `punie` which reserves stdout for ACP JSON-RPC, `punie init` is a normal CLI command that generates files and prints user-facing messages.

### Implementation

**Pure Functions (Testable):**

```python
def resolve_punie_command() -> tuple[str, list[str]]:
    """Detect how to invoke Punie executable."""
    punie_path = shutil.which("punie")
    if punie_path:
        return (punie_path, [])
    return ("uvx", ["punie"])

def generate_acp_config(command: str, args: list[str], env: dict[str, str]) -> dict:
    """Generate JetBrains ACP configuration for Punie."""
    return {
        "default_mcp_settings": {
            "use_idea_mcp": True,
            "use_custom_mcp": True,
        },
        "agent_servers": {
            "punie": {"command": command, "args": args, "env": env}
        },
    }

def merge_acp_config(existing: dict, punie_config: dict) -> dict:
    """Merge Punie config into existing ACP config."""
    # Preserves other agents, does not mutate inputs
    ...
```

**Typer Command:**

```python
@app.command()
def init(
    model: str | None = typer.Option(None, "--model", ...),
    output: Path = typer.Option(Path.home() / ".jetbrains" / "acp.json", "--output", ...),
) -> None:
    """Generate JetBrains ACP configuration for Punie."""
    command, args = resolve_punie_command()
    env = {"PUNIE_MODEL": model} if model else {}
    punie_config = generate_acp_config(command, args, env)

    # Merge with existing if present
    if output.exists():
        existing = json.loads(output.read_text())
        final_config = merge_acp_config(existing, punie_config)
    else:
        final_config = punie_config

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(final_config, indent=2) + "\n")

    typer.secho(f"✓ Created {output}", fg=typer.colors.GREEN)
```

### Generated Config Format

```json
{
  "default_mcp_settings": {
    "use_idea_mcp": true,
    "use_custom_mcp": true
  },
  "agent_servers": {
    "punie": {
      "command": "/usr/local/bin/punie",
      "args": [],
      "env": {"PUNIE_MODEL": "claude-sonnet-4-5-20250929"}
    }
  }
}
```

### Test Coverage

**New Tests: 13 tests in `tests/test_cli.py`**

**Pure function tests (9):**
- `test_resolve_punie_command_finds_executable` — shutil.which returns path
- `test_resolve_punie_command_uvx_fallback` — not on PATH, uses uvx
- `test_generate_acp_config_basic` — structure correct
- `test_generate_acp_config_with_env` — PUNIE_MODEL in env
- `test_generate_acp_config_uvx_args` — uvx invocation
- `test_merge_acp_config_preserves_other_agents` — other agents kept
- `test_merge_acp_config_updates_existing_punie` — punie entry updated
- `test_merge_acp_config_adds_missing_defaults` — adds default_mcp_settings
- `test_merge_does_not_mutate_original` — no mutation of input

**CLI integration tests (4):**
- `test_cli_init_creates_file` — writes acp.json
- `test_cli_init_with_model` — --model sets env
- `test_cli_init_merges_existing` — merges into existing file
- `test_cli_init_help` — shows init help text

**Test Suite:** 157 tests passing (144 existing + 13 new init tests)

### Example

**New Example: `examples/12_init_config.py`**

Demonstrates `resolve_punie_command()` and `generate_acp_config()` programmatically:
- Detecting Punie executable
- Generating basic config
- Config with model pre-set

### Usage

```bash
# Generate default config
uv run punie init

# With model flag
uv run punie init --model claude-opus-4

# Custom output path
uv run punie init --output /tmp/acp.json

# Help text
uv run punie init --help

# Main help shows subcommands
uv run punie --help
```

### Code Changes

| Action | File | Lines |
|--------|------|-------|
| Create | `agent-os/specs/2026-02-08-init-command/` | +800 (4 spec docs) |
| Modify | `src/punie/cli.py` | +80 (3 pure functions + 1 command) |
| Modify | `tests/test_cli.py` | +150 (13 tests) |
| Create | `examples/12_init_config.py` | +35 (config demo) |

**Net Impact:** ~1065 lines added

### Architecture Impact

**Before Phase 5.2:**
- Users manually create acp.json
- Error-prone executable path configuration
- Overwrites existing configs accidentally

**After Phase 5.2:**
- `punie init` generates valid config
- Auto-detects system vs uvx installation
- Preserves other agents when merging
- Optional --model flag for convenience

### Design Decisions

**1. Pure Functions First**

Separated business logic (resolve, generate, merge) from I/O (read/write files). Makes code testable without temp files in most tests.

**2. Intelligent Executable Detection**

```python
shutil.which("punie") → "/usr/local/bin/punie"  # System install
shutil.which("punie") → None → ("uvx", ["punie"])  # uvx fallback
```

**3. Config Merging, Not Overwriting**

```python
existing = {"agent_servers": {"other": {...}}}
merged = merge_acp_config(existing, punie_config)
# Result: both "other" and "punie" present
```

**4. No Mutation**

```python
merged = copy.deepcopy(existing)  # New dict, inputs unchanged
```

### Standards Applied

This phase followed 4 Agent OS standards:

1. **function-based-tests** — All 13 tests are functions, not classes
2. **agent-verification** — astral:ty + astral:ruff before completion
3. **pure-functions-first** — Business logic testable without I/O
4. **no-mutation** — merge_acp_config does not mutate inputs

Full spec documentation in `agent-os/specs/2026-02-08-init-command/`

## Phase 5.4: Dual-Protocol Serve (2026-02-08)

### Context

Phase 3.1 added HTTP server alongside ACP stdio with `run_dual()` infrastructure. Phase 5.1 added CLI with bare `punie` running stdio only. But there was no way to run dual-protocol mode from CLI — users had to write their own scripts.

Phase 5.4 adds `punie serve` subcommand to wrap existing `run_dual()` infrastructure, enabling HTTP + ACP stdio concurrently from command line.

**Note:** Phase 5.3 (model download) **skipped/deferred** — local model strategy TBD.

### Key Insight

**Subcommands can write to stdout freely** — unlike bare `punie` which reserves stdout for ACP JSON-RPC, `punie serve` can print startup messages before the agent starts.

### Implementation

**Async Helper (Separation of Concerns):**

```python
async def run_serve_agent(
    model: str,
    name: str,
    host: str,
    port: int,
    log_level: str,
) -> None:
    """Create agent and run dual-protocol mode."""
    agent = PunieAgent(model=model, name=name)
    app_instance = create_app()
    await run_dual(agent, app_instance, Host(host), Port(port), log_level)
```

**Why separate?** Typer commands must be sync (no `async def`). Extracting async logic into helper function allows testing without CliRunner complexity.

**Typer Command:**

```python
@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", ...),
    port: int = typer.Option(8000, "--port", ...),
    model: str | None = typer.Option(None, "--model", ...),
    name: str = typer.Option("punie-agent", "--name", ...),
    log_dir: Path = typer.Option(Path("~/.punie/logs"), "--log-dir", ...),
    log_level: str = typer.Option("info", "--log-level", ...),
) -> None:
    """Run Punie agent with dual protocol support."""
    setup_logging(log_dir, log_level)
    resolved_model = resolve_model(model)

    # Startup message (OK for serve command before agent starts)
    typer.echo("Starting Punie agent (dual protocol mode)")
    typer.echo(f"  Model: {resolved_model}")
    typer.echo(f"  HTTP: http://{host}:{port}")
    typer.echo(f"  Logs: {log_dir.expanduser() / 'punie.log'}")

    asyncio.run(run_serve_agent(resolved_model, name, host, port, log_level))
```

### Reused Infrastructure (No Changes)

**From existing modules:**
- `PunieAgent(model, name)` — agent adapter (Phase 3.2)
- `create_app()` — Starlette app factory (Phase 3.1)
- `run_dual(agent, app, host, port, log_level)` — concurrent stdio + HTTP (Phase 3.1)
- `Host`, `Port` — NewType wrappers (Phase 3.1)

**No new dependencies** — pure wiring of existing infrastructure.

### Test Coverage

**New Tests: 6 tests in `tests/test_cli.py`**

**Async helper test (1):**
- `test_run_serve_agent_creates_agent` — async test with monkeypatch verifying agent creation and run_dual call

**CLI integration tests (5):**
- `test_cli_serve_help` — shows serve-specific flags
- `test_cli_help_shows_subcommands` — main help lists init and serve
- `test_serve_sets_up_logging` — logging configured before agent starts
- `test_serve_resolves_model` — model resolution chain works
- `test_serve_model_flag_overrides_env` — --model takes priority

**Test Suite:** 163 tests passing (157 existing + 6 new serve tests)

### Example

**New Example: `examples/13_serve_dual.py`**

Demonstrates dual-protocol setup programmatically:
- Creating agent and HTTP app
- Showing dual-protocol architecture (stdio + HTTP)
- Endpoints available (/health, /echo)

### Usage

```bash
# Basic serve
uv run punie serve

# Custom host/port
uv run punie serve --host 0.0.0.0 --port 9000

# With model flag
uv run punie serve --model claude-sonnet-4-5-20250929

# Help text
uv run punie serve --help

# Test HTTP endpoints (while serve is running)
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/echo -H "Content-Type: application/json" -d '{"message":"test"}'
```

### Code Changes

| Action | File | Lines |
|--------|------|-------|
| Create | `agent-os/specs/2026-02-08-serve-command/` | +600 (4 spec docs) |
| Modify | `src/punie/cli.py` | +60 (1 async helper + 1 command + imports) |
| Modify | `tests/test_cli.py` | +100 (6 tests) |
| Create | `examples/13_serve_dual.py` | +35 (dual-protocol demo) |

**Net Impact:** ~795 lines added

### Architecture Impact

**Before Phase 5.4:**
- Dual-protocol requires custom script
- No CLI access to HTTP + stdio mode
- Phase 3.1 infrastructure unused from CLI

**After Phase 5.4:**
- `punie serve` runs dual protocols from CLI
- Full control via flags (host, port, model, logging)
- Reuses Phase 3.1 infrastructure cleanly
- Startup messages show configuration

### Protocol Behavior

**Before agent starts:**
- stdout available for setup messages
- User-facing output with `typer.echo()`

**After agent starts:**
- stdout owned by ACP JSON-RPC
- HTTP runs on separate port
- All logs to files

### Design Decisions

**1. Async Helper Separation**

```python
# Typer command (sync)
def serve(...):
    asyncio.run(run_serve_agent(...))

# Async logic (testable)
async def run_serve_agent(...):
    ...
```

**2. Reuse Existing Infrastructure**

No changes to `run_dual()`, `create_app()`, or HTTP endpoints. Pure wiring.

**3. Startup Messages**

```
Starting Punie agent (dual protocol mode)
  Model: claude-sonnet-4-5-20250929
  HTTP: http://127.0.0.1:8000
  Logs: ~/.punie/logs/punie.log
```

Clear feedback before stdout reserved for ACP.

**4. Flag Consistency**

Same flags as main command (--model, --name, --log-dir, --log-level) plus HTTP-specific (--host, --port).

### Standards Applied

This phase followed 4 Agent OS standards:

1. **function-based-tests** — All 6 tests are functions, not classes
2. **agent-verification** — astral:ty + astral:ruff before completion
3. **separation-of-concerns** — Async helper separate from Typer command
4. **reuse-infrastructure** — No duplication of Phase 3.1 code

Full spec documentation in `agent-os/specs/2026-02-08-serve-command/`

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

## Phase 6.1: Local MLX Model with Tool Calling (2026-02-08)

### Context

Enable fully local, offline AI-assisted development on Apple Silicon. The existing `pydantic-ai-mlx` project by dorukgezici provided MLX model support for Pydantic AI, but was completely broken with Pydantic AI v1.56.0:

**Breaking changes from pydantic-ai-mlx to current API:**
1. `AgentModel` abstract class → removed (now just `Model`)
2. `Model.agent_model()` method → removed
3. `request()` signature → added `model_request_parameters` argument
4. `StreamedResponse` → 4 new abstract properties required
5. `Usage` dataclass → renamed to `RequestUsage`
6. Tool definitions → moved to `ModelRequestParameters.function_tools`

**Tool calling status:** WIP in original project — chat template approach existed, but response parsing was never implemented.

**Decision:** Port the sound architectural ideas (message mapping, chat templates) to current Pydantic AI API and complete tool calling.

### Implementation

**Core Module: `src/punie/models/mlx.py`**

**Pure Function:**
```python
def parse_tool_calls(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Extract <tool_call>{"name": "...", "arguments": {...}}</tool_call> blocks."""
    pattern = r'<tool_call>(.*?)</tool_call>'
    matches = re.findall(pattern, text, re.DOTALL)

    calls = []
    for match in matches:
        try:
            call = json.loads(match.strip())
            if "name" in call:
                calls.append(call)
        except json.JSONDecodeError:
            continue

    clean_text = re.sub(pattern, '', text, flags=re.DOTALL).strip()
    return clean_text, calls
```

**Model Class:**
```python
class MLXModel(Model):
    def __init__(self, model_name: str, *, settings: ModelSettings | None = None):
        try:
            from mlx_lm.utils import load as mlx_load
        except ImportError as e:
            raise ImportError("mlx-lm is required...") from e

        self._model_name = model_name
        self.model_data, self.tokenizer = mlx_load(model_name)

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        # Map messages to OpenAI format dicts
        chat_messages = self._map_request(messages)

        # Convert ToolDefinition to OpenAI tools format
        tools = self._build_tools(model_request_parameters)

        # Generate with chat template
        output = self._generate(chat_messages, tools, model_settings, stream=False)

        # Parse tool calls from output
        text, tool_calls = parse_tool_calls(output)

        # Build response parts
        parts = []
        if text:
            parts.append(TextPart(content=text))
        for tool_call in tool_calls:
            parts.append(ToolCallPart(
                tool_name=tool_call["name"],
                args=tool_call.get("arguments", {}),
            ))

        return ModelResponse(parts=parts, ...)
```

**Streaming Support:**
```python
@dataclass
class MLXStreamedResponse(StreamedResponse):
    """Streaming does NOT parse tool calls (requires full output)."""

    async def _get_event_iterator(self):
        text_part = TextPart(content="")
        yield PartStartEvent(index=0, part=text_part)

        async for token_dict in AsyncStream(self._stream_iterator):
            if isinstance(token_dict, dict) and "text" in token_dict:
                for event in self._parts_manager.handle_text_delta(
                    vendor_part_id=0, content=token_dict["text"]
                ):
                    yield event
```

### Factory Integration

**Model Selection:**
```python
def create_pydantic_agent(model: KnownModelName | Model = "test", ...):
    if model == "local":
        model = _create_local_model()  # Default: Qwen2.5-Coder-7B-Instruct-4bit
    elif isinstance(model, str) and model.startswith("local:"):
        model = _create_local_model(model.split(":", 1)[1])
```

**Usage:**
```bash
# Environment variable
PUNIE_MODEL=local punie serve

# CLI flag
punie serve --model local

# Custom model
punie serve --model local:mlx-community/Qwen2.5-Coder-3B-Instruct-4bit
```

### Cross-Platform Support

**Lazy Imports with TYPE_CHECKING:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mlx_lm import generate, stream_generate
    from mlx_lm.utils import load as mlx_load

class MLXModel(Model):
    def __init__(self, model_name: str):
        try:
            from mlx_lm.utils import load as mlx_load
        except ImportError as e:
            raise ImportError("mlx-lm is required...") from e
```

**Why?** Module must be importable on Linux/Windows for tests and type checking, even though MLX only runs on macOS arm64.

### Optional Dependency

**pyproject.toml:**
```toml
[project.optional-dependencies]
local = ["mlx-lm>=0.22.0"]
```

**Installation:**
```bash
# Basic install (no MLX)
uv pip install punie

# With local model support (macOS arm64 only)
uv pip install 'punie[local]'
```

### Tool Calling Approach

MLX models don't have native function-calling API. Instead:

1. **Tool Definitions → Chat Template:**
   ```python
   tools = [{"type": "function", "function": {"name": "read", ...}}]
   prompt = tokenizer.apply_chat_template(messages, tools=tools, ...)
   ```

2. **Model Outputs Tags:**
   ```
   Let me read that file<tool_call>{"name": "read", "arguments": {"path": "foo.py"}}</tool_call>
   ```

3. **Regex Parsing:**
   ```python
   text, calls = parse_tool_calls(output)
   # text = "Let me read that file"
   # calls = [{"name": "read", "arguments": {"path": "foo.py"}}]
   ```

4. **Pydantic AI Handles Loop:**
   - Returns `ModelResponse` with `ToolCallPart`
   - Pydantic AI executes tool
   - Adds `ToolReturnPart` to messages
   - Loops until model returns text only

### Test Coverage

**26 function-based tests in `tests/test_mlx_model.py`:**

**Pure function tests (7):**
- `test_parse_single_tool_call` — single tool call extraction
- `test_parse_multiple_tool_calls` — multiple calls in one output
- `test_parse_no_tool_calls` — plain text, no calls
- `test_parse_invalid_json_tool_call` — skip malformed JSON
- `test_parse_tool_call_missing_name` — skip calls without name
- `test_async_stream_wraps_sync_iterator` — AsyncStream wrapper
- `test_async_stream_raises_stop_async_iteration` — exhausted iterator

**Model property tests (4):**
- `test_mlx_model_import_without_mlx_lm` — TYPE_CHECKING guards work
- `test_mlx_model_init_without_mlx_lm` — ImportError without mlx-lm
- `test_mlx_model_properties` — model_name, system properties
- `test_build_tools_converts_function_tools` — ToolDefinition → OpenAI format
- `test_build_tools_returns_none_for_empty` — no tools = None

**Message mapping tests (5):**
- `test_map_request_with_system_and_user` — system + user parts
- `test_map_request_with_tool_return` — ToolReturnPart handling
- `test_map_request_with_model_response` — ModelResponse with text + tool calls

**Request integration tests (3):**
- `test_request_with_text_response` — text-only response
- `test_request_with_tool_calls` — tool call parsing
- `test_request_with_mixed_text_and_tools` — both text and calls

**Factory tests (4):**
- `test_factory_local_model_raises_import_error` — no mlx-lm installed
- `test_factory_local_with_model_name_raises_import_error` — 'local:name' without mlx-lm
- `test_factory_local_model_name_parsing` — 'local:model-name' extraction
- `test_factory_local_default_model_name` — default Qwen model

**All tests work WITHOUT mlx-lm installed** — uses monkeypatching and fakes.

### Example

**New Example: `examples/15_mlx_local_model.py`**

Demonstrates:
1. Direct MLXModel creation
2. Agent with `model='local'`
3. Custom model with `model='local:model-name'`
4. Recommended models info (3B, 7B, 14B variants)
5. Platform guard for non-macOS

### Code Changes

| Action | File | Description |
|--------|------|-------------|
| Create | `src/punie/models/__init__.py` | Thin package init with TYPE_CHECKING guards |
| Create | `src/punie/models/mlx.py` | MLXModel, MLXStreamedResponse, parse_tool_calls, AsyncStream (~440 lines) |
| Modify | `src/punie/agent/factory.py` | Add _create_local_model(), handle 'local' and 'local:name' (+25 lines) |
| Modify | `pyproject.toml` | Add [project.optional-dependencies] local (+2 lines) |
| Create | `tests/test_mlx_model.py` | 26 function-based tests (~500 lines) |
| Create | `examples/15_mlx_local_model.py` | Local model demo (~140 lines) |
| Create | `agent-os/specs/2026-02-08-mlx-model/` | 4 spec docs: plan, shape, standards, references (~800 lines) |

**Net Impact:** ~1,907 lines added

### Recommended Models

| Model | Size | RAM | Use Case |
|-------|------|-----|----------|
| Qwen2.5-Coder-3B-Instruct-4bit | ~2GB | 6GB+ | Fast, simple tasks |
| **Qwen2.5-Coder-7B-Instruct-4bit** (default) | ~4GB | 8GB+ | **Balanced quality/speed** |
| Qwen2.5-Coder-14B-Instruct-4bit | ~8GB | 16GB+ | Best quality, slower |

All models: https://huggingface.co/mlx-community

**Qwen2.5-Coder advantages:**
- Tool-aware chat template built-in
- Excellent coding task performance
- 4-bit quantization for memory efficiency

### Architecture Impact

**Before Phase 6.1:**
- All models require API calls (OpenAI, Anthropic, etc.)
- No offline development mode
- Costs per token for experimentation

**After Phase 6.1:**
- `PUNIE_MODEL=local` runs entirely on-device
- Zero API costs for local development
- Privacy-sensitive codebases supported
- Fast iteration (no API latency)
- Full tool calling works locally

### Design Decisions

**1. No openai Dependency**

Original pydantic-ai-mlx imported `openai.types.chat` for type hints, then converted to dicts. We skip openai entirely:

```python
# Direct dict construction
{"role": "user", "content": "Hello"}
```

**Trade-off:** Lose type safety on message format, gain zero external dependencies.

**2. Streaming Without Tool Call Parsing**

`request_stream()` yields text only. Tool calls parsed only in `request()`.

**Rationale:** Regex parsing `<tool_call>...</tool_call>` requires complete output. Streaming would need buffering, partial parse states, complexity not justified.

**Trade-off:** Streaming can't execute tools until complete. Acceptable because local models are fast.

**3. Default Model: Qwen2.5-Coder-7B-Instruct-4bit**

4-bit quantization fits in 8GB unified memory. Qwen2.5-Coder has tool-calling chat template. 7B balances quality and speed.

**4. Cross-Platform Imports**

TYPE_CHECKING guards allow import on any platform. Runtime import in `__init__` raises clear ImportError with installation instructions.

### Package Structure

| Package         | Purpose                     | Key Modules                                         |
|-----------------|-----------------------------|-----------------------------------------------------|
| `punie.acp`     | Vendored ACP SDK (29 files) | `interfaces`, `core`, `schema`, `agent/`, `client/` |
| `punie.agent`   | Pydantic AI bridge          | `adapter`, `toolset`, `deps`, `factory`             |
| `punie.models`  | **Custom model implementations** | **`mlx` — Local MLX model with tool calling** |
| `punie.http`    | HTTP server                 | `app`, `runner`, `types`                            |
| `punie.testing` | Test infrastructure         | `fakes`, `server`                                   |

### Test Statistics

- **Total tests:** 189 (as of Phase 6.1)
- **Coverage:** 81%+ (exceeds 80% requirement)
- **Test distribution:**
    - Protocol satisfaction: 2
    - Schema/RPC: 8
    - Tool calls/concurrency: 8
    - Fakes: 39
    - Pydantic agent: 20
    - Discovery: 16
    - Session registration: 16
    - CLI: 19 (10 basic + 4 init + 5 serve)
    - HTTP: 6
    - Dual protocol: 2
    - MLX model: 26 (7 pure function + 4 properties + 5 mapping + 3 integration + 4 factory + 3 streaming)
    - Examples: 11 (10_session_registration + 15_mlx_local_model)

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
| `typer>=0.15.0`           | Phase 5.1 | CLI framework for punie command                                 |
| `mlx-lm>=0.22.0` (optional) | Phase 6.1 | **Local MLX model support (macOS arm64 only)**              |

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
| 2026-02-08 | 5.1     | CLI development (Typer entry point, file-only logging, stdio constraint, 10 tests)           |
| 2026-02-08 | 5.2     | Config generation (punie init, acp.json, pure functions, 13 tests)                           |
| 2026-02-08 | 5.4     | Server mode (punie serve, dual-protocol HTTP+ACP, 6 tests)                                   |
| 2026-02-08 | 6.1     | Local MLX model (port pydantic-ai-mlx, tool calling, cross-platform support, 26 tests)       |
| 2026-02-08 | 6.2     | Model download CLI + Python 3.14 (download-model command, model validation, remove free-threading)  |
