# Plan: Create Comprehensive Examples (Roadmap 1.2)

## Context

With project structure complete (1.1), Punie needs a minimal "hello world" example in `examples/` following the tdom-svcs pattern. This establishes the examples infrastructure — the `examples/` directory on pythonpath, a `main()` function pattern with assertions, and a parametrized test runner that auto-discovers examples. Future examples will build on this foundation.

## Spec Folder

`agent-os/specs/2026-02-07-1800-comprehensive-examples/`

## Standards Applied

- **agent-verification** — Verify using Astral skills, not justfile recipes
- **testing/function-based-tests** — Tests as functions, not classes
- **testing/sybil-doctest** — Sybil for README and docstring testing

## Reference Project

`/Users/pauleveritt/projects/t-strings/tdom-svcs/` — examples/ directory pattern:
- Each example has a `main()` function with assertions (self-testing)
- `tests/test_examples.py` auto-discovers and runs all example `main()` functions
- `pythonpath = ["examples"]` in pyproject.toml makes examples importable
- Root conftest.py excludes `examples/` from Sybil collection

## Tasks

### Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-07-1800-comprehensive-examples/` with:
- `plan.md` — This plan
- `shape.md` — Scope, decisions, context
- `standards.md` — Full content of 3 applied standards
- `references.md` — Pointer to tdom-svcs examples/ pattern

### Task 2: Create Hello World Example

| File | Content |
|------|---------|
| `examples/__init__.py` | Empty (makes examples a package) |
| `examples/hello_world.py` | Simple `main()` function that exercises punie import and asserts correctness |

The hello_world.py pattern (following tdom-svcs):
```python
"""Hello world example for Punie."""

import punie


def main() -> None:
    """Verify basic punie package access."""
    assert punie.__name__ == "punie"
    greeting = f"Hello from {punie.__name__}!"
    assert "Hello" in greeting
    assert "punie" in greeting


if __name__ == "__main__":
    main()
    print("Hello world example passed!")
```

### Task 3: Create Example Test Runner

| File | Content |
|------|---------|
| `tests/test_examples.py` | Parametrized test that auto-discovers example modules with `main()` |

Following tdom-svcs `tests/test_examples.py` pattern:
- Scan `examples/` for `.py` files (excluding `__init__.py`)
- Import each module dynamically
- Call `main()` if it exists
- Support async `main()` via `anyio.run()`

### Task 4: Update pyproject.toml

Add `"examples"` to `testpaths` so pytest can discover tests in examples if needed later:
```toml
testpaths = ["tests", "src", "examples"]
```

**Note:** `pythonpath = ["examples"]` is already configured from task 1.1.

### Task 5: Verify

1. Run `uv run pytest tests/test_examples.py -v` — hello_world example passes
2. Run `uv run pytest` — full suite passes (including existing test + example runner)
3. Use `astral:ruff` skill to check linting
4. Use `astral:ty` skill to check types
5. Run `python examples/hello_world.py` directly — works standalone

## Files Summary

**4 files to create**, **1 file to modify** (pyproject.toml)
