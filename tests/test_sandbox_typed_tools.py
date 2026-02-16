"""Tests for typed tools integration in sandbox (ruff_check, pytest_run)."""

import pytest

from punie.agent.monty_runner import ExternalFunctions, run_code
from punie.agent.typed_tools import (
    DocumentSymbolsResult,
    FindReferencesResult,
    GitDiffResult,
    GitLogResult,
    GitStatusResult,
    GotoDefinitionResult,
    HoverResult,
    RuffResult,
    TestResult,
    TypeCheckResult,
    WorkspaceSymbolsResult,
)


# Fake functions for testing


def fake_read_file(path: str) -> str:
    return "content"


def fake_write_file(path: str, content: str) -> str:
    return "success"


def fake_run_command(command: str, args=None, cwd=None) -> str:  # noqa: ARG001
    return "output"


def fake_typecheck(path: str) -> TypeCheckResult:  # noqa: ARG001
    return TypeCheckResult(success=True, error_count=0, warning_count=0, errors=[])


def fake_ruff_check(path: str) -> RuffResult:
    """Fake ruff checker that returns violations for 'violation' in path."""
    if "violation" in path:
        from punie.agent.typed_tools import RuffViolation

        return RuffResult(
            success=False,
            violation_count=1,
            fixable_count=1,
            violations=[
                RuffViolation(
                    file=path,
                    line=10,
                    column=1,
                    code="F401",
                    message="`os` imported but unused",
                    fixable=True,
                )
            ],
        )
    return RuffResult(success=True, violation_count=0, fixable_count=0, violations=[])


def fake_pytest_run(path: str) -> TestResult:
    """Fake pytest runner that returns failures for 'failure' in path."""
    if "failure" in path:
        from punie.agent.typed_tools import TestCase

        return TestResult(
            success=False,
            passed=1,
            failed=1,
            errors=0,
            skipped=0,
            duration=0.10,
            tests=[
                TestCase(
                    name=f"{path}::test_fail",
                    outcome="failed",
                    duration=0.10,
                    message="AssertionError",
                )
            ],
        )
    return TestResult(
        success=True,
        passed=2,
        failed=0,
        errors=0,
        skipped=0,
        duration=0.05,
        tests=[],
    )


def fake_goto_definition(
    file_path: str, line: int, column: int, symbol: str  # noqa: ARG001
) -> GotoDefinitionResult:
    """Fake goto_definition that returns no locations."""
    return GotoDefinitionResult(success=False, symbol=symbol, locations=[])


def fake_find_references(
    file_path: str, line: int, column: int, symbol: str  # noqa: ARG001
) -> FindReferencesResult:
    """Fake find_references that returns no references."""
    return FindReferencesResult(
        success=False, symbol=symbol, reference_count=0, references=[]
    )


def fake_hover(
    file_path: str, line: int, column: int, symbol: str  # noqa: ARG001
) -> HoverResult:
    """Fake hover that returns no info."""
    return HoverResult(success=False, symbol=symbol)


def fake_document_symbols(file_path: str) -> DocumentSymbolsResult:  # noqa: ARG001
    """Fake document_symbols that returns no symbols."""
    return DocumentSymbolsResult(success=False, file_path=file_path, symbols=[])


def fake_workspace_symbols(query: str) -> WorkspaceSymbolsResult:  # noqa: ARG001
    """Fake workspace_symbols that returns no symbols."""
    return WorkspaceSymbolsResult(success=False, query=query, symbols=[])


def fake_git_status(path: str) -> GitStatusResult:  # noqa: ARG001
    """Fake git_status that returns clean tree."""
    return GitStatusResult(success=True, clean=True, file_count=0, files=[])


def fake_git_diff(path: str, staged: bool = False) -> GitDiffResult:  # noqa: ARG001
    """Fake git_diff that returns no changes."""
    return GitDiffResult(success=True, file_count=0, additions=0, deletions=0, files=[])


def fake_git_log(path: str, count: int = 10) -> GitLogResult:  # noqa: ARG001
    """Fake git_log that returns no commits."""
    return GitLogResult(success=True, commits=[], commit_count=0)


@pytest.fixture
def external_functions():
    """Fixture with all external functions including typed tools."""
    return ExternalFunctions(
        read_file=fake_read_file,
        write_file=fake_write_file,
        run_command=fake_run_command,
        typecheck=fake_typecheck,
        ruff_check=fake_ruff_check,
        pytest_run=fake_pytest_run,
        goto_definition=fake_goto_definition,
        find_references=fake_find_references,
        hover=fake_hover,
        document_symbols=fake_document_symbols,
        workspace_symbols=fake_workspace_symbols,
        git_status=fake_git_status,
        git_diff=fake_git_diff,
        git_log=fake_git_log,
    )


def test_run_code_calls_ruff_check(external_functions):
    """Sandbox can call ruff_check and access structured result."""
    code = """
result = ruff_check("src/")
print(f"Success: {result.success}")
print(f"Violations: {result.violation_count}")
"""
    output = run_code(code, external_functions)
    assert "Success: True" in output
    assert "Violations: 0" in output


def test_run_code_ruff_check_with_violations(external_functions):
    """ruff_check returns structured violations that code can access."""
    code = """
result = ruff_check("violation_file.py")
print(f"Success: {result.success}")
print(f"Violations: {result.violation_count}")
print(f"Fixable: {result.fixable_count}")
if result.violations:
    v = result.violations[0]
    print(f"Code: {v.code}, Line: {v.line}, Fixable: {v.fixable}")
"""
    output = run_code(code, external_functions)
    assert "Success: False" in output
    assert "Violations: 1" in output
    assert "Fixable: 1" in output
    assert "Code: F401" in output
    assert "Line: 10" in output


def test_run_code_calls_pytest_run(external_functions):
    """Sandbox can call pytest_run and access structured result."""
    code = """
result = pytest_run("tests/")
print(f"Success: {result.success}")
print(f"Passed: {result.passed}")
print(f"Failed: {result.failed}")
"""
    output = run_code(code, external_functions)
    assert "Success: True" in output
    assert "Passed: 2" in output
    assert "Failed: 0" in output


def test_run_code_pytest_run_with_failures(external_functions):
    """pytest_run returns structured test results with failures."""
    code = """
result = pytest_run("failure_test.py")
print(f"Success: {result.success}")
print(f"Passed: {result.passed}, Failed: {result.failed}")
if result.tests:
    test = result.tests[0]
    print(f"Test: {test.name}, Outcome: {test.outcome}")
"""
    output = run_code(code, external_functions)
    assert "Success: False" in output
    assert "Passed: 1" in output
    assert "Failed: 1" in output
    assert "Outcome: failed" in output


def test_run_code_ruff_pytest_workflow(external_functions):
    """Sandbox can combine ruff_check and pytest_run in workflow."""
    code = """
ruff = ruff_check("src/")
tests = pytest_run("tests/")

print(f"Lint: {ruff.violation_count} violations")
print(f"Tests: {tests.passed}/{tests.passed + tests.failed} passed")

if ruff.success and tests.success:
    print("Quality check: PASS")
else:
    print("Quality check: FAIL")
"""
    output = run_code(code, external_functions)
    assert "Lint: 0 violations" in output
    assert "Tests: 2/2 passed" in output
    assert "Quality check: PASS" in output
