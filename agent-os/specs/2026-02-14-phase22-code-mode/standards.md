# Phase 22 Code Mode — Standards Applied

This spec follows Agent OS standards for code quality and architecture.

## agent-verification

**Applies to:** All new Python code (stubs.py, monty_runner.py, test files)

**Usage:**
```bash
# Type checking
uv run ty check src/punie/agent/stubs.py
uv run ty check src/punie/agent/monty_runner.py

# Linting and formatting
uv run ruff check src/punie/agent/
uv run ruff format src/punie/agent/
```

**Requirements:**
- No type errors (strict mode)
- All functions have return type hints
- All parameters have type hints
- No `Any` types (use `object` or specific unions)
- Docstrings for all public functions

## frozen-dataclass-services

**Applies to:** Monty runner dependencies, external function registration

**Pattern:**
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ExternalFunctions:
    """Registry of external functions available in sandbox."""
    read_file: Callable[[str], str]
    write_file: Callable[[str, str], None]
    run_command: Callable[[str, list[str] | None, str | None], str]
```

**Why frozen:**
- Immutable service configuration
- Thread-safe (if we add concurrency later)
- Clear lifecycle (created once, used many times)

## function-based-tests

**Applies to:** All new test files

**Pattern:**
```python
# tests/test_stubs.py
def test_generate_stubs_reads_toolset():
    """Stubs include all functions from toolset."""
    stubs = generate_stubs()
    assert "def read_file(path: str) -> str:" in stubs

def test_stubs_exclude_ctx_parameter():
    """Generated stubs don't include RunContext parameter."""
    stubs = generate_stubs()
    assert "RunContext" not in stubs
```

**Why not classes:**
- Simpler test discovery
- No inheritance confusion
- Easier to run individual tests
- Aligns with Pytest's recommendation

## fakes-over-mocks

**Applies to:** Testing Monty runner, testing execute_code tool

**Pattern:**
```python
# tests/test_monty_runner.py
def fake_read_file(path: str) -> str:
    """Fake file reader for testing."""
    if path == "test.txt":
        return "test content"
    raise FileNotFoundError(path)

def test_monty_executes_code_with_external_functions():
    """Monty runs code and calls external functions."""
    code = 'content = read_file("test.txt"); print(content)'
    result = run_monty(code, read_file=fake_read_file)
    assert result == "test content\n"
```

**Why not mocks:**
- Fakes test behavior, not implementation
- More maintainable (no fragile assertions like `mock.assert_called_once_with(...)`)
- Self-documenting (fake_read_file shows what's expected)
- Easier to debug (fakes can print, mocks are opaque)

## Additional Standards

### Error handling
- Use specific exceptions (not bare `except:`)
- Include context in error messages
- Log errors with structured data (not print statements)

### Documentation
- README.md for each script (scripts/convert_to_code_format.py, etc.)
- Docstrings for all public APIs
- Comments for non-obvious logic (e.g., Monty start/resume pattern)

### Training data validation
- All generated Python code must pass `ast.parse()`
- No syntax errors, no incomplete expressions
- Validate before writing to JSONL files

### Naming conventions
- Scripts: `verb_object.py` (e.g., `convert_to_code_format.py`)
- Tests: `test_module.py` (e.g., `test_stubs.py`)
- Functions: `verb_object()` (e.g., `generate_stubs()`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `PUNIE_INSTRUCTIONS`)
