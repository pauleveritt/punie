# Applicable Standards: Dynamic Tool Discovery

This spec follows 7 Agent OS standards:

## 1. agent-verification

**Standard:** Use `astral:ty` and `astral:ruff` skills for quality verification before completion.

**Application:**
- Task 11 explicitly runs `astral:ty` to catch type errors
- Task 11 explicitly runs `astral:ruff` to catch lint issues
- All new code in `discovery.py`, `interfaces.py`, `toolset.py`, `adapter.py` must pass both checks
- No merge until both skills report success

**Files Affected:**
- `src/punie/agent/discovery.py` (new)
- `src/punie/acp/interfaces.py` (modified)
- `src/punie/agent/toolset.py` (modified)
- `src/punie/agent/adapter.py` (modified)
- `src/punie/agent/factory.py` (modified)
- `src/punie/testing/fakes.py` (modified)

## 2. protocol-first-design

**Standard:** Define protocols (abstract interfaces) before implementations. Implementations satisfy protocols via structural typing.

**Application:**
- `discover_tools()` added to `Client` protocol in `interfaces.py` first
- `FakeClient` and real IDE client both satisfy the same protocol
- No coupling between protocol definition and implementation details
- Protocol returns `dict[str, Any]` (schema-agnostic), agent layer does parsing

**Key Protocol Addition:**
```python
async def discover_tools(
    self, session_id: str, **kwargs: Any
) -> dict[str, Any]: ...
```

**Why Dict Return:**
- Keeps protocol layer decoupled from agent layer types
- IDE can evolve schema without protocol changes
- Agent layer owns ToolCatalog parsing logic

## 3. frozen-dataclass-services

**Standard:** Use `@dataclass(frozen=True)` for service objects to ensure immutability and value semantics.

**Application:**
- `ToolDescriptor` is frozen dataclass (Task 2)
- `ToolCatalog` is frozen dataclass (Task 2)
- Both use tuples instead of lists for collection fields
- No setters, no mutation, only construction

**Example:**
```python
@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    kind: str
    description: str
    parameters: dict[str, Any]
    requires_permission: bool = False
    categories: tuple[str, ...] = ()  # tuple, not list

@dataclass(frozen=True)
class ToolCatalog:
    tools: tuple[ToolDescriptor, ...]  # tuple, not list
```

**Tests:**
- `test_tool_descriptor_is_frozen()` — verifies frozen=True
- `test_tool_catalog_is_frozen()` — verifies frozen=True

## 4. protocol-satisfaction-test

**Standard:** Write tests that verify implementations satisfy protocols via structural typing checks.

**Application:**
- `test_fake_client_discover_tools()` verifies `FakeClient.discover_tools()` satisfies Client protocol signature
- Tests call protocol methods through protocol-typed references (not concrete types)
- Uses `isinstance()` or duck-typing checks, not inheritance

**Example Test Pattern:**
```python
def test_fake_client_discover_tools():
    client: Client = FakeClient(tool_catalog=[...])  # Type as protocol
    result = await client.discover_tools(session_id="test")
    assert isinstance(result, dict)
    assert "tools" in result
```

## 5. fakes-over-mocks

**Standard:** Use hand-written fake implementations instead of mock frameworks for testing. Fakes accumulate reusable test infrastructure.

**Application:**
- Extend `FakeClient` with `discover_tools()` method (Task 7)
- Add `tool_catalog` field to configure fake's tool list
- Add `capabilities` parameter for capability-based fallback tests
- No `unittest.mock` or `pytest-mock` usage

**FakeClient Additions:**
```python
class FakeClient:
    tool_catalog: list[dict]  # Configurable tool descriptors
    capabilities: ClientCapabilities | None

    async def discover_tools(self, session_id, **kwargs) -> dict:
        return {"tools": self.tool_catalog}
```

**Benefit:** Other tests can reuse `FakeClient` with custom catalogs without duplicating setup.

