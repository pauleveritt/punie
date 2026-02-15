# Phase 24 Standards

## Applied Standards from agent-os/standards/

### 1. agent-verification.md
**Principle**: External functions must be verifiable through fakes in tests.

**Application in Phase 24**:
- `ruff_check()` and `pytest_run()` both have fake implementations
- Fakes return realistic `RuffResult` and `TestResult` objects
- Tests verify sandbox calls fakes correctly, not real CLI tools
- Example: `test_run_code_calls_ruff_check()` uses `fake_ruff_check`

### 2. function-based-tests.md
**Principle**: Write functions, not test classes.

**Application in Phase 24**:
- All new tests in `test_typed_tools.py`, `test_monty_runner.py` are functions
- Pattern: `def test_ruff_result_validation(): ...`
- No class-based tests introduced
- Follows existing codebase pattern (195 existing tests all function-based)

### 3. fakes-over-mocks.md
**Principle**: Use realistic fake implementations, not mocks.

**Application in Phase 24**:
```python
def fake_ruff_check(path: str) -> RuffResult:
    """Realistic fake that returns actual RuffResult objects."""
    return RuffResult(
        success=False,
        violation_count=2,
        fixable_count=1,
        violations=[
            RuffViolation(
                file="src/foo.py",
                line=10,
                column=5,
                code="E501",
                message="Line too long",
                fixable=True
            )
        ]
    )
```
- No `unittest.mock` or `mocker` fixtures
- Fakes are callable functions, not mock objects
- Fakes return real domain objects, not MagicMock

### 4. frozen-dataclass-services.md
**Principle**: Services are frozen dataclasses with dependencies injected via constructor.

**Application in Phase 24**:
```python
@dataclass(frozen=True)
class ExternalFunctions:
    """Frozen dataclass containing all external function dependencies."""
    read_file: Callable[[str], str]
    write_file: Callable[[str, str], None]
    run_command: Callable[[str], str]
    typecheck: Callable[[str], TypeCheckResult]
    ruff_check: Callable[[str], RuffResult]  # New
    pytest_run: Callable[[str], TestResult]  # New
```
- `ExternalFunctions` is frozen (immutable)
- All typed tools injected as constructor arguments
- Tests inject fakes, production injects real implementations
- No mutable state, no global variables

## Phase 24-Specific Patterns

### Typed Tool Implementation Pattern
1. **Pydantic model** for results (e.g., `RuffResult`)
2. **Parser function** (e.g., `parse_ruff_output()`)
3. **Sync bridge** (e.g., `sync_ruff_check()`) using `run_coroutine_threadsafe`
4. **Terminal workflow** (async, calls ACP)
5. **Sandbox registration** in `ExternalFunctions`
6. **Stub generation** in `stubs.py`
7. **Fake implementation** for tests

### Training Data Format (Code Mode)
- User message: Natural language query
- Assistant response: `<tool_call>` with Python code
- Code uses external functions directly: `result = ruff_check("path")`
- Code accesses structured fields: `result.violation_count`, `result.violations[0].code`

### Domain Data Mining Pattern
1. Read actual files from repositories
2. Extract representative code snippets (10-50 lines)
3. Generate training examples with real content
4. Mix code reading, search, concept questions, workflows
5. Validate examples are realistic and useful

## Quality Gates

Before merging Phase 24:
1. ✅ All tests pass (`uv run pytest`)
2. ✅ No regressions in existing functionality
3. ✅ Training converges (val loss < 0.8)
4. ✅ Model passes 95% of test queries
5. ✅ Doctests pass (Sybil integration)
6. ✅ Type checking passes (`astral:ty`)
7. ✅ Linting passes (`astral:ruff`)
