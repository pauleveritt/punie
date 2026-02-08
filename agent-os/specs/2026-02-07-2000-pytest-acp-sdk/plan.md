# Plan: Pytest ACP SDK Integration (Roadmap 1.4)

## Context

Punie needs to prove the ACP Python SDK (`agent-client-protocol`) works correctly under Python 3.14.2t (free-threaded) before Phase 2 begins. This adds the SDK as a dependency, ports the SDK's test infrastructure into Punie, and writes focused integration tests covering RPC, file ops, notifications, tool calls, and concurrency.

## Spec Folder

`agent-os/specs/2026-02-07-2000-pytest-acp-sdk/`

## Standards Applied

- **agent-verification** — Verify using Astral skills, not justfile recipes

## References

- ACP Python SDK test infrastructure: `~/PycharmProjects/python-acp-sdk/tests/conftest.py`
- ACP SDK RPC tests: `~/PycharmProjects/python-acp-sdk/tests/test_rpc.py`

## Key Design Decisions

1. **`tests/acp_helpers.py` for classes, `tests/conftest.py` for fixtures** — Keeps fake classes importable and conftest focused on fixture wiring
2. **Rename TestAgent/TestClient → FakeAgent/FakeClient** — Avoids pytest collection; clearer naming
3. **`asyncio_mode = "auto"`** — Removes `@pytest.mark.asyncio` boilerplate; no conflict with Sybil (sync code blocks)
4. **7 focused tests** — Not exhaustive SDK coverage, but proves all critical paths work under 3.14t
5. **Production dependency** — `agent-client-protocol` added to `[project] dependencies` (will be replaced with own implementation later)

## Tasks

### Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-07-2000-pytest-acp-sdk/` with:
- `plan.md` — This plan
- `shape.md` — Scope, decisions, context
- `standards.md` — Full content of agent-verification standard
- `references.md` — Pointers to SDK test infrastructure files

### Task 2: Update `pyproject.toml`

**File:** `pyproject.toml`

- Add `"agent-client-protocol>=0.7.1"` to `dependencies`
- Add `"pytest-asyncio>=0.24.0"` to `[dependency-groups] dev`
- Add `asyncio_mode = "auto"` to `[tool.pytest.ini_options]`
- Run `uv sync`

### Task 3: Create `tests/acp_helpers.py`

**File:** `tests/acp_helpers.py` (new)

Port from `~/PycharmProjects/python-acp-sdk/tests/conftest.py`:

- **`_Server`** — TCP loopback creating two `(StreamReader, StreamWriter)` pairs for in-process ACP transport
- **`FakeAgent`** — Implements Agent Protocol: `initialize` echoes protocol version, `new_session` returns fixed ID, `cancel` records session IDs, `prompt` records and returns end_turn
- **`FakeClient`** — Implements Client Protocol: `request_permission` pops from queue, `read_text_file`/`write_text_file` use in-memory `files` dict, `session_update` appends to `notifications` list

Both fakes have `__test__ = False`.

### Task 4: Create `tests/conftest.py`

**File:** `tests/conftest.py` (new)

Four fixtures:
- `server` — async fixture yielding `_Server` context manager
- `agent` — returns `FakeAgent()`
- `client` — returns `FakeClient()`
- `connect` — factory returning `(AgentSideConnection, ClientSideConnection)` wired over the server streams

### Task 5: Create `tests/test_acp_sdk.py`

**File:** `tests/test_acp_sdk.py` (new)

7 function-based tests:

| # | Test | What it proves |
|---|------|----------------|
| 1 | `test_acp_schema_model_roundtrip` | Pydantic schema models serialize/deserialize under 3.14t (sync, no fixtures) |
| 2 | `test_initialize_and_new_session` | Agent-side RPC: initialize + new_session roundtrip over TCP loopback |
| 3 | `test_bidirectional_file_read_write` | Client-side RPC: agent reads/writes via client's in-memory filesystem |
| 4 | `test_cancel_notification_dispatched` | One-way notification: cancel propagates to agent handler |
| 5 | `test_session_update_notifications` | Agent-to-client: message notifications dispatched correctly |
| 6 | `test_tool_call_lifecycle` | Full tool call flow: start_tool_call → update_tool_call with status tracking |
| 7 | `test_concurrent_file_reads` | `asyncio.gather` over 5 parallel reads (free-threading safety) |

### Task 6: Verify

1. `uv run pytest -v` — all tests pass (existing + new)
2. Use `astral:ruff` skill to check linting
3. Use `astral:ty` skill to check types

### Task 7: Update Roadmap

**File:** `agent-os/product/roadmap.md`

Mark `1.3` and `1.4` as complete:
- `[x] 1.3 Add documentation with deep research on python-sdk and Pydantic AI`
- `[x] 1.4 Configure pytest setup proving python-sdk works correctly`

## Files Summary

**4 spec files to create:**
- `agent-os/specs/2026-02-07-2000-pytest-acp-sdk/plan.md`
- `agent-os/specs/2026-02-07-2000-pytest-acp-sdk/shape.md`
- `agent-os/specs/2026-02-07-2000-pytest-acp-sdk/standards.md`
- `agent-os/specs/2026-02-07-2000-pytest-acp-sdk/references.md`

**3 source files to create:**
- `tests/acp_helpers.py`
- `tests/conftest.py`
- `tests/test_acp_sdk.py`

**2 files to modify:**
- `pyproject.toml` — add dependencies and asyncio_mode
- `agent-os/product/roadmap.md` — mark 1.3 and 1.4 complete
