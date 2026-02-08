# Plan: Minimal Transition to Pydantic AI Project Structure (Roadmap 3.2)

## Context

Punie currently has a vendored ACP SDK and a hand-rolled `MinimalAgent` used only in tests. The roadmap calls for migrating to Pydantic AI as the internal agent engine. Phase 3.2 is the "minimal transition" — introduce the Pydantic AI dependency, create the adapter layer that bridges ACP's Agent protocol to Pydantic AI's `Agent.arun()`, and prove it works end-to-end with one tool (`read_file`).

**Goal:** Replace the hand-rolled MinimalAgent with a real Pydantic AI-backed `PunieAgent` that satisfies the ACP Agent protocol while delegating prompt handling to Pydantic AI.

## Architecture

Three new types in `src/punie/agent/`:

1. **ACPDeps** — Frozen dataclass holding `client_conn: Client`, `session_id: str`, `tracker: ToolCallTracker`. This is the `DepsType` for the Pydantic AI Agent.

2. **ACPToolset** — Subclass of `pydantic_ai.toolsets.AbstractToolset` exposing ACP Client methods as Pydantic AI tools. Phase 3.2 implements only `read_file` (wrapping `Client.read_text_file`).

3. **PunieAgent** — Adapter class satisfying the ACP `Agent` protocol (all 14 methods). Delegates `prompt()` to Pydantic AI `agent.arun()`. All other methods provide sensible defaults (matching current MinimalAgent behavior).

**Data flow:** ACP stdio receives prompt → PunieAgent.prompt() → constructs ACPDeps → calls pydantic_agent.arun() → Pydantic AI runs LLM → LLM may call read_file tool → ACPToolset calls Client.read_text_file via ACP → result flows back → PunieAgent sends AgentMessageChunk via session_update → returns PromptResponse.

## Tasks

### Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-07-pydantic-ai-structure/` with:
- **plan.md** — This plan
- **shape.md** — Scope decisions, adapter pattern rationale
- **standards.md** — All applicable standards (agent-verification, protocol-first-design, frozen-dataclass-services, fakes-over-mocks, function-based-tests, protocol-satisfaction-test, sybil-doctest)
- **references.md** — Pointers to ACP interfaces, research docs, existing fakes

### Task 2: Add pydantic-ai Dependency

**Modify:** `pyproject.toml` — add `"pydantic-ai>=0.1.0"` to `[project] dependencies`

Run `uv sync` and verify: `uv run python -c "from pydantic_ai import Agent"`

**Note:** Version floor TBD after checking latest available version. Must support `AbstractToolset` API.

### Task 3: Create `src/punie/agent/` Package

#### `src/punie/agent/deps.py` — ACPDeps

```python
@dataclass(frozen=True)
class ACPDeps:
    client_conn: Client      # ACP Client protocol reference
    session_id: str           # Current ACP session ID
    tracker: ToolCallTracker  # Tool call lifecycle manager
```

Frozen per `frozen-dataclass-services` standard. The `tracker` itself is mutable internally but the reference is frozen.

#### `src/punie/agent/toolset.py` — ACPToolset

Subclass `AbstractToolset[ACPDeps]`. Implement:
- `read_file` tool wrapping `Client.read_text_file()`
- Tool call lifecycle reporting via `tracker.start()` / `tracker.progress()` / `client.session_update()`

**Fallback:** If `AbstractToolset` API proves difficult, use `FunctionToolset[ACPDeps]` with `@toolset.tool` decorators instead. Simpler but functionally equivalent.

#### `src/punie/agent/adapter.py` — PunieAgent

Implements all 14 ACP Agent protocol methods. Key method signatures must match `src/punie/acp/interfaces.py` exactly (including type annotations) so `isinstance(agent, Agent)` passes at runtime.

- `on_connect()` — stores Client reference
- `new_session()` — creates session IDs (`"punie-session-N"`)
- `prompt()` — extracts text from ACP prompt blocks, constructs ACPDeps, calls `pydantic_agent.arun()`, sends response via `session_update()`
- All other methods — pass-through defaults (copy from MinimalAgent at `tests/fixtures/minimal_agent.py`)

#### `src/punie/agent/factory.py` — Agent Factory

```python
def create_pydantic_agent(model: str = "test") -> Agent[ACPDeps, str]:
    return Agent[ACPDeps, str](
        model,
        deps_type=ACPDeps,
        system_prompt="You are Punie, an AI coding assistant.",
        toolsets=[ACPToolset()],
    )
```

Default `model="test"` uses Pydantic AI's TestModel (no LLM calls needed for testing).

#### `src/punie/agent/__init__.py` — Exports

