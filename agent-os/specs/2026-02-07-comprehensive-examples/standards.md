# Standards: Comprehensive Examples

This spec applies the following project standards:

## agent-verification

**Location:** `agent-os/standards/agent-verification.md`

- Examples serve as both documentation and verification
- Each example has assertions that verify behavior
- Examples are auto-discovered and tested by `tests/test_examples.py`
- Standalone execution confirms examples work outside test harness

## sybil-doctest

**Location:** `agent-os/standards/sybil-doctest.md`

- Module docstrings in examples may contain testable code snippets
- Sybil integration allows documentation to serve as verification
- Examples bridge the gap between README.md and unit tests

## function-based-tests

**Location:** `agent-os/standards/function-based-tests.md`

- Each example uses a `main()` function, not a class
- Direct, procedural flow from setup → action → assertion
- No inheritance hierarchy or complex test class structure
- Examples are functions that happen to be tested, not test functions

## fakes-over-mocks

**Location:** `agent-os/standards/fakes-over-mocks.md`

- Example 07 uses `FakeAgent` and `FakeClient` from `tests.acp_helpers`
- No mock.patch or mock.Mock usage
- Real ACP protocol flow over in-process TCP loopback
- Fakes implement full behavior, not just stubbed methods

## Additional Conventions

- **Numbered ordering** — `01_` through `09_` for clear progression
- **Self-contained** — No external dependencies beyond ACP SDK and test helpers
- **Aspirational marking** — Examples 08 and 09 clearly document future functionality in docstrings
- **Import discipline** — Example 07 handles `tests.acp_helpers` import with sys.path fallback for standalone execution
