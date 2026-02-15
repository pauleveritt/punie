"""Tests for Python code execution sandbox."""

import pytest

from punie.agent.monty_runner import (
    CodeExecutionError,
    ExternalFunctions,
    run_code,
    run_code_async,
)
from punie.agent.typed_tools import (
    RuffResult,
    RuffViolation,
    TestCase,
    TestResult,
    TypeCheckError,
    TypeCheckResult,
)


# Fake external functions for testing (fakes-over-mocks pattern)


def fake_read_file(path: str) -> str:
    """Fake file reader for testing."""
    files = {
        "test.txt": "test content",
        "data.json": '{"key": "value"}',
    }
    if path in files:
        return files[path]
    raise FileNotFoundError(f"File not found: {path}")


def fake_write_file(path: str, content: str) -> str:
    """Fake file writer for testing."""
    if not content:
        raise ValueError("Content cannot be empty")
    return f"Wrote {len(content)} bytes to {path}"


def fake_run_command(
    command: str, args: list[str] | None = None, cwd: str | None = None
) -> str:
    """Fake command runner for testing."""
    if command == "echo":
        return " ".join(args) if args else ""
    if command == "pwd":
        return cwd or "/fake/path"
    if command == "fail":
        raise RuntimeError("Command failed")
    return f"Executed: {command}"


def fake_typecheck(path: str) -> TypeCheckResult:
    """Fake type checker for testing."""
    # Simulate type checking with fake results
    if "error" in path:
        # Simulate file with type error
        return TypeCheckResult(
            success=False,
            error_count=1,
            warning_count=0,
            errors=[
                TypeCheckError(
                    file=path,
                    line=10,
                    column=5,
                    severity="error",
                    code="unresolved-reference",
                    message="Cannot resolve reference 'foo'",
                )
            ],
        )
    else:
        # Simulate clean file
        return TypeCheckResult(success=True, error_count=0, warning_count=0, errors=[])


def fake_ruff_check(path: str) -> RuffResult:
    """Fake ruff linter for testing."""
    # Simulate ruff checking with fake results
    if "violation" in path:
        # Simulate file with linting violations
        return RuffResult(
            success=False,
            violation_count=2,
            fixable_count=1,
            violations=[
                RuffViolation(
                    file=path,
                    line=10,
                    column=5,
                    code="E501",
                    message="Line too long (89 > 88 characters)",
                    fixable=False,
                ),
                RuffViolation(
                    file=path,
                    line=15,
                    column=1,
                    code="F401",
                    message="`os` imported but unused",
                    fixable=True,
                ),
            ],
        )
    else:
        # Simulate clean file
        return RuffResult(success=True, violation_count=0, fixable_count=0, violations=[])


def fake_pytest_run(path: str) -> TestResult:
    """Fake pytest runner for testing."""
    # Simulate pytest running with fake results
    if "failure" in path:
        # Simulate tests with failures
        return TestResult(
            success=False,
            passed=2,
            failed=1,
            errors=0,
            skipped=0,
            duration=0.15,
            tests=[
                TestCase(
                    name=f"{path}::test_passing",
                    outcome="passed",
                    duration=0.05,
                    message=None,
                ),
                TestCase(
                    name=f"{path}::test_failing",
                    outcome="failed",
                    duration=0.10,
                    message="AssertionError: expected 2 but got 3",
                ),
            ],
        )
    else:
        # Simulate all tests passing
        return TestResult(
            success=True,
            passed=3,
            failed=0,
            errors=0,
            skipped=0,
            duration=0.12,
            tests=[],
        )


@pytest.fixture
def external_functions():
    """Fixture providing external functions registry."""
    return ExternalFunctions(
        read_file=fake_read_file,
        write_file=fake_write_file,
        run_command=fake_run_command,
        typecheck=fake_typecheck,
        ruff_check=fake_ruff_check,
        pytest_run=fake_pytest_run,
    )


# Basic execution tests


def test_run_code_executes_simple_python(external_functions):
    """Runner executes simple Python and captures stdout."""
    code = 'print("Hello, world!")'
    result = run_code(code, external_functions)
    assert result.strip() == "Hello, world!"


def test_run_code_supports_variables(external_functions):
    """Runner supports variable assignments and expressions."""
    code = """
x = 5
y = 10
print(x + y)
"""
    result = run_code(code, external_functions)
    assert result.strip() == "15"


def test_run_code_supports_loops(external_functions):
    """Runner supports loops and control flow."""
    code = """
for i in range(3):
    print(i)
"""
    result = run_code(code, external_functions)
    assert result.strip() == "0\n1\n2"


def test_run_code_supports_functions(external_functions):
    """Runner supports function definitions."""
    code = """
def greet(name):
    return f"Hello, {name}!"

print(greet("Alice"))
"""
    result = run_code(code, external_functions)
    assert result.strip() == "Hello, Alice!"


# External function tests


def test_run_code_calls_read_file(external_functions):
    """Runner calls external read_file function."""
    code = """
content = read_file("test.txt")
print(content)
"""
    result = run_code(code, external_functions)
    assert result.strip() == "test content"


def test_run_code_calls_write_file(external_functions):
    """Runner calls external write_file function."""
    code = """
result = write_file("output.txt", "new content")
print(result)
"""
    result = run_code(code, external_functions)
    assert "Wrote" in result
    assert "output.txt" in result


