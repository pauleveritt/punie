# References: Pytest ACP SDK Integration

## Primary Sources

### ACP Python SDK Test Infrastructure
**File:** `~/PycharmProjects/python-acp-sdk/tests/conftest.py`

**Key Components:**
- `_Server` class — TCP loopback server creating paired stream readers/writers
- `TestAgent` class — Fake agent implementing Agent Protocol
- `TestClient` class — Fake client implementing Client Protocol
- `server`, `agent`, `client`, `connect` fixtures

**Porting Notes:**
- Rename `TestAgent` → `FakeAgent`, `TestClient` → `FakeClient`
- Move class definitions to `tests/acp_helpers.py`
- Keep fixtures in `tests/conftest.py`
- Add `__test__ = False` to both fake classes

### ACP SDK RPC Tests
**File:** `~/PycharmProjects/python-acp-sdk/tests/test_rpc.py`

**Key Test Patterns:**
- `test_initialize_and_new_session` — Basic RPC roundtrip
- `test_bidirectional_file_ops` — File read/write through client
- `test_cancel_notification_and_capture_wire` — One-way notifications
- `test_session_notifications_flow` — Agent-to-client messaging
- `test_concurrent_reads` — Parallel asyncio operations
- `test_example_agent_permission_flow` — Full tool call with permissions

**Adaptation for Punie:**
- Simplify to 7 focused tests (not full 15+ from SDK)
- Focus on integration points Punie will use
- Remove process spawning tests (SDK coverage sufficient)
- Remove extensive error handling tests (SDK coverage sufficient)

## Schema Models Reference

**Import from:** `acp.schema`

**Key Models Used:**
- `TextContentBlock` — Text content for prompts/responses
- `AgentMessageChunk` — Agent-to-client text messages
- `UserMessageChunk` — User message notifications
- `ToolCallStart` — Begin tool call with status/locations
- `ToolCallProgress` — Update tool call status/output
- `ToolCallLocation` — File path reference in tool calls
- `PermissionOption` — Permission prompt options
- `AllowedOutcome` / `DeniedOutcome` — Permission responses

## Protocol Connection Classes

**Import from:** `acp.core`

- `AgentSideConnection` — Agent's view of ACP connection
- `ClientSideConnection` — Client's view of ACP connection

**Key Methods:**
- `.initialize()` — Handshake with protocol version
- `.new_session()` — Create session
- `.prompt()` — Send prompt to agent
- `.request_permission()` — Ask for tool approval
- `.read_text_file()` / `.write_text_file()` — File operations
- `.session_update()` — Send notifications

## pytest-asyncio Configuration

**Documentation:** https://pytest-asyncio.readthedocs.io/

**Configuration Used:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**Effect:**
- Auto-detects async test functions
- Removes need for `@pytest.mark.asyncio` decorator
- Works alongside Sybil (sync doctest blocks unaffected)

## Sybil Compatibility Note

Existing Sybil configuration in `tests/conftest.py`:
```python
pytest_collect_file = Sybil(...).pytest()
```

**No conflict:** Sybil only collects from `.md` files and docstrings (sync code blocks). pytest-asyncio only affects async test functions. Both coexist safely.

## Related Documentation

- ACP Protocol Spec: https://github.com/anthropics/agent-client-protocol
- Pydantic 2.x: https://docs.pydantic.dev/latest/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- asyncio: https://docs.python.org/3/library/asyncio.html

## Local Research Documents

Created in Roadmap 1.3:
- `research/acp-python-sdk.md` — Deep dive on SDK architecture
- `research/pydantic-ai.md` — Pydantic AI patterns
