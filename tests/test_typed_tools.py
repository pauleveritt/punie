"""Tests for typed tool Pydantic models."""

import json

import pytest
from pydantic import ValidationError

from punie.agent.typed_tools import (
    RuffResult,
    RuffViolation,
    TestCase,
    TestResult,
    TypeCheckError,
    TypeCheckResult,
    parse_pytest_output,
    parse_ruff_output,
    parse_ty_output,
)


def test_typecheck_error_has_required_fields():
    """TypeCheckError requires all fields."""
    error = TypeCheckError(
        file="test.py",
        line=10,
        column=5,
        severity="error",
        code="unresolved-reference",
        message="Cannot resolve reference 'foo'",
    )
    assert error.file == "test.py"
    assert error.line == 10
    assert error.column == 5
    assert error.severity == "error"
    assert error.code == "unresolved-reference"
    assert error.message == "Cannot resolve reference 'foo'"


def test_typecheck_error_validation_fails_without_required_fields():
    """TypeCheckError validates required fields."""
    with pytest.raises(ValidationError):
        TypeCheckError(file="test.py")  # Missing other required fields


def test_typecheck_result_success():
    """TypeCheckResult for successful check (no errors)."""
    result = TypeCheckResult(
        success=True, error_count=0, warning_count=0, errors=[]
    )
    assert result.success is True
    assert result.error_count == 0
    assert result.warning_count == 0
    assert len(result.errors) == 0


def test_typecheck_result_with_errors():
    """TypeCheckResult with errors."""
    error1 = TypeCheckError(
        file="test.py",
        line=10,
        column=5,
        severity="error",
        code="unresolved-reference",
        message="Cannot resolve reference 'foo'",
    )
    error2 = TypeCheckError(
        file="test.py",
        line=15,
        column=10,
        severity="warning",
        code="unused-variable",
        message="Variable 'bar' is not used",
    )
    result = TypeCheckResult(
        success=False, error_count=1, warning_count=1, errors=[error1, error2]
    )
    assert result.success is False
    assert result.error_count == 1
    assert result.warning_count == 1
    assert len(result.errors) == 2
    assert result.errors[0].severity == "error"
    assert result.errors[1].severity == "warning"


def test_typecheck_result_allows_empty_errors_list():
    """TypeCheckResult allows empty errors list."""
    result = TypeCheckResult(
        success=True, error_count=0, warning_count=0, errors=[]
    )
    assert result.errors == []


def test_typecheck_error_can_be_serialized():
    """TypeCheckError can be serialized to dict."""
    error = TypeCheckError(
        file="test.py",
        line=10,
        column=5,
        severity="error",
        code="unresolved-reference",
        message="Cannot resolve reference 'foo'",
    )
    data = error.model_dump()
    assert data["file"] == "test.py"
    assert data["line"] == 10
    assert data["severity"] == "error"


def test_typecheck_result_can_be_serialized():
    """TypeCheckResult can be serialized to dict."""
    result = TypeCheckResult(
        success=False, error_count=1, warning_count=0, errors=[]
    )
    data = result.model_dump()
    assert data["success"] is False
    assert data["error_count"] == 1
    assert "errors" in data


def test_typecheck_error_from_dict():
    """TypeCheckError can be created from dict (JSON parsing)."""
    data = {
        "file": "test.py",
        "line": 10,
        "column": 5,
        "severity": "error",
        "code": "unresolved-reference",
        "message": "Cannot resolve reference 'foo'",
    }
    error = TypeCheckError(**data)
    assert error.file == "test.py"
    assert error.line == 10


def test_typecheck_result_from_dict():
    """TypeCheckResult can be created from dict (JSON parsing)."""
    data = {
        "success": False,
        "error_count": 1,
        "warning_count": 0,
        "errors": [
            {
                "file": "test.py",
                "line": 10,
                "column": 5,
                "severity": "error",
                "code": "unresolved-reference",
                "message": "Cannot resolve reference 'foo'",
            }
        ],
    }
    result = TypeCheckResult(**data)
    assert result.success is False
    assert len(result.errors) == 1
    assert result.errors[0].file == "test.py"


# Parser tests


