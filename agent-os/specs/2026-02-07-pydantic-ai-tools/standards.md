# Standards Applied

This implementation follows these Punie project standards:

## agent-verification

**What:** All agent features must have executable verification tests that simulate real-world usage patterns.

**Application:**
- Each new tool has dedicated tests in `test_pydantic_agent.py`
- Permission flow tested with both allowed and denied outcomes
- Terminal lifecycle tested through FakeClient state management
- Integration test verifies toolset composition

## protocol-first-design

**What:** Design around protocols (structural interfaces) rather than concrete inheritance hierarchies.

**Application:**
- Tools use `Client` protocol from `interfaces.py`, not concrete implementations
- FakeClient implements `Client` protocol for testing
- `RunContext[ACPDeps]` provides dependency injection via protocol
- Terminal operations work with any `Client` implementation

## frozen-dataclass-services

**What:** Use frozen dataclasses for immutable service configuration and data transfer objects.

**Application:**
- `ACPDeps` is a frozen dataclass holding client, session, tracker
- `FakeTerminal` is a frozen dataclass holding terminal state
- Permission responses use frozen dataclasses (`AllowedOutcome`, `DeniedOutcome`)
- Tool call locations use frozen dataclass (`ToolCallLocation`)

## fakes-over-mocks

**What:** Prefer fake implementations with real behavior over mock frameworks.

**Application:**
- `FakeClient` provides real in-memory implementations, not mocks
- Terminal methods store actual state in `self.terminals` dict
- Permission queue uses real `AllowedOutcome`/`DeniedOutcome` instances
- File operations modify actual `self.files` dict

## function-based-tests

**What:** Write tests as functions, never classes.

**Application:**
- All new tests are `async def test_*()` functions
- No test classes or setUp/tearDown methods
- Direct construction of dependencies (no inheritance needed)
- Each test is independent and self-contained

## sybil-doctest

**What:** Use Sybil for doctest integration in README.md and docstrings.

**Application:**
- Tool docstrings include usage examples as doctests
- README.md examples are executable via Sybil
- Test suite automatically validates documentation examples
- Keeps documentation in sync with implementation