Export: `ACPDeps`, `ACPToolset`, `PunieAgent`, `create_pydantic_agent`

### Task 4: Write Unit Tests

**Create:** `tests/test_pydantic_agent.py`

Tests (function-based, fakes-over-mocks):

1. `test_punie_agent_satisfies_agent_protocol()` — `isinstance(PunieAgent(...), Agent)` (first test per protocol-satisfaction-test standard)
2. `test_acp_deps_is_frozen()` — verify frozen dataclass
3. `test_acp_deps_holds_references()` — construct with FakeClient, verify fields
4. `test_toolset_returns_read_file_tool()` — call `get_tools()`, verify tool definition
5. `test_punie_agent_initialize()` — verify InitializeResponse fields
6. `test_punie_agent_new_session_sequential_ids()` — verify session IDs are sequential
7. `test_punie_agent_prompt_delegates_to_pydantic_ai()` — use TestModel, verify prompt flows through, response sent back via session_update

All tests use `FakeClient` from `src/punie/testing/fakes.py` (already has `read_text_file`, `session_update`, `notifications` list).

### Task 5: Update Test Fixtures

**Modify:** `tests/fixtures/minimal_agent.py`
- Replace `MinimalAgent` class with `PunieAgent` + `create_pydantic_agent(model="test")`
- Keep `name="minimal-test-agent"` parameter for backward compatibility with `test_stdio_integration.py` assertions

**Modify:** `tests/fixtures/dual_agent.py`
- Same change: use PunieAgent instead of MinimalAgent

**Modify:** Tests that assert on session ID prefix:
- `tests/test_stdio_integration.py` lines 78, 145, 149 — change `"test-session-"` to `"punie-session-"`
- `tests/test_dual_protocol.py` line 130 — change `"test-session-"` to `"punie-session-"`

**Note:** `FakeAgent` in `src/punie/testing/fakes.py` stays unchanged — it's for testing the Client side, not the Agent side.

### Task 6: Update Exports and Documentation

**Modify:** `src/punie/__init__.py` — add `PunieAgent`, `ACPDeps`, `ACPToolset`, `create_pydantic_agent` to exports

**Modify:** `agent-os/product/tech-stack.md` — update Agent Framework section to note pydantic-ai is now a dependency (not just aspirational)

### Task 7: Verification and Roadmap Update

1. `uv run pytest` — all existing tests pass (no regressions)
2. `uv run pytest tests/test_pydantic_agent.py -v` — new unit tests pass
3. `uv run pytest -m slow` — integration tests pass with PunieAgent
4. Use `astral:ty` skill — no type errors on new code
5. Use `astral:ruff` skill — no lint issues
6. `uv run python -c "from punie.agent import PunieAgent, ACPDeps, ACPToolset"` — imports work

Update `agent-os/product/roadmap.md` — mark 3.2 complete.

## Files Summary

| Action | Files |
|--------|-------|
| **Create (spec)** | `agent-os/specs/2026-02-07-pydantic-ai-structure/{plan,shape,standards,references}.md` |
| **Create (agent)** | `src/punie/agent/{__init__,deps,toolset,adapter,factory}.py` |
| **Create (test)** | `tests/test_pydantic_agent.py` |
| **Modify** | `pyproject.toml` (add pydantic-ai dep) |
| **Modify** | `src/punie/__init__.py` (add exports) |
| **Modify** | `tests/fixtures/minimal_agent.py` (use PunieAgent) |
| **Modify** | `tests/fixtures/dual_agent.py` (use PunieAgent) |
| **Modify** | `tests/test_stdio_integration.py` (session ID prefix) |
| **Modify** | `tests/test_dual_protocol.py` (session ID prefix) |
| **Modify** | `agent-os/product/{roadmap.md,tech-stack.md}` |

No vendored ACP code is modified. FakeAgent/FakeClient remain unchanged.

## Critical Files to Reference During Implementation

- `src/punie/acp/interfaces.py` — ACP Agent protocol (PunieAgent must match exactly)
- `tests/fixtures/minimal_agent.py` — Template for PunieAgent's protocol method signatures
- `src/punie/testing/fakes.py` — FakeClient (used in all new tests)
- `src/punie/acp/contrib/tool_calls.py` — ToolCallTracker (used by ACPToolset)
- `docs/research/pydantic-ai.md` — AbstractToolset patterns and ACPDeps design

## What Phase 3.2 Does NOT Include

- No write_file tool (requires permission flow — Phase 3.3)
- No terminal tools (Phase 3.3)
- No real LLM model configuration (TestModel only)
- No Pydantic AI serving (to_a2a, to_ag_ui) — existing HTTP app stays as-is
- No changes to vendored ACP code
