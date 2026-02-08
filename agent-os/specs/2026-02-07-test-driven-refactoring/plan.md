# Plan: Test-Driven Refactoring (Roadmap Task Group 2)

## Context

Punie depends on the ACP Python SDK (`agent-client-protocol` pip package) as an external dependency. To enable future modification and Pydantic AI integration (Phase 3), the SDK needs to be vendored into the project. The existing test suite bundles concerns into one file and uses hardcoded fakes. This plan vendors the SDK, transitions imports, splits tests by concern, and builds configurable mock infrastructure for model calls.

**Branch:** `feature/2-test-driven-refactoring`

## Key Design Decisions

1. **Vendor location:** `src/punie/acp/` — subpackage of punie, imports become `from punie.acp import ...`
2. **Single absolute import fix:** Only `router.py:11` has `from acp.utils import ...` — change to relative
3. **Flat test structure:** Split by concern via file naming (no subdirectories), avoids conftest scoping complexity
4. **Testing utilities as public package:** `src/punie/testing/` — fakes are discoverable and reusable
5. **Add `pydantic>=2.0` as direct dependency** — currently transitive through `agent-client-protocol`, needed after removal
6. **`schema.py` excluded from ruff** — 137KB auto-generated file, copied verbatim

## Tasks

### Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-07-test-driven-refactoring/` with:
- **plan.md** — This plan
- **shape.md** — Scope decisions, context from shaping conversation
- **standards.md** — agent-verification, function-based-tests, fakes-over-mocks, protocol-satisfaction-test, sybil-doctest
- **references.md** — Pointers to upstream SDK, current test files

### Task 2: Vendor the ACP SDK (Roadmap 2.1)

Copy `~/PycharmProjects/python-acp-sdk/src/acp/` → `src/punie/acp/` (29 files).

**Modifications to vendored files:**
- `src/punie/acp/router.py:11` — Change `from acp.utils import to_camel_case` → `from .utils import to_camel_case`
- `src/punie/acp/interfaces.py` — Add `@runtime_checkable` to `Agent` (line 143) and `Client` (line 73) protocols
- `src/punie/acp/schema.py` — Add vendoring provenance comment

**Config changes:**
- `pyproject.toml` — Add `"src/punie/acp/schema.py"` to `[tool.ruff] extend-exclude`

**Do NOT remove** `agent-client-protocol` from dependencies yet — both can coexist.

**Verify:** `uv run python -c "from punie.acp import Agent, Client"` succeeds; existing tests still pass.

### Task 3: Transition Imports and Remove pip Dependency (Roadmap 2.2)

**12 files, ~16 import lines** — mechanical `from acp` → `from punie.acp` across:
- `tests/conftest.py`, `tests/acp_helpers.py`, `tests/test_acp_sdk.py`, `tests/test_freethreaded.py`
- `examples/01_schema_basics.py` through `examples/09_dynamic_tool_discovery.py` (9 files)

**Config changes:**
- `pyproject.toml` — Remove `"agent-client-protocol>=0.7.1"` from `dependencies`, add `"pydantic>=2.0"`
- Run `uv sync` to update lock file

**Also:** Update `examples/07_acp_connection_lifecycle.py` to import from `punie.testing` instead of `tests.acp_helpers` (removes sys.path hack).

**Verify:** `uv run pytest -v` passes; `uv run python -c "import acp"` fails (pip package gone); all examples work.

### Task 4: Refactor Tests — Fakes and Protocol Satisfaction (Roadmap 2.3a)

**Create `src/punie/testing/`:**
- `__init__.py` — Re-exports `FakeAgent`, `FakeClient`, `LoopbackServer`
- `server.py` — `LoopbackServer` (renamed from `_Server`)
- `fakes.py` — `FakeAgent` and `FakeClient` with configurable constructors:
  - `FakeAgent(session_id=..., protocol_version=..., model_responder=...)`
  - `FakeClient(files=..., default_file_content=...)`

**Modify `tests/acp_helpers.py`** — Replace with thin re-exports from `punie.testing`

**Modify `tests/conftest.py`** — Import from `punie.testing`

**Create `tests/test_protocol_satisfaction.py`:**
- `test_fake_agent_satisfies_agent_protocol()` — `isinstance(FakeAgent(), Agent)`
- `test_fake_client_satisfies_client_protocol()` — `isinstance(FakeClient(), Client)`

**Verify:** `uv run pytest tests/test_protocol_satisfaction.py -v` passes.

### Task 5: Refactor Tests — Split by Concern (Roadmap 2.3b)

Split `tests/test_acp_sdk.py` (7 tests) into focused modules:

