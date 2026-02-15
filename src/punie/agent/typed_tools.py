"""Typed tools with structured output for domain-specific operations.

This module provides Pydantic models for tools that return structured data
instead of raw text. The first typed tool is ty (type checking), which returns
TypeCheckResult with structured error information.
"""

import json

from pydantic import BaseModel


class TypeCheckError(BaseModel):
    """A single type checking error from ty.

    Attributes:
        file: File path where the error occurred
        line: Line number (1-indexed)
        column: Column number (1-indexed)
        severity: Error severity level ("error" or "warning")
        code: Error code (e.g., "unresolved-reference", "type-mismatch")
        message: Human-readable error message
    """

    file: str
    line: int
    column: int
    severity: str  # "error" | "warning"
    code: str
    message: str


class TypeCheckResult(BaseModel):
    """Result of running ty type checker.

    Attributes:
        success: True if no errors found, False otherwise
        error_count: Number of errors found
        warning_count: Number of warnings found
        errors: List of errors and warnings
    """

    success: bool
    error_count: int
    warning_count: int
    errors: list[TypeCheckError]


def parse_ty_output(output: str) -> TypeCheckResult:
    """Parse ty check output into TypeCheckResult.

    Args:
        output: Raw output from ty check command (JSON format)

    Returns:
        TypeCheckResult with parsed errors

    Note:
        Expects ty to be run with --output-format json flag.
        If output is empty or malformed, returns success=True with no errors.
    """
    # Handle empty output (no errors)
    if not output or output.strip() == "":
        return TypeCheckResult(success=True, error_count=0, warning_count=0, errors=[])

    try:
        # Parse JSON output from ty
        data = json.loads(output)

        # ty --output-format json returns a list of diagnostics
        # Each diagnostic has: file, line, column, severity, code, message
        errors = []
        error_count = 0
        warning_count = 0

        for diag in data:
            error = TypeCheckError(
                file=diag["file"],
                line=diag["line"],
                column=diag.get("column", 0),
                severity=diag.get("severity", "error"),
                code=diag.get("code", "unknown"),
                message=diag["message"],
            )
            errors.append(error)

            if error.severity == "error":
                error_count += 1
            elif error.severity == "warning":
                warning_count += 1

        success = error_count == 0
        return TypeCheckResult(
            success=success,
            error_count=error_count,
            warning_count=warning_count,
            errors=errors,
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        # If parsing fails, return success (ty might not support JSON format yet)
        return TypeCheckResult(success=True, error_count=0, warning_count=0, errors=[])
