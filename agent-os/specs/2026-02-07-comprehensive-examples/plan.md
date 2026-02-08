# Plan: Create Comprehensive Examples (Roadmap 1.2)

## Context

Punie's roadmap item 1.2 calls for "Create comprehensive examples." The existing `examples/` directory has only `hello_world.py`. The project needs progressive examples demonstrating ACP SDK primitives, contrib utilities, connection lifecycle, and aspirational integration patterns. These examples serve as both documentation and self-testing runnable code.

**Branch:** `feature/1.2-comprehensive-examples`

## Key Design Decisions

1. **9 numbered examples** (`01_` through `09_`) providing clear progressive ordering. `hello_world.py` stays as the unnumbered foundational example.

2. **Self-contained convention:** Each example has a module docstring, `main()` function with assertions, and `if __name__ == "__main__":` guard. No pytest fixtures — examples must work standalone.

3. **Tier structure:**
   - Tier 1 (01-06): Sync, schema/model only — no network needed
   - Tier 2 (07): Async, self-contained TCP loopback using `tests.acp_helpers`
   - Tier 3 (08-09): Aspirational — schema portions run, future code in comments

4. **No changes to test infrastructure** — `tests/test_examples.py` auto-discovers all new examples via parametrized glob.

## Tasks

### Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-07-comprehensive-examples/` with:
- **plan.md** — This plan
- **shape.md** — Scope decisions, context from shaping conversation
- **standards.md** — agent-verification, sybil-doctest, function-based-tests, fakes-over-mocks
- **references.md** — Pointers to `tests/test_acp_sdk.py` and ACP SDK helpers

### Task 2: `01_schema_basics.py`

**Sync** — ACP schema model construction, serialization, deserialization roundtrip.

### Task 3: `02_content_blocks.py`

**Sync** — Content block types and helper factory functions.

### Task 4: `03_tool_call_models.py`

**Sync** — Tool call lifecycle models and factory functions.

### Task 5: `04_session_notifications.py`

**Sync** — Session notifications, plan management, and SessionAccumulator.

### Task 6: `05_tool_call_tracker.py`

**Sync** — Agent-side tool call state management with ToolCallTracker.

### Task 7: `06_permission_models.py`

**Sync** — Permission option types and request construction.

### Task 8: `07_acp_connection_lifecycle.py`

**Async** — Full ACP agent-client connection over TCP loopback.

### Task 9: `08_pydantic_ai_agent.py`

**Sync, Aspirational** — Intended Pydantic AI + ACP integration pattern (Phase 3).

### Task 10: `09_dynamic_tool_discovery.py`

**Sync, Aspirational** — Dynamic tool discovery pattern (Phase 4).

### Task 11: Update Roadmap

**File:** `agent-os/product/roadmap.md`

Change `- [ ] 1.2 Create comprehensive examples` to `- [x] 1.2 Create comprehensive examples`

### Task 12: Verify

1. Run each example standalone: `uv run python examples/01_schema_basics.py` (etc.)
2. Run full test suite: `uv run pytest -v`
3. Use `astral:ruff` skill for lint/format
4. Use `astral:ty` skill for type checking

## Files Summary

| File | Action |
|------|--------|
| `agent-os/specs/2026-02-07-comprehensive-examples/plan.md` | Create |
| `agent-os/specs/2026-02-07-comprehensive-examples/shape.md` | Create |
| `agent-os/specs/2026-02-07-comprehensive-examples/standards.md` | Create |
| `agent-os/specs/2026-02-07-comprehensive-examples/references.md` | Create |
| `examples/01_schema_basics.py` | Create |
| `examples/02_content_blocks.py` | Create |
| `examples/03_tool_call_models.py` | Create |
| `examples/04_session_notifications.py` | Create |
| `examples/05_tool_call_tracker.py` | Create |
| `examples/06_permission_models.py` | Create |
| `examples/07_acp_connection_lifecycle.py` | Create |
| `examples/08_pydantic_ai_agent.py` | Create |
| `examples/09_dynamic_tool_discovery.py` | Create |
| `agent-os/product/roadmap.md` | Modify — check 1.2 |
