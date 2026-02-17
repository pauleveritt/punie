# Standards Applied to Phase 29

This implementation follows these Agent OS standards:

---

## 1. Agent Verification Standard

### Purpose

Agents should use Astral tools directly via skills rather than convenience wrappers like justfile recipes. This ensures agents get the full context and guidance these tools provide.

### Rationale

- **Justfile recipes** (`just test`, `just lint`) are convenience wrappers for humans and CI/CD
- **Astral skills** (`astral:ruff`, `astral:ty`, `astral:uv`) provide richer context and guidance for agents
- **Direct tool usage** gives better error messages and actionable diagnostics
- **ty LSP** provides real-time type checking feedback during development
- **Skills can provide guidance** on how to fix issues, not just report them

### Rules for Verification

#### Type Checking

**DO:**
- Use the `astral:ty` skill to check types and get guidance
- Pay attention to ty LSP diagnostics as they appear in tool results
- Read and understand type errors before attempting fixes

**DON'T:**
- Run `just lint` or `just typecheck` through Bash
- Ignore ty diagnostics that appear during development

#### Linting and Formatting

**DO:**
- Use the `astral:ruff` skill to check, format, and fix code
- Let ruff guide you on style and error fixes

**DON'T:**
- Run `just lint` or `just format` through Bash
- Apply fixes without understanding what ruff is correcting

#### Testing

**DO:**
- Use `uv run pytest` directly with clear descriptions
- Use `astral:uv` skill if you need guidance on pytest or uv usage
- Specify test paths clearly (e.g., `uv run pytest tests/` not `just test`)

**DON'T:**
- Run `just test` through Bash
- Use justfile test recipes in verification steps

---

## 2. Function-Based Tests

Write tests as functions, never classes.

```python
# CORRECT
def test_user_can_login_with_valid_credentials():
    """Test successful login."""
    user = create_user(password="secret")
    assert user.login("secret") is True

def test_user_cannot_login_with_wrong_password():
    """Test login failure."""
    user = create_user(password="secret")
    assert user.login("wrong") is False
```

```python
# WRONG - Do not do this
class TestUserLogin:
    def test_valid_credentials(self):
        ...
    def test_wrong_password(self):
        ...
```

### Why Functions

- Simpler, less boilerplate
- No `self` parameter noise
- Fixtures work more naturally
- Pytest's native style

### Rules

- Name: `test_<what>_<scenario>()`
- One assertion focus per test
- Use fixtures for shared setup, not class `setUp`

---

## 3. Protocol-First Design

Define service interfaces as `@runtime_checkable` Protocols before implementations.

### Structure

```
service_name/
├── __init__.py    # Export protocol and implementation
├── types.py       # Protocol definition
└── models.py      # Concrete implementation
```

### Protocol Definition (types.py)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class MyServiceProtocol(Protocol):
    """One-line description of what this service does."""

    def __call__(self, input: InputType) -> OutputType:
        """Method docstring with Args/Returns."""
        ...
```

### Why

- **Testability**: Swap implementations with fakes
- **Type Safety**: Catch breaking changes at dev time
- **Multiple Implementations**: Different contexts (Sphinx, Django, etc.)

### Rules

- Always use `@runtime_checkable` for `isinstance()` checks in tests
- Protocol goes in `types.py`, implementation in `models.py`
- First test: verify implementation satisfies protocol

---

## 4. Fakes Over Mocks

Use simple dataclass fakes, not mock frameworks.

```python
@dataclass
class FakeDatabase:
    """Fake database - predictable, no side effects."""
    _results: dict[str, list[dict]] = field(default_factory=dict)

    def query(self, sql: str) -> list[dict]:
        return self._results.get(sql, [])

def test_service_uses_database():
    fake_db = FakeDatabase(_results={"SELECT * FROM users": [{"id": 1}]})
    service = UserService(db=fake_db)
    assert len(service.get_users()) == 1
```

### Why Fakes

- **Simplicity**: Plain Python classes, no magic
- **Refactor-resilient**: Fakes follow protocol; mocks break on rename
- **Predictable**: Explicit state, no surprising behavior

### Rules

- Fake should implement the same Protocol as the real service
- Keep fakes simple—avoid complex state machines
- Store fakes in test files or `tests/fakes/` if shared
- Never use `unittest.mock` or `pytest-mock` unless absolutely necessary

---

## Application to Phase 29

### Agent Verification

**Verification steps use:**
- `astral:ty` skill for type checking (not `just lint`)
- `astral:ruff` skill for linting/formatting (not `just format`)
- `uv run pytest tests/test_toad_client.py -v` for testing (not `just test`)

### Function-Based Tests

**All tests are functions:**
```python
def test_create_toad_session_connects_and_handshakes():
    """Test session creation performs ACP handshake."""
    ...

def test_send_prompt_stream_calls_callback_for_each_chunk():
    """Test streaming chunks invoke callback."""
    ...
```

**No test classes** - violates function-based-tests standard

### Protocol-First Design

**Callback protocols defined:**
```python
# Implicit protocol for callbacks
OnUpdateCallback = Callable[[dict[str, Any]], None]
OnChunkCallback = Callable[[str, dict[str, Any]], None]
OnToolCallCallback = Callable[[str, dict[str, Any]], None]
```

While we don't create a full Protocol class for simple callbacks, we document the expected signature clearly in docstrings.

### Fakes Over Mocks

**Use fake callbacks in tests:**
```python
@pytest.fixture
def fake_callback():
    """Fake callback that records calls."""
    calls = []
    def callback(update_type: str, content: dict):
        calls.append((update_type, content))
    callback.calls = calls
    return callback
```

**Not using `unittest.mock.Mock` or `pytest-mock`** - violates fakes-over-mocks standard

---

## Summary

Phase 29 follows all four standards:
1. ✅ Verification uses Astral skills (not justfile)
2. ✅ Tests are functions (not classes)
3. ✅ Callback protocols defined (type hints + docstrings)
4. ✅ Fake callbacks for testing (not mocks)
