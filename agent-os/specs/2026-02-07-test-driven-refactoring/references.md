# References for Test-Driven Refactoring

## Upstream ACP SDK

### Location
`~/PycharmProjects/python-acp-sdk/`

### Key Files to Vendor
- **Source directory:** `~/PycharmProjects/python-acp-sdk/src/acp/` (29 files)
- **Total size:** ~200KB (including 137KB `schema.py`)

### Files Requiring Modification After Vendoring

| File | Line | Change | Reason |
|------|------|--------|--------|
| `router.py` | 11 | `from acp.utils import to_camel_case` → `from .utils import to_camel_case` | Fix absolute import for vendored location |
| `interfaces.py` | 73 | Add `@runtime_checkable` to `Client` protocol | Enable isinstance() tests |
| `interfaces.py` | 143 | Add `@runtime_checkable` to `Agent` protocol | Enable isinstance() tests |
| `schema.py` | 1 | Add provenance comment | Document source and modification policy |

### Package Information
- **PyPI package:** `agent-client-protocol>=0.7.1`
- **Dependencies:** `pydantic>=2.0`, `websockets`, `aiofiles`
- **After vendoring:** Must add `pydantic>=2.0` as direct punie dependency

## Current Punie Test Suite

### Test Files

| File | Purpose | Line Count | Tests |
|------|---------|------------|-------|
| `tests/test_acp_sdk.py` | ACP integration tests (TO BE SPLIT) | ~200 | 7 |
| `tests/test_freethreaded.py` | Free-threading verification | ~50 | 2 |
| `tests/conftest.py` | Pytest fixtures | ~30 | N/A |
| `tests/acp_helpers.py` | Test fakes (TO BE MIGRATED) | ~180 | N/A |

### Tests in test_acp_sdk.py (to be distributed)

1. **test_acp_schema_model_roundtrip** → `tests/test_schema.py`
   - Verifies Request/Response JSON serialization

2. **test_initialize_and_new_session** → `tests/test_rpc.py`
   - Tests initialize call and session creation

3. **test_bidirectional_file_read_write** → `tests/test_rpc.py`
   - Tests file_read and file_write RPC methods

4. **test_cancel_notification_dispatched** → `tests/test_notifications.py`
   - Verifies cancel notifications reach agent

5. **test_session_update_notifications** → `tests/test_notifications.py`
   - Tests session state change notifications

6. **test_tool_call_lifecycle** → `tests/test_tool_calls.py`
   - Tests tool registration, call, and response

7. **test_concurrent_file_reads** → `tests/test_concurrency.py`
   - Tests parallel file access handling

### Test Helpers in acp_helpers.py (to be migrated)

| Class | Purpose | Destination |
|-------|---------|-------------|
| `_Server` | WebSocket server for tests | `src/punie/testing/server.py` as `LoopbackServer` |
| `FakeAgent` | Mock agent for testing | `src/punie/testing/fakes.py` with configurable constructor |
| `FakeClient` | Mock client for testing | `src/punie/testing/fakes.py` with configurable constructor |

## Example Files Using ACP SDK

All examples import from `acp` package (need transition to `punie.acp`):

1. `examples/01_schema_basics.py` — Request/Response models
2. `examples/02_json_rpc_basics.py` — RPC message construction
3. `examples/03_agent_protocol.py` — Agent interface
4. `examples/04_client_protocol.py` — Client interface
5. `examples/05_tool_definitions.py` — Tool schema
6. `examples/06_websocket_lifecycle.py` — Connection setup
7. `examples/07_acp_connection_lifecycle.py` — Full lifecycle (imports from tests/)
8. `examples/08_session_management.py` — Session state
9. `examples/09_dynamic_tool_discovery.py` — Dynamic tools

**Special case:** Example 07 uses `sys.path.insert` to import from `tests/acp_helpers.py`. After Task 4, should import from `punie.testing` instead.

## Configuration Files

### pyproject.toml Changes

**Task 2 (Vendoring):**
- Add `"src/punie/acp/schema.py"` to `[tool.ruff] extend-exclude`

**Task 3 (Dependency Removal):**
- Remove: `"agent-client-protocol>=0.7.1"` from `dependencies`
- Add: `"pydantic>=2.0"` to `dependencies`

## Documentation Files Requiring Updates

### Task 7 (Sever Upstream Connection)

| File | Current Reference | Required Change |
|------|-------------------|-----------------|
| `README.md` | `~/PycharmProjects/python-acp-sdk` references | Update to describe vendored `punie.acp` |
| `tests/acp_helpers.py` | "Ported from python-acp-sdk" comment | Remove (now just re-export wrapper) |
| `docs/research/acp-sdk.md` | "Local checkout" section | Note SDK vendored at `src/punie/acp/` |

### Files NOT to Change

| File | Reason |
|------|--------|
| `agent-os/specs/2026-02-07-1900-*` | Historical spec, documents where code came from originally |
| `agent-os/specs/2026-02-07-2000-*` | Historical spec, accurate at time of writing |

## Related Roadmap Items

- **2.1** Vendor ACP SDK → Task 2
- **2.2** Transition imports → Task 3
- **2.3a** Refactor test fakes → Task 4
- **2.3b** Split tests by concern → Task 5
- **2.4** Model mock infrastructure → Task 6
- **3.3** Pydantic AI integration (future, depends on vendored SDK)

## Verification Commands

### After Task 2 (Vendoring)
```bash
uv run python -c "from punie.acp import Agent, Client"  # should work
uv run pytest -v  # should pass (using old imports)
```

### After Task 3 (Import Transition)
```bash
uv run python -c "import acp"  # should fail (pip package removed)
uv run python -c "from punie.acp import Agent, Client"  # should work
uv run pytest -v  # should pass (using new imports)
```

### After Task 4 (Protocol Satisfaction)
```bash
uv run pytest tests/test_protocol_satisfaction.py -v  # should pass
```

### After Task 6 (Model Responders)
```bash
uv run pytest tests/test_model_responder.py -v  # should pass
```

### Final Verification (Task 8)
```bash
uv run pytest -v  # all tests pass
grep -r "PycharmProjects" --include="*.py" --include="*.md" src/ tests/ examples/  # no hits outside specs
```

## External Dependencies

### Direct Dependencies After Refactoring
- `pydantic>=2.0` — Data validation (was transitive, now direct)
- `websockets` — WebSocket protocol (transitive from vendored code)
- `aiofiles` — Async file I/O (transitive from vendored code)

### Removed Dependencies
- `agent-client-protocol>=0.7.1` — Replaced by vendored `punie.acp`

## Standards Referenced

See `standards.md` in this spec directory for details:
- agent-verification
- function-based-tests
- fakes-over-mocks
- protocol-satisfaction-test
- sybil-doctest
