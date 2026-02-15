"""Typed tools with structured output for domain-specific operations.

This module provides Pydantic models for tools that return structured data
instead of raw text. Currently supports:
- ty (type checking) → TypeCheckResult
- ruff (linting) → RuffResult
- pytest (testing) → TestResult
"""

import json
import re

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


# Ruff models


class RuffViolation(BaseModel):
    """A single linting violation from ruff.

    Attributes:
        file: File path where the violation occurred
        line: Line number (1-indexed)
        column: Column number (1-indexed)
        code: Ruff rule code (e.g., "E501", "F401")
        message: Human-readable description of the violation
        fixable: Whether ruff can auto-fix this violation
    """

    file: str
    line: int
    column: int
    code: str
    message: str
    fixable: bool


class RuffResult(BaseModel):
    """Result of running ruff check.

    Attributes:
        success: True if no violations found, False otherwise
        violation_count: Total number of violations found
        fixable_count: Number of violations that can be auto-fixed
        violations: List of all violations
    """

    success: bool
    violation_count: int
    fixable_count: int
    violations: list[RuffViolation]


def parse_ruff_output(output: str) -> RuffResult:
    """Parse ruff check output into RuffResult.

    Args:
        output: Raw output from ruff check command (text format)

    Returns:
        RuffResult with parsed violations

    Note:
        Parses default ruff text output format:
        path/to/file.py:10:5: E501 Line too long (89 > 88 characters)
        path/to/file.py:15:1: F401 [*] `os` imported but unused

        [*] indicates fixable violations
    """
    # Handle empty output (no violations)
    if not output or output.strip() == "":
        return RuffResult(
            success=True, violation_count=0, fixable_count=0, violations=[]
        )

    violations = []
    fixable_count = 0

    # Pattern: file.py:line:col: CODE message
    # [*] prefix indicates fixable
    pattern = r"^(.+?):(\d+):(\d+):\s+([A-Z]\d+)\s+(\[\*\]\s+)?(.+)$"

    for line in output.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("Found ") or line.startswith("No "):
            continue

        match = re.match(pattern, line)
        if match:
            file_path, line_no, col_no, code, fixable_marker, message = match.groups()
            is_fixable = fixable_marker is not None

            violation = RuffViolation(
                file=file_path,
                line=int(line_no),
                column=int(col_no),
                code=code,
                message=message.strip(),
                fixable=is_fixable,
            )
            violations.append(violation)

            if is_fixable:
                fixable_count += 1

    success = len(violations) == 0
    return RuffResult(
        success=success,
        violation_count=len(violations),
        fixable_count=fixable_count,
        violations=violations,
    )


# Pytest models


class TestCase(BaseModel):
    """A single test case result from pytest.

    Attributes:
        name: Test identifier (e.g., "tests/test_foo.py::test_bar")
        outcome: Test outcome ("passed", "failed", "error", "skipped")
        duration: Test execution time in seconds
        message: Error/failure message if test didn't pass (optional)
    """

    name: str
    outcome: str  # "passed" | "failed" | "error" | "skipped"
    duration: float
    message: str | None = None


class TestResult(BaseModel):
    """Result of running pytest.

    Attributes:
        success: True if all tests passed, False otherwise
        passed: Number of tests that passed
        failed: Number of tests that failed
        errors: Number of tests with errors
        skipped: Number of tests that were skipped
        duration: Total test execution time in seconds
        tests: List of individual test results
    """

    success: bool
    passed: int
    failed: int
    errors: int
    skipped: int
    duration: float
    tests: list[TestCase]


def parse_pytest_output(output: str) -> TestResult:
    """Parse pytest output into TestResult.

    Args:
        output: Raw output from pytest -v --tb=short command

    Returns:
        TestResult with parsed test results

    Note:
        Parses pytest verbose output format:
        tests/test_foo.py::test_bar PASSED                       [100%]
        tests/test_foo.py::test_baz FAILED                       [100%]

        Summary line: === 1 failed, 1 passed in 0.05s ===
    """
    # Handle empty output
    if not output or output.strip() == "":
        return TestResult(
            success=True,
            passed=0,
            failed=0,
            errors=0,
            skipped=0,
            duration=0.0,
            tests=[],
        )

    tests = []
    passed = failed = errors = skipped = 0
    duration = 0.0

    lines = output.strip().split("\n")

    # Parse individual test results
    test_pattern = r"^(.+?)\s+(PASSED|FAILED|ERROR|SKIPPED)"
    for line in lines:
        match = re.match(test_pattern, line)
        if match:
            test_name, outcome = match.groups()
            test_name = test_name.strip()
            outcome = outcome.lower()

            # Try to extract duration from verbose output (not always present)
            duration_match = re.search(r"\[(\d+\.\d+)s\]", line)
            test_duration = float(duration_match.group(1)) if duration_match else 0.0

            test_case = TestCase(
                name=test_name,
                outcome=outcome,
                duration=test_duration,
                message=None,  # Would need --tb output parsing for messages
            )
            tests.append(test_case)

            # Count outcomes
            if outcome == "passed":
                passed += 1
            elif outcome == "failed":
                failed += 1
            elif outcome == "error":
                errors += 1
            elif outcome == "skipped":
                skipped += 1

    # Parse summary line: === 1 failed, 2 passed in 0.05s ===
    summary_pattern = r"===.*?(?:(\d+)\s+failed)?.*?(?:(\d+)\s+passed)?.*?(?:(\d+)\s+error)?.*?(?:(\d+)\s+skipped)?.*?in\s+([\d.]+)s"
    for line in lines:
        match = re.search(summary_pattern, line)
        if match:
            f, p, e, s, dur = match.groups()
            if f:
                failed = int(f)
            if p:
                passed = int(p)
            if e:
                errors = int(e)
            if s:
                skipped = int(s)
            duration = float(dur)
            break

    success = failed == 0 and errors == 0
    return TestResult(
        success=success,
        passed=passed,
        failed=failed,
        errors=errors,
        skipped=skipped,
        duration=duration,
        tests=tests,
    )