def test_parse_ty_output_empty():
    """parse_ty_output handles empty output (no errors)."""
    result = parse_ty_output("")
    assert result.success is True
    assert result.error_count == 0
    assert result.warning_count == 0
    assert len(result.errors) == 0


def test_parse_ty_output_with_errors():
    """parse_ty_output parses ty JSON output with errors."""
    output = json.dumps([
        {
            "file": "test.py",
            "line": 10,
            "column": 5,
            "severity": "error",
            "code": "unresolved-reference",
            "message": "Cannot resolve reference 'foo'",
        }
    ])
    result = parse_ty_output(output)
    assert result.success is False
    assert result.error_count == 1
    assert result.warning_count == 0
    assert len(result.errors) == 1
    assert result.errors[0].file == "test.py"
    assert result.errors[0].line == 10


def test_parse_ty_output_with_warnings():
    """parse_ty_output distinguishes errors from warnings."""
    output = json.dumps([
        {
            "file": "test.py",
            "line": 10,
            "column": 5,
            "severity": "error",
            "code": "unresolved-reference",
            "message": "Cannot resolve reference 'foo'",
        },
        {
            "file": "test.py",
            "line": 15,
            "column": 10,
            "severity": "warning",
            "code": "unused-variable",
            "message": "Variable 'bar' is not used",
        },
    ])
    result = parse_ty_output(output)
    assert result.success is False  # Has errors
    assert result.error_count == 1
    assert result.warning_count == 1
    assert len(result.errors) == 2


def test_parse_ty_output_warnings_only():
    """parse_ty_output with only warnings counts as success."""
    output = json.dumps([
        {
            "file": "test.py",
            "line": 15,
            "column": 10,
            "severity": "warning",
            "code": "unused-variable",
            "message": "Variable 'bar' is not used",
        }
    ])
    result = parse_ty_output(output)
    assert result.success is True  # No errors, only warnings
    assert result.error_count == 0
    assert result.warning_count == 1


def test_parse_ty_output_malformed_json():
    """parse_ty_output handles malformed JSON gracefully."""
    result = parse_ty_output("not valid json")
    assert result.success is True  # Fallback to success
    assert result.error_count == 0
    assert len(result.errors) == 0


# Ruff model tests


def test_ruff_violation_has_required_fields():
    """RuffViolation requires all fields."""
    violation = RuffViolation(
        file="test.py",
        line=10,
        column=5,
        code="E501",
        message="Line too long",
        fixable=True,
    )
    assert violation.file == "test.py"
    assert violation.line == 10
    assert violation.column == 5
    assert violation.code == "E501"
    assert violation.message == "Line too long"
    assert violation.fixable is True


def test_ruff_violation_validation_fails_without_required_fields():
    """RuffViolation validates required fields."""
    with pytest.raises(ValidationError):
        RuffViolation(file="test.py")  # Missing other required fields


def test_ruff_result_success():
    """RuffResult for successful check (no violations)."""
    result = RuffResult(
        success=True, violation_count=0, fixable_count=0, violations=[]
    )
    assert result.success is True
    assert result.violation_count == 0
    assert result.fixable_count == 0
    assert len(result.violations) == 0


def test_ruff_result_with_violations():
    """RuffResult with violations."""
    violation1 = RuffViolation(
        file="test.py",
        line=10,
        column=5,
        code="E501",
        message="Line too long",
        fixable=False,
    )
    violation2 = RuffViolation(
        file="test.py",
        line=15,
        column=1,
        code="F401",
        message="`os` imported but unused",
        fixable=True,
    )
    result = RuffResult(
        success=False, violation_count=2, fixable_count=1, violations=[violation1, violation2]
    )
    assert result.success is False
    assert result.violation_count == 2
    assert result.fixable_count == 1
    assert len(result.violations) == 2
    assert result.violations[0].fixable is False
    assert result.violations[1].fixable is True


def test_parse_ruff_output_empty():
    """parse_ruff_output handles empty output (no violations)."""
    result = parse_ruff_output("")
    assert result.success is True
    assert result.violation_count == 0
    assert result.fixable_count == 0
    assert len(result.violations) == 0


