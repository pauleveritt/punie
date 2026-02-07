# Standards Applied

This spec applies three Agent OS standards to ensure quality and consistency.

## 1. Agent Verification Standard

### Purpose

Agents should use Astral tools directly via skills rather than convenience wrappers like justfile recipes. This ensures agents get the full context and guidance these tools provide.

### Rationale

- **Justfile recipes** (`just test`, `just lint`) are convenience wrappers for humans and CI/CD
- **Astral skills** (`astral:ruff`, `astral:ty`, `astral:uv`) provide richer context and guidance for agents
- **Direct tool usage** gives better error messages and actionable diagnostics
- **ty LSP** provides real-time type checking feedback during development
- **Skills can provide guidance** on how to fix issues, not just report them

### Rules for Verification

#### Type Checking

**DO:**
- Use the `astral:ty` skill to check types and get guidance
- Pay attention to ty LSP diagnostics as they appear in tool results
- Read and understand type errors before attempting fixes

**DON'T:**
- Run `just lint` or `just typecheck` through Bash
- Ignore ty diagnostics that appear during development

#### Linting and Formatting

**DO:**
- Use the `astral:ruff` skill to check, format, and fix code
- Let ruff guide you on style and error fixes

**DON'T:**
- Run `just lint` or `just format` through Bash
- Apply fixes without understanding what ruff is correcting

#### Testing

**DO:**
- Use `uv run pytest` directly with clear descriptions
- Use `astral:uv` skill if you need guidance on pytest or uv usage
- Specify test paths clearly (e.g., `uv run pytest tests/` not `just test`)

**DON'T:**
- Run `just test` through Bash
- Use justfile test recipes in verification steps

### Application in This Spec

Task 11 (Install Dependencies and Verify) uses:
- `astral:ruff` skill for linting verification
- `astral:ty` skill for type checking verification
- Direct `uv run pytest` commands for testing
- No justfile recipe usage during verification

## 2. Function-Based Tests Standard

### Purpose

Write tests as functions, never classes.

### Correct Pattern

```python
# CORRECT
def test_user_can_login_with_valid_credentials():
    """Test successful login."""
    user = create_user(password="secret")
    assert user.login("secret") is True

def test_user_cannot_login_with_wrong_password():
    """Test login failure."""
    user = create_user(password="secret")
    assert user.login("wrong") is False
```

### Incorrect Pattern

```python
# WRONG - Do not do this
class TestUserLogin:
    def test_valid_credentials(self):
        ...
    def test_wrong_password(self):
        ...
```

### Why Functions

- Simpler, less boilerplate
- No `self` parameter noise
- Fixtures work more naturally
- Pytest's native style

### Rules

- Name: `test_<what>_<scenario>()`
- One assertion focus per test
- Use fixtures for shared setup, not class `setUp`

### Application in This Spec

Task 5 creates `tests/test_punie.py` with function-based tests:

```python
def test_punie_module_has_correct_name():
    """Test that punie module can be imported and has correct __name__."""
    import punie
    assert punie.__name__ == "punie"
```

## 3. Sybil Doctest Integration Standard

### Purpose

Use Sybil to test code examples in docs and docstrings.

### Configuration Pattern

```python
from sybil import Sybil
from sybil.parsers.myst import PythonCodeBlockParser
from sybil.parsers.rest import DocTestParser

# Test Python docstrings in src/
_sybil_src = Sybil(
    parsers=[DocTestParser()],
    patterns=["*.py"],
    path="src",
)

# Test code blocks in README.md
_sybil_readme = Sybil(
    parsers=[PythonCodeBlockParser()],
    patterns=["README.md"],
    path=".",
)

def pytest_collect_file(file_path, parent):
    """Route files to appropriate Sybil parser."""
    ...
```

### What Gets Tested

- `src/**/*.py`: Docstring examples (`>>> ...`)
- `README.md`: Python code blocks
- `docs/**/*.md`: Via separate `docs/conftest.py`

### Rules

- Keep doctest examples minimal and focused
- Exclude research/draft docs from collection
- Use `PythonCodeBlockParser` for Markdown, `DocTestParser` for docstrings

### Application in This Spec

Task 6 creates root `conftest.py` following the tdom-svcs pattern:
- `DocTestParser` for `src/**/*.py`
- `PythonCodeBlockParser` for `README.md`
- `pytest_collect_file` hook with `examples/` exclusion

Task 8 creates `docs/conftest.py` for documentation files.
