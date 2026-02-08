# Applicable Standards: Session Registration

This spec follows 5 Agent OS standards:

## 1. frozen-dataclass-services

**Standard:** Use `@dataclass(frozen=True)` for service objects to ensure immutability and value semantics.

**Application:**
- `SessionState` is frozen dataclass holding session-scoped cached state
- Fields: `catalog`, `toolset`, `agent`, `discovery_tier`
- No setters, no mutation, only construction
- Immutable for entire session lifetime

**Example:**
```python
@dataclass(frozen=True)
class SessionState:
    catalog: ToolCatalog | None          # None if Tier 2/3 fallback
    toolset: FunctionToolset[ACPDeps]
    agent: PydanticAgent[ACPDeps, str]
    discovery_tier: int                  # 1=catalog, 2=capabilities, 3=default
```

**Tests:**
- `test_session_state_is_frozen()` — verifies frozen=True
- `test_session_state_stores_fields()` — verifies field storage

**Files Affected:**
- `src/punie/agent/session.py` (new)

## 2. function-based-tests

**Standard:** Write tests as flat functions, not classes. Use descriptive names, flat structure, and avoid setup/teardown methods.

**Application:**
- All ~16 tests in `test_session_registration.py` are functions
- No `class Test*` patterns
- No `setUp()`/`tearDown()` methods
- Each test is self-contained and readable

**Example:**
```python
async def test_new_session_discovers_tools_once():
    """new_session() calls discover_tools() exactly once."""
    fake = FakeClient(tool_catalog=[...])
    agent = PunieAgent(client=fake)

    await agent.new_session("session-1")

    assert len(fake.discover_tools_calls) == 1
    assert fake.discover_tools_calls[0] == "session-1"
```

**Test List (All Functions):**
1. `test_session_state_is_frozen()`
2. `test_session_state_stores_fields()`
3. `test_new_session_discovers_tools_once()`
4. `test_new_session_caches_session_state()`
5. `test_new_session_records_discovery_tier()`
6. `test_new_session_tier_2_fallback()`
7. `test_new_session_tier_3_fallback()`
8. `test_new_session_graceful_failure()`
9. `test_prompt_uses_cached_agent()`
10. `test_prompt_does_not_re_discover()`
11. `test_prompt_multiple_calls_single_discovery()`
12. `test_prompt_lazy_fallback_unknown_session()`
13. `test_prompt_lazy_fallback_caches_result()`
14. `test_legacy_agent_skips_registration()`
15. `test_legacy_agent_still_works()`
16. `test_fake_client_tracks_discover_calls()`

**Files Affected:**
- `tests/test_session_registration.py` (new)

## 3. fakes-over-mocks

**Standard:** Use hand-written fake implementations instead of mock frameworks for testing. Fakes accumulate reusable test infrastructure.

**Application:**
- Extend `FakeClient` with `discover_tools_calls: list[str]` field
- Tracks which session_ids triggered `discover_tools()` calls
- No `unittest.mock` or `pytest-mock` usage
- Other tests can reuse this tracking capability

**FakeClient Addition:**
```python
class FakeClient:
    discover_tools_calls: list[str]  # Track session_ids

    async def discover_tools(self, session_id, **kwargs) -> dict:
        self.discover_tools_calls.append(session_id)
        return {"tools": self.tool_catalog}
```

**Benefit:** Tests can assert discovery happens exactly once per session by checking `len(fake.discover_tools_calls)`.

**Files Affected:**
- `src/punie/testing/fakes.py` (modified)

## 4. sybil-doctest

**Standard:** Use Sybil for doctest integration in README.md and docstrings. Doctests serve as both documentation and tests.

**Application:**
- Add docstring example to `SessionState` showing typical construction
- Add docstring to `_discover_and_build_toolset()` showing workflow
- Examples show session registration pattern
- Sybil runs these as tests automatically

**Example Docstring:**
```python
@dataclass(frozen=True)
class SessionState:
    """Immutable session-scoped cached state.

    >>> state = SessionState(
    ...     catalog=None,
    ...     toolset=some_toolset,
    ...     agent=some_agent,
    ...     discovery_tier=3
    ... )
    >>> state.discovery_tier
    3
    """
    catalog: ToolCatalog | None
    toolset: FunctionToolset[ACPDeps]
    agent: PydanticAgent[ACPDeps, str]
    discovery_tier: int
```

**Files With Doctests:**
- `src/punie/agent/session.py` — SessionState
- `src/punie/agent/adapter.py` — _discover_and_build_toolset()

## 5. agent-verification

**Standard:** Use `astral:ty` and `astral:ruff` skills for quality verification before completion.

**Application:**
- Task 10 explicitly runs `astral:ty` to catch type errors
- Task 10 explicitly runs `astral:ruff` to catch lint issues
- All new code in `session.py`, modified code in `adapter.py`, `fakes.py`, `__init__.py` must pass both checks
- No merge until both skills report success

**Files Affected:**
- `src/punie/agent/session.py` (new)
- `src/punie/agent/adapter.py` (modified)
- `src/punie/agent/__init__.py` (modified)
- `src/punie/testing/fakes.py` (modified)
- `tests/test_session_registration.py` (new)

## Standards Summary Table

| Standard | Primary Files | Key Requirement |
|----------|---------------|-----------------|
| frozen-dataclass-services | `session.py` | SessionState is frozen dataclass |
| function-based-tests | `test_session_registration.py` | 16 function tests, no classes |
| fakes-over-mocks | `fakes.py`, tests | Extend FakeClient tracking, no mock framework |
| sybil-doctest | `session.py`, `adapter.py` | Docstring examples are runnable tests |
| agent-verification | All source files | Pass astral:ty and astral:ruff |

## Compliance Checklist

- [ ] SessionState is frozen dataclass (frozen-dataclass-services)
- [ ] All ~16 tests are functions (function-based-tests)
- [ ] FakeClient extended, no mocks (fakes-over-mocks)
- [ ] Docstring examples added (sybil-doctest)
- [ ] Type checking passes (agent-verification)
- [ ] Linting passes (agent-verification)