| New file | Tests moved |
|----------|-------------|
| `tests/test_schema.py` | `test_acp_schema_model_roundtrip` |
| `tests/test_rpc.py` | `test_initialize_and_new_session`, `test_bidirectional_file_read_write` |
| `tests/test_notifications.py` | `test_cancel_notification_dispatched`, `test_session_update_notifications` |
| `tests/test_tool_calls.py` | `test_tool_call_lifecycle` |
| `tests/test_concurrency.py` | `test_concurrent_file_reads` |

**Delete** `tests/test_acp_sdk.py` after distribution.

**Verify:** `uv run pytest -v` — same test count, all pass.

### Task 6: Build Model Mock Infrastructure (Roadmap 2.4)

**Create `src/punie/testing/model_responder.py`:**

```python
@runtime_checkable
class ModelResponder(Protocol):
    async def respond(self, prompt, session_id, **kwargs) -> PromptResponse: ...
```

**Pre-built fakes:**
- `CannedResponder(stop_reason="end_turn")` — Default behavior (current hardcoded response)
- `ErrorResponder(exception)` — Raises on respond()
- `MultiTurnResponder(responses)` — Returns responses in sequence
- `CallbackResponder(fn)` — Wraps arbitrary async callable

**Update `src/punie/testing/fakes.py`** — `FakeAgent.prompt()` delegates to `self._model_responder`

**Update `src/punie/testing/__init__.py`** — Re-export all responders

**Create `tests/test_model_responder.py`:**
- Protocol satisfaction tests for each responder
- Behavioral tests (canned response, error raising, multi-turn sequence)
- Integration test: `FakeAgent` with custom `ModelResponder`

**Verify:** `uv run pytest tests/test_model_responder.py -v` passes.

### Task 7: Sever Connection with Upstream Project

Remove all references treating `python-acp-sdk` as an external dependency. The SDK is now vendored and owned by Punie.

**Files to modify:**
- `README.md` — Remove `~/PycharmProjects/python-acp-sdk` references; update to describe vendored `punie.acp`
- `tests/acp_helpers.py` — Remove "Ported from python-acp-sdk" comment (file is now a re-export wrapper)
- `docs/research/acp-sdk.md` — Update "Local checkout" reference to note SDK is now vendored at `src/punie/acp/`

**Historical spec files** (`agent-os/specs/2026-02-07-1900-*`, `agent-os/specs/2026-02-07-2000-*`) — Leave as-is. These document past decisions and correctly reference where code came from at the time.

**Roadmap references** (`agent-os/product/roadmap.md`) — The "python-sdk" wording in items 1.3, 1.4, 2.1, 2.2, 3.3 is historical context. Update 2.1 and 2.2 descriptions when marking them complete to reflect what was done.

### Task 8: Final Verification and Roadmap Update

1. `uv run pytest -v` — All tests pass
2. Use `astral:ruff` skill — No issues
3. Use `astral:ty` skill — No type errors
4. `uv run python -c "from punie.acp import Agent, Client"` — Works
5. `uv run python -c "from punie.testing import FakeAgent, ModelResponder"` — Works
6. `grep -r "PycharmProjects" --include="*.py" --include="*.md" src/ tests/ examples/` — No hits outside historical specs

**Update `agent-os/product/roadmap.md`** — Mark 2.1-2.4 as complete.

## Files Summary

| Action | Files |
|--------|-------|
| **Create (spec)** | `agent-os/specs/2026-02-07-test-driven-refactoring/{plan,shape,standards,references}.md` |
| **Create (vendored SDK)** | `src/punie/acp/` — 29 files from upstream |
| **Create (testing pkg)** | `src/punie/testing/{__init__,server,fakes,model_responder}.py` |
| **Create (new tests)** | `tests/test_{protocol_satisfaction,schema,rpc,notifications,tool_calls,concurrency,model_responder}.py` |
| **Modify (imports)** | `tests/{conftest,acp_helpers,test_freethreaded}.py`, `examples/0{1..9}_*.py` |
| **Modify (config)** | `pyproject.toml` (deps + ruff exclude) |
| **Modify (vendored)** | `src/punie/acp/{router,interfaces,schema}.py` |
| **Modify (roadmap)** | `agent-os/product/roadmap.md` |
| **Delete** | `tests/test_acp_sdk.py` |

## Critical Reference Files

| File | Why |
|------|-----|
| `~/PycharmProjects/python-acp-sdk/src/acp/` | Source to vendor |
| `~/PycharmProjects/python-acp-sdk/src/acp/router.py:11` | Single absolute import to fix |
| `~/PycharmProjects/python-acp-sdk/src/acp/interfaces.py:73,143` | `Client`/`Agent` protocols — add `@runtime_checkable` |
| `tests/acp_helpers.py` | Current fakes to migrate to `src/punie/testing/` |
| `tests/test_acp_sdk.py` | 7 tests to split into 5 focused modules |
| `tests/conftest.py` | Fixtures to update imports |