def test_run_code_calls_run_command(external_functions):
    """Runner calls external run_command function."""
    code = """
output = run_command("echo", args=["hello"])
print(output)
"""
    result = run_code(code, external_functions)
    assert result.strip() == "hello"


def test_run_code_calls_multiple_external_functions(external_functions):
    """Runner handles multiple external function calls."""
    code = """
content = read_file("test.txt")
write_file("output.txt", content)
output = run_command("pwd")
print(output)
"""
    result = run_code(code, external_functions)
    assert "/fake/path" in result


# Safe module tests


def test_run_code_has_json_module(external_functions):
    """Runner provides json module for structured data parsing (no import needed)."""
    code = """
data = json.loads('{"key": "value"}')
print(data["key"])
"""
    result = run_code(code, external_functions)
    assert result.strip() == "value"


def test_run_code_json_parse_tool_output(external_functions):
    """Runner can parse JSON output from tools using json module."""
    code = """
content = read_file("data.json")
parsed = json.loads(content)
print(f"Key: {parsed['key']}")
"""
    result = run_code(code, external_functions)
    assert result.strip() == "Key: value"


def test_run_code_json_dumps(external_functions):
    """Runner can use json.dumps for serialization."""
    code = """
data = {"name": "test", "count": 42}
output = json.dumps(data)
print(output)
"""
    result = run_code(code, external_functions)
    assert "test" in result
    assert "42" in result


# Typed tool tests (typecheck)


def test_run_code_calls_typecheck(external_functions):
    """Runner calls external typecheck function."""
    code = """
result = typecheck("src/test.py")
print(f"Success: {result.success}")
print(f"Errors: {result.error_count}")
"""
    result = run_code(code, external_functions)
    assert "Success: True" in result
    assert "Errors: 0" in result


def test_run_code_typecheck_with_errors(external_functions):
    """Runner can handle typecheck results with errors."""
    code = """
result = typecheck("src/error.py")
if not result.success:
    print(f"Found {result.error_count} errors")
    for error in result.errors:
        print(f"  {error.file}:{error.line} - {error.message}")
"""
    result = run_code(code, external_functions)
    assert "Found 1 errors" in result
    assert "error.py:10" in result
    assert "Cannot resolve reference" in result


def test_run_code_typecheck_workflow(external_functions):
    """Runner can use typecheck in multi-step workflow."""
    code = """
# Check types
result = typecheck("src/test.py")

# Take action based on result
if result.success:
    print("All types OK!")
else:
    print(f"Need to fix {result.error_count} errors")
    for error in result.errors:
        # Could read file and fix here
        print(f"Error in {error.file}")
"""
    result = run_code(code, external_functions)
    assert "All types OK!" in result


# Error handling tests


def test_run_code_rejects_syntax_errors(external_functions):
    """Runner rejects code with syntax errors."""
    code = "print('unclosed string"
    with pytest.raises(CodeExecutionError, match="Syntax error"):
        run_code(code, external_functions)


def test_run_code_catches_runtime_errors(external_functions):
    """Runner catches runtime errors and wraps in CodeExecutionError."""
    code = """
x = 1 / 0
"""
    with pytest.raises(CodeExecutionError, match="Runtime error"):
        run_code(code, external_functions)


def test_run_code_propagates_external_function_errors(external_functions):
    """Runner propagates errors from external functions."""
    code = """
content = read_file("nonexistent.txt")
"""
    with pytest.raises(CodeExecutionError, match="Runtime error"):
        run_code(code, external_functions)


# Security tests


def test_run_code_blocks_import(external_functions):
    """Runner blocks import statements."""
    code = "import os"
    with pytest.raises(CodeExecutionError, match="Runtime error"):
        run_code(code, external_functions)


def test_run_code_blocks_open(external_functions):
    """Runner blocks built-in open() function."""
    code = 'open("file.txt")'
    with pytest.raises(CodeExecutionError, match="Runtime error"):
        run_code(code, external_functions)


def test_run_code_blocks_eval(external_functions):
    """Runner blocks eval() function."""
    code = 'eval("1+1")'
    with pytest.raises(CodeExecutionError, match="Runtime error"):
        run_code(code, external_functions)


def test_run_code_blocks_exec(external_functions):
    """Runner blocks exec() function."""
    code = 'exec("print(1)")'
    with pytest.raises(CodeExecutionError, match="Runtime error"):
        run_code(code, external_functions)


# Async tests


async def test_run_code_async_works(external_functions):
    """Async wrapper executes code successfully."""
    code = 'print("async test")'
    result = await run_code_async(code, external_functions)
    assert result.strip() == "async test"


async def test_run_code_async_calls_external_functions(external_functions):
    """Async wrapper calls external functions."""
    code = """
content = read_file("test.txt")
print(content)
"""
    result = await run_code_async(code, external_functions)
    assert result.strip() == "test content"


# Edge cases


def test_run_code_handles_empty_code(external_functions):
    """Runner handles empty code gracefully."""
    result = run_code("", external_functions)
    assert result == ""


def test_run_code_handles_no_output(external_functions):
    """Runner handles code with no stdout."""
    code = "x = 42"
    result = run_code(code, external_functions)
    assert result == ""


def test_run_code_handles_multiline_output(external_functions):
    """Runner captures multiline output."""
    code = """
for i in range(5):
    print(f"Line {i}")
"""
    result = run_code(code, external_functions)
    lines = result.strip().split("\n")
    assert len(lines) == 5
    assert lines[0] == "Line 0"
    assert lines[4] == "Line 4"
