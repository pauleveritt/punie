# Standards Applied: Pydantic AI Structure (Phase 3.2)

This implementation adheres to the following Agent OS standards:

## agent-verification

**Location:** `agent-os/standards/agent-verification.md`

**Application:**
- Use `astral:ty` skill for type checking (not `just lint`)
- Use `astral:ruff` skill for linting/formatting (not `just format`)
- Use `uv run pytest` directly for testing (not `just test`)

**Verification Steps:**
1. `astral:ty` — check types on new code
2. `astral:ruff` — check/fix linting issues
3. `uv run pytest tests/test_pydantic_agent.py -v` — unit tests
4. `uv run pytest` — full suite (no regressions)

## services/protocol-first-design

**Location:** `agent-os/standards/services/protocol-first-design.md`

**Application:**
- `PunieAgent` satisfies ACP `Agent` protocol (from `src/punie/acp/interfaces.py`)
- All 14 protocol methods must be implemented with exact signatures
- Use `@runtime_checkable` on protocols for `isinstance()` checks
- Protocol defines contract, implementation is flexible

**Key Point:**
The ACP Agent protocol is already defined and `@runtime_checkable`. `PunieAgent` must conform exactly to pass `isinstance(agent, Agent)` at runtime.

## services/frozen-dataclass-services

**Location:** `agent-os/standards/services/frozen-dataclass-services.md`

**Application:**
- `ACPDeps` is a frozen dataclass (`@dataclass(frozen=True)`)
- Holds references to services: `client_conn: Client`, `session_id: str`, `tracker: ToolCallTracker`
- References are immutable, but services themselves may be mutable (e.g., `tracker` updates internal state)

**Rationale:**
Frozen dataclasses prevent accidental mutation of service references, improving code safety and making dependencies explicit.

**Example:**
```python
from dataclasses import dataclass
from punie.acp import Client
from punie.acp.contrib.tool_calls import ToolCallTracker

@dataclass(frozen=True)
class ACPDeps:
    client_conn: Client
    session_id: str
    tracker: ToolCallTracker
```

## testing/fakes-over-mocks

**Location:** `agent-os/standards/testing/fakes-over-mocks.md`

**Application:**
- Use `FakeClient` (from `src/punie/testing/fakes.py`) for all tests
- No mock/patch calls — `FakeClient` is a real implementation of Client protocol
- `FakeClient` records calls in `notifications` list for assertions
- Behavior can be configured via `files` dict, `permission_outcomes` queue

**Why Not Mocks:**
- Fakes are more maintainable (one implementation for all tests)
- Fakes catch protocol violations that mocks miss
- Fakes work across all test scenarios without reconfiguration

**Example:**
```python
def test_read_file_tool():
    fake_client = FakeClient(files={"/test.py": "content"})
    deps = ACPDeps(client_conn=fake_client, session_id="sess-1", tracker=ToolCallTracker())

    # Use fake_client in test — no mocks needed
    result = await fake_client.read_text_file(session_id="sess-1", path="/test.py")
    assert result.content == "content"
```

## testing/function-based-tests

**Location:** `agent-os/standards/testing/function-based-tests.md`

**Application:**
- All tests in `tests/test_pydantic_agent.py` are function-based (`def test_...()`)
- No test classes (no `class TestFoo:`)
- Each function tests one behavior
- Use fixtures for setup, not class methods

**Rationale:**
- Simpler and more discoverable
- Encourages small, focused tests
- Works seamlessly with pytest fixtures
- Easier for agents to read and modify

**Example:**
```python
def test_punie_agent_satisfies_agent_protocol():
    """PunieAgent should satisfy the ACP Agent protocol."""
    agent = PunieAgent(...)
    assert isinstance(agent, Agent)

def test_acp_deps_is_frozen():
    """ACPDeps should be a frozen dataclass."""
    deps = ACPDeps(...)
    with pytest.raises(FrozenInstanceError):
        deps.session_id = "new-id"
```

## testing/protocol-satisfaction-test

**Location:** `agent-os/standards/testing/protocol-satisfaction-test.md`

**Application:**
- **First test** in `tests/test_pydantic_agent.py` must be protocol satisfaction test
- Use `isinstance(PunieAgent(...), Agent)` to verify protocol compliance
- Relies on `@runtime_checkable` decorator on `Agent` protocol

**Why First:**
- If this fails, all other tests are meaningless
- Documents intent: "PunieAgent is an Agent"
- Fast feedback on protocol conformance

**Example:**
```python
from punie.acp import Agent
from punie.agent import PunieAgent

def test_punie_agent_satisfies_agent_protocol():
    """PunieAgent must satisfy the ACP Agent protocol.

    This test is first because protocol satisfaction is the fundamental
    requirement. If this fails, PunieAgent cannot be used with ACP.
    """
    fake_client = FakeClient()
    agent = PunieAgent(...)

    # Runtime protocol check
    assert isinstance(agent, Agent)
```

## testing/sybil-doctest

**Location:** `agent-os/standards/testing/sybil-doctest.md`

**Application:**
- Add docstring examples to `ACPDeps`, `ACPToolset`, `PunieAgent`
- Examples will be tested via Sybil during pytest runs
- Examples should be copy-pasteable and self-contained

**Scope:**
Docstring examples are optional for Phase 3.2 (internal types). Priority is unit tests. Add examples in Phase 3.3+ when types become user-facing.

**Example (if added):**
```python
class ACPToolset(AbstractToolset[ACPDeps]):
    """Pydantic AI toolset that bridges to ACP Client Protocol.

    Example:
        >>> from punie.testing import FakeClient
        >>> fake = FakeClient(files={"/test.py": "print('hello')"})
        >>> deps = ACPDeps(client_conn=fake, session_id="s1", tracker=ToolCallTracker())
        >>> # Use in Pydantic AI agent
    """
```

## Summary

| Standard | Key Application |
|----------|----------------|
| **agent-verification** | Use Astral skills (`astral:ty`, `astral:ruff`), not justfile |
| **protocol-first-design** | PunieAgent conforms to ACP Agent protocol |
| **frozen-dataclass-services** | ACPDeps is frozen dataclass |
| **fakes-over-mocks** | Use FakeClient for all testing |
| **function-based-tests** | All tests are functions, not classes |
| **protocol-satisfaction-test** | First test verifies `isinstance(agent, Agent)` |
| **sybil-doctest** | Add docstring examples (optional for Phase 3.2) |

These standards ensure the implementation is:
- **Type-safe** (protocol-first-design)
- **Testable** (fakes-over-mocks, function-based-tests)
- **Verifiable** (agent-verification, protocol-satisfaction-test)
- **Maintainable** (frozen-dataclass-services)
