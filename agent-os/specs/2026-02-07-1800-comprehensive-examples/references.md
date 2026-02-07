# References

## Primary Reference: tdom-svcs Examples Pattern

**Location:** `/Users/pauleveritt/projects/t-strings/tdom-svcs/`

### Key Files to Reference

1. **`examples/` directory structure**
   - Each example module has a `main()` function
   - Examples are self-testing with assertions
   - Can run standalone: `python examples/hello_world.py`

2. **`tests/test_examples.py`**
   - Parametrized test that auto-discovers examples
   - Dynamically imports example modules
   - Calls `main()` if it exists
   - Supports both sync and async `main()` via `anyio.run()`

3. **`pyproject.toml`**
   - `pythonpath = ["examples"]` makes examples importable
   - `testpaths` includes examples for pytest discovery

4. **Root `conftest.py`**
   - Excludes `examples/` from Sybil collection
   - Prevents duplicate test collection

### Pattern Benefits

- **Self-documenting:** Examples show actual usage
- **Self-testing:** Assertions verify correctness
- **Dual-purpose:** Run standalone or via pytest
- **Auto-discovery:** No manual test registration
- **Scalable:** Add examples by creating new `.py` files

### Example Structure

```python
"""Example description."""

import relevant_package


def main() -> None:
    """Execute the example with assertions."""
    # Example code here
    result = do_something()
    assert result == expected
    # More assertions...


if __name__ == "__main__":
    main()
    print("Example passed!")
```

### Test Runner Pattern

```python
from pathlib import Path
import importlib.util
import pytest
import anyio

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

def discover_examples():
    """Find all example modules with main() functions."""
    examples = []
    for py_file in EXAMPLES_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        examples.append(py_file.stem)
    return examples

@pytest.mark.parametrize("example_name", discover_examples())
def test_example(example_name: str):
    """Run each example's main() function."""
    spec = importlib.util.spec_from_file_location(
        example_name,
        EXAMPLES_DIR / f"{example_name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "main"):
        if inspect.iscoroutinefunction(module.main):
            anyio.run(module.main)
        else:
            module.main()
```

## Related Patterns

- **Testing standards:** Function-based tests, Sybil integration
- **Verification standards:** Use Astral skills for quality checks
- **Documentation:** Examples complement formal docs with runnable code
