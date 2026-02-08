# Standards Applied in Test-Driven Refactoring

This spec applies the following Agent OS standards:

## agent-verification

**Standard:** Testing utilities should satisfy the protocols they implement, verified via runtime checks.

**Application:**
- Add `@runtime_checkable` decorator to `Agent` and `Client` protocols in `src/punie/acp/interfaces.py`
- Create `tests/test_protocol_satisfaction.py` with `isinstance()` tests:
  - `test_fake_agent_satisfies_agent_protocol()`
  - `test_fake_client_satisfies_client_protocol()`
- Future responders also get protocol satisfaction tests

**Rationale:** Runtime verification is stronger than type-checking alone. If protocols change, tests fail immediately.

## function-based-tests

**Standard:** Write test functions, not test classes.

**Application:**
- All 7 tests in `tests/test_acp_sdk.py` are already functions
- All new tests (`test_protocol_satisfaction.py`, `test_schema.py`, etc.) use functions
- No test classes introduced during refactoring

**Rationale:** Functions are simpler, more explicit, and avoid hidden state in test class attributes.

## fakes-over-mocks

**Standard:** Prefer handwritten fakes to mock framework magic.

**Application:**
- `FakeAgent` and `FakeClient` are handwritten classes, not `unittest.mock.Mock`
- `LoopbackServer` implements real WebSocket behavior
- `ModelResponder` fakes (`CannedResponder`, `ErrorResponder`, etc.) are concrete classes
- No use of `@patch` decorators or `MagicMock`

**Rationale:** Fakes are type-checkable, discoverable, and understandable. Mocks hide behavior and are fragile to implementation changes.

## protocol-satisfaction-test

**Standard:** Every fake that claims to implement a protocol must have an `isinstance()` test proving it.

**Application:**
- `tests/test_protocol_satisfaction.py`:
  - `test_fake_agent_satisfies_agent_protocol()` — proves `FakeAgent` satisfies `Agent`
  - `test_fake_client_satisfies_client_protocol()` — proves `FakeClient` satisfies `Client`
- `tests/test_model_responder.py`:
  - Protocol satisfaction tests for each `ModelResponder` implementation

**Rationale:** Protocols are contracts. Tests verify fakes uphold contracts at runtime, not just at type-check time.

## sybil-doctest

**Standard:** Use Sybil for doctest integration in README.md and docstrings.

**Application:**
- Docstrings in `src/punie/testing/` can reference fakes in examples
- Future README.md examples can use `from punie.testing import FakeAgent`
- Pytest + Sybil integration allows doctests to run alongside regular tests

**Rationale:** Documentation examples that actually run catch documentation drift and serve as executable specifications.

## Not Applied (Explicitly Out of Scope)

### docstring-first
**Reason:** This is a refactoring task, not new feature development. Existing code docstrings preserved as-is. Docstrings for new testing utilities added in Task 6.

### readme-doctest
**Reason:** README.md updates deferred until Phase 3 (Pydantic AI integration). Current README focuses on ACP basics, not testing utilities.

## Summary

This refactoring prioritizes:
1. **Verification over assumption** (agent-verification, protocol-satisfaction-test)
2. **Simplicity over magic** (function-based-tests, fakes-over-mocks)
3. **Executable documentation** (sybil-doctest for future examples)

The standards guide implementation decisions (e.g., `@runtime_checkable` required, no mocks allowed) and define success criteria (protocol satisfaction tests must exist and pass).