## 6. function-based-tests

**Standard:** Write tests as flat functions, not classes. Use descriptive names, flat structure, and avoid setup/teardown methods.

**Application:**
- All 14 tests in `test_discovery.py` are functions (Task 8)
- No `class Test*` patterns
- No `setUp()`/`tearDown()` methods
- Each test is self-contained and readable

**Example:**
```python
def test_tool_catalog_by_name():
    """ToolCatalog.by_name() returns matching descriptor."""
    descriptor = ToolDescriptor(name="read_file", kind="read", ...)
    catalog = ToolCatalog(tools=(descriptor,))
    assert catalog.by_name("read_file") == descriptor
    assert catalog.by_name("unknown") is None
```

**Test List (All Functions):**
1. `test_tool_descriptor_is_frozen()`
2. `test_tool_catalog_is_frozen()`
3. `test_tool_catalog_by_name()`
4. `test_tool_catalog_by_kind()`
5. `test_tool_catalog_by_category()`
6. `test_create_toolset_from_catalog_known_tools()`
7. `test_create_toolset_from_catalog_unknown_tools()`
8. `test_create_toolset_from_capabilities_fs_only()`
9. `test_create_toolset_from_capabilities_all()`
10. `test_adapter_stores_client_capabilities()`
11. `test_adapter_uses_discovery_when_available()`
12. `test_adapter_falls_back_to_capabilities()`
13. `test_adapter_falls_back_to_defaults()`
14. `test_fake_client_discover_tools()`

## 7. sybil-doctest

**Standard:** Use Sybil for doctest integration in README.md and docstrings. Doctests serve as both documentation and tests.

**Application:**
- Add docstring examples to `ToolCatalog.by_name()`, `by_kind()`, `by_category()` methods
- Add docstring example to `create_toolset_from_catalog()`
- Examples show typical usage patterns
- Sybil runs these as tests automatically

**Example Docstring:**
```python
def by_name(self, name: str) -> ToolDescriptor | None:
    """Look up a tool descriptor by name.

    >>> descriptor = ToolDescriptor(name="read_file", kind="read",
    ...                              description="Read file", parameters={})
    >>> catalog = ToolCatalog(tools=(descriptor,))
    >>> catalog.by_name("read_file").name
    'read_file'
    >>> catalog.by_name("unknown") is None
    True
    """
    ...
```

**Files With Doctests:**
- `src/punie/agent/discovery.py` — ToolCatalog methods
- `src/punie/agent/toolset.py` — create_toolset_from_catalog()

## Standards Summary Table

| Standard | Primary Files | Key Requirement |
|----------|---------------|-----------------|
| agent-verification | All source files | Pass astral:ty and astral:ruff |
| protocol-first-design | `interfaces.py` | Protocol defines contract, not implementation |
| frozen-dataclass-services | `discovery.py` | Use frozen dataclasses for ToolDescriptor, ToolCatalog |
| protocol-satisfaction-test | `test_discovery.py` | Verify FakeClient satisfies Client protocol |
| fakes-over-mocks | `fakes.py`, `test_discovery.py` | Extend FakeClient, no mock framework |
| function-based-tests | `test_discovery.py` | 14 function tests, no classes |
| sybil-doctest | `discovery.py`, `toolset.py` | Docstring examples are runnable tests |

## Compliance Checklist

- [ ] Type checking passes (agent-verification)
- [ ] Linting passes (agent-verification)
- [ ] `discover_tools()` in Client protocol (protocol-first-design)
- [ ] ToolDescriptor is frozen dataclass (frozen-dataclass-services)
- [ ] ToolCatalog is frozen dataclass (frozen-dataclass-services)
- [ ] Protocol satisfaction test exists (protocol-satisfaction-test)
- [ ] FakeClient extended, no mocks (fakes-over-mocks)
- [ ] All 14 tests are functions (function-based-tests)
- [ ] Docstring examples added (sybil-doctest)
