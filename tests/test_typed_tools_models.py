"""Tests for typed tool Pydantic models.

Tests model validation, serialization, and field access for all typed tool result models:
- TypeCheckError, TypeCheckResult
- RuffViolation, RuffResult
- TestCase, TestResult
- DefinitionLocation, GotoDefinitionResult
- ReferenceLocation, FindReferencesResult
"""

import pytest
from pydantic import ValidationError

from punie.agent.typed_tools import (
    DefinitionLocation,
    FindReferencesResult,
    GotoDefinitionResult,
    ReferenceLocation,
    RuffResult,
    RuffViolation,
    TestCase,
    TestResult,
    TypeCheckError,
    TypeCheckResult,
)


# TypeCheck models


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


# Ruff models


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


# Pytest models


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


# LSP Navigation models


def test_definition_location_has_required_fields():
    """DefinitionLocation requires all fields."""
    location = DefinitionLocation(
        file="/path/to/file.py",
        line=10,
        column=5,
        end_line=10,
        end_column=15,
        preview="def foo():",
    )
    assert location.file == "/path/to/file.py"
    assert location.line == 10
    assert location.column == 5
    assert location.end_line == 10
    assert location.end_column == 15
    assert location.preview == "def foo():"


def test_goto_definition_result_success():
    """GotoDefinitionResult for successful lookup."""
    result = GotoDefinitionResult(
        success=True,
        symbol="UserService",
        locations=[
            DefinitionLocation(
                file="/src/services.py",
                line=20,
                column=7,
                end_line=20,
                end_column=18,
            )
        ],
    )
    assert result.success is True
    assert result.symbol == "UserService"
    assert len(result.locations) == 1
    assert result.locations[0].line == 20
    assert result.parse_error is None


def test_goto_definition_result_not_found():
    """GotoDefinitionResult when symbol not found."""
    result = GotoDefinitionResult(
        success=False,
        symbol="MissingClass",
        locations=[],
    )
    assert result.success is False
    assert result.symbol == "MissingClass"
    assert len(result.locations) == 0
    assert result.parse_error is None


def test_reference_location_has_required_fields():
    """ReferenceLocation requires all fields."""
    location = ReferenceLocation(
        file="/path/to/file.py",
        line=10,
        column=5,
        preview="user_service.process()",
    )
    assert location.file == "/path/to/file.py"
    assert location.line == 10
    assert location.column == 5
    assert location.preview == "user_service.process()"


def test_find_references_result_success():
    """FindReferencesResult for successful lookup."""
    result = FindReferencesResult(
        success=True,
        symbol="process_order",
        reference_count=3,
        references=[
            ReferenceLocation(file="/src/app.py", line=15, column=10),
            ReferenceLocation(file="/src/api.py", line=42, column=8),
            ReferenceLocation(file="/tests/test_app.py", line=100, column=12),
        ],
    )
    assert result.success is True
    assert result.symbol == "process_order"
    assert result.reference_count == 3
    assert len(result.references) == 3
    assert result.references[0].file == "/src/app.py"
    assert result.parse_error is None


def test_find_references_result_not_found():
    """FindReferencesResult when no references found."""
    result = FindReferencesResult(
        success=False,
        symbol="unused_function",
        reference_count=0,
        references=[],
    )
    assert result.success is False
    assert result.symbol == "unused_function"
    assert result.reference_count == 0
    assert len(result.references) == 0
    assert result.parse_error is None