def test_parse_ruff_output_with_violations():
    """parse_ruff_output parses ruff text output with violations."""
    output = """test.py:10:5: E501 Line too long (89 > 88 characters)
test.py:15:1: F401 [*] `os` imported but unused"""
    result = parse_ruff_output(output)
    assert result.success is False
    assert result.violation_count == 2
    assert result.fixable_count == 1
    assert len(result.violations) == 2
    assert result.violations[0].code == "E501"
    assert result.violations[0].fixable is False
    assert result.violations[1].code == "F401"
    assert result.violations[1].fixable is True


def test_parse_ruff_output_all_fixable():
    """parse_ruff_output counts fixable violations correctly."""
    output = """test.py:10:1: F401 [*] `os` imported but unused
test.py:15:1: F401 [*] `sys` imported but unused"""
    result = parse_ruff_output(output)
    assert result.violation_count == 2
    assert result.fixable_count == 2


def test_parse_ruff_output_ignores_summary_lines():
    """parse_ruff_output ignores summary lines from ruff."""
    output = """test.py:10:5: E501 Line too long
Found 1 error."""
    result = parse_ruff_output(output)
    assert result.violation_count == 1
    assert len(result.violations) == 1


# Pytest model tests


def test_test_case_has_required_fields():
    """TestCase requires all fields."""
    test = TestCase(
        name="tests/test_foo.py::test_bar",
        outcome="passed",
        duration=0.05,
        message=None,
    )
    assert test.name == "tests/test_foo.py::test_bar"
    assert test.outcome == "passed"
    assert test.duration == 0.05
    assert test.message is None


def test_test_case_with_failure_message():
    """TestCase can have failure message."""
    test = TestCase(
        name="tests/test_foo.py::test_bar",
        outcome="failed",
        duration=0.05,
        message="AssertionError: expected 2 but got 3",
    )
    assert test.outcome == "failed"
    assert test.message == "AssertionError: expected 2 but got 3"


def test_test_result_success():
    """TestResult for successful run (all tests passed)."""
    result = TestResult(
        success=True,
        passed=5,
        failed=0,
        errors=0,
        skipped=0,
        duration=0.25,
        tests=[],
    )
    assert result.success is True
    assert result.passed == 5
    assert result.failed == 0
    assert result.errors == 0


def test_test_result_with_failures():
    """TestResult with test failures."""
    result = TestResult(
        success=False,
        passed=3,
        failed=2,
        errors=0,
        skipped=1,
        duration=0.30,
        tests=[],
    )
    assert result.success is False
    assert result.passed == 3
    assert result.failed == 2
    assert result.skipped == 1


def test_parse_pytest_output_empty():
    """parse_pytest_output handles empty output."""
    result = parse_pytest_output("")
    assert result.success is True
    assert result.passed == 0
    assert result.failed == 0
    assert len(result.tests) == 0


def test_parse_pytest_output_all_passed():
    """parse_pytest_output parses successful test run."""
    output = """tests/test_foo.py::test_bar PASSED                       [100%]
tests/test_foo.py::test_baz PASSED                       [100%]
=== 2 passed in 0.05s ==="""
    result = parse_pytest_output(output)
    assert result.success is True
    assert result.passed == 2
    assert result.failed == 0
    assert result.duration == 0.05
    assert len(result.tests) == 2
    assert result.tests[0].name == "tests/test_foo.py::test_bar"
    assert result.tests[0].outcome == "passed"


def test_parse_pytest_output_with_failures():
    """parse_pytest_output parses test failures."""
    output = """tests/test_foo.py::test_bar PASSED                       [50%]
tests/test_foo.py::test_baz FAILED                       [100%]
=== 1 failed, 1 passed in 0.10s ==="""
    result = parse_pytest_output(output)
    assert result.success is False
    assert result.passed == 1
    assert result.failed == 1
    assert result.duration == 0.10
    assert len(result.tests) == 2
    assert result.tests[1].outcome == "failed"


def test_parse_pytest_output_with_errors_and_skipped():
    """parse_pytest_output handles errors and skipped tests."""
    output = """tests/test_foo.py::test_bar PASSED
tests/test_foo.py::test_baz ERROR
tests/test_foo.py::test_qux SKIPPED
=== 1 error, 1 passed, 1 skipped in 0.03s ==="""
    result = parse_pytest_output(output)
    assert result.success is False  # Errors count as failure
    assert result.passed == 1
    assert result.errors == 1
    assert result.skipped == 1
    assert len(result.tests) == 3
