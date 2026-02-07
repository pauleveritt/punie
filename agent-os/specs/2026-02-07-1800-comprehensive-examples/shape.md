# Shape: Comprehensive Examples

## Scope

This spec establishes the examples infrastructure for Punie by creating:
1. An `examples/` directory with a minimal hello world example
2. A parametrized test runner that auto-discovers and runs example `main()` functions
3. Configuration to make examples importable as a package

## In Scope

- Create `examples/hello_world.py` with self-testing `main()` function
- Create `tests/test_examples.py` that auto-discovers examples
- Update pyproject.toml to include examples in testpaths
- Verify examples work standalone and via pytest

## Out of Scope

- Additional examples beyond hello world (future tasks)
- Documentation examples (covered separately)
- Complex example infrastructure (keep it simple)

## Key Decisions

### 1. Follow tdom-svcs Pattern

**Decision:** Use the exact pattern from `/Users/pauleveritt/projects/t-strings/tdom-svcs/`

**Rationale:**
- Proven pattern in production use
- Examples are self-testing with assertions in `main()`
- Parametrized test runner auto-discovers examples
- Works standalone (`python examples/hello_world.py`) and in pytest

### 2. Minimal Hello World

**Decision:** Start with simplest possible example that imports punie

**Rationale:**
- Validates the examples infrastructure works
- Provides template for future examples
- Low barrier to entry for contributors
- Follows "crawl, walk, run" approach

### 3. Support Both Sync and Async

**Decision:** Test runner uses `anyio.run()` for async `main()` functions

**Rationale:**
- Future-proofs for async examples
- Follows tdom-svcs pattern
- Minimal overhead for sync examples

### 4. Exclude Examples from Sybil

**Decision:** Update root conftest.py to exclude `examples/` from Sybil collection

**Rationale:**
- Examples are tested via `tests/test_examples.py`
- Prevents duplicate test collection
- Follows tdom-svcs pattern

## Context

This builds on task 1.1 (project structure) which already configured:
- `pythonpath = ["examples"]` in pyproject.toml
- Basic pytest and Sybil setup
- Project directory structure

The examples pattern is critical for:
- Demonstrating Punie usage
- Testing real-world scenarios
- Providing copy-paste starting points
- Validating API design
