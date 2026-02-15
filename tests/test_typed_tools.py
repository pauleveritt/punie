"""Tests for typed tool Pydantic models."""

import json

import pytest
from pydantic import ValidationError

from punie.agent.typed_tools import TypeCheckError, TypeCheckResult, parse_ty_output


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
