#!/usr/bin/env python3
"""Generate Phase 26 field access training examples.

This script creates 120 training examples (4 patterns × 3 tools × 10 examples)
demonstrating structured field access on typed tool results. This addresses the
Phase 23 gap where models called tools but never accessed result fields.

Patterns:
  1. Conditional Logic (30): if result.error_count > 0:
  2. Field Access + Formatting (30): print(f"Errors: {result.error_count}")
  3. Iteration (30): for error in result.errors:
  4. Multi-step Workflows (30): check → access field → use in next tool

Tools:
  - typecheck() → TypeCheckResult
  - ruff_check() → RuffResult
  - pytest_run() → TestResult
"""

import json
from pathlib import Path

from punie.training.dataset import ChatMessage, TrainingExample

# Constants
OUTPUT_DIR = Path("data/phase26_field_access")
SYSTEM_PROMPT = "You are Punie, an AI coding assistant that helps with Python development via PyCharm."


def create_example(user_query: str, assistant_code: str) -> TrainingExample:
    """Create a training example with system message + XML-wrapped code.

    Args:
        user_query: Natural user question
        assistant_code: Python code with field access (will be XML-wrapped)

    Returns:
        TrainingExample in Format A (XML-wrapped with system message)
    """
    # Wrap code in Format A XML structure
    xml_content = f"""<tool_call><function=execute_code>
<parameter=code>
{assistant_code.strip()}
</parameter>
</function></tool_call>"""

    return TrainingExample(
        messages=(
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_query),
            ChatMessage(role="assistant", content=xml_content),
        )
    )


# Pattern 1: Conditional Logic (30 examples)


def generate_conditional_typecheck() -> list[TrainingExample]:
    """Generate conditional logic examples for typecheck() (10 examples)."""
    examples = []

    # Example 1: Basic error count check
    examples.append(
        create_example(
            "Check types in src/ and report if any errors",
            """result = typecheck("src/")
if result.error_count > 0:
    print(f"Found {result.error_count} type errors")
else:
    print("No type errors found")""",
        )
    )

    # Example 2: Check success field
    examples.append(
        create_example(
            "Is src/punie/agent/ fully typed?",
            """result = typecheck("src/punie/agent/")
if result.success:
    print("✓ All files are fully typed")
else:
    print(f"✗ Found {result.error_count} errors, {result.warning_count} warnings")""",
        )
    )

    # Example 3: Warning threshold
    examples.append(
        create_example(
            "Check if tests/ has more than 5 type warnings",
            """result = typecheck("tests/")
if result.warning_count > 5:
    print(f"Too many warnings: {result.warning_count}")
else:
    print(f"Warnings within acceptable range: {result.warning_count}")""",
        )
    )

    # Example 4: Error vs warning check
    examples.append(
        create_example(
            "Check types in config.py and distinguish errors from warnings",
            """result = typecheck("src/punie/agent/config.py")
if result.error_count > 0:
    print(f"FAIL: {result.error_count} errors must be fixed")
elif result.warning_count > 0:
    print(f"WARN: {result.warning_count} warnings found")
else:
    print("PASS: No issues found")""",
        )
    )

    # Example 5: Parse error check
    examples.append(
        create_example(
            "Check if ty output parsed correctly for src/",
            """result = typecheck("src/")
if result.parse_error:
    print(f"Error parsing ty output: {result.parse_error}")
else:
    print(f"Type check completed: {result.error_count} errors found")""",
        )
    )

    # Examples 6-10: More variations
    examples.append(
        create_example(
            "Check types and exit early if no errors",
            """result = typecheck("src/punie/")
if result.error_count == 0:
    print("✓ All clear, no type errors")
else:
    print(f"Need to fix {result.error_count} errors")""",
        )
    )

    examples.append(
        create_example(
            "Is typed_tools.py error-free?",
            """result = typecheck("src/punie/agent/typed_tools.py")
if not result.success:
    print(f"File has {result.error_count} type errors")
else:
    print("File is error-free")""",
        )
    )

    examples.append(
        create_example(
            "Check if test files have any type issues",
            """result = typecheck("tests/")
has_issues = result.error_count > 0 or result.warning_count > 0
if has_issues:
    print(f"Tests have {result.error_count} errors and {result.warning_count} warnings")
else:
    print("Tests are fully typed")""",
        )
    )

    examples.append(
        create_example(
            "Check types and show severity counts",
            """result = typecheck("src/")
if result.error_count > 0:
    print(f"Critical: {result.error_count} errors")
if result.warning_count > 0:
    print(f"Warning: {result.warning_count} warnings")
if result.success:
    print("All checks passed")""",
        )
    )

    examples.append(
        create_example(
            "Quick type check for toolset.py",
            """result = typecheck("src/punie/agent/toolset.py")
status = "PASS" if result.success else "FAIL"
print(f"Type check: {status} ({result.error_count} errors, {result.warning_count} warnings)")""",
        )
    )

    return examples


def generate_conditional_ruff() -> list[TrainingExample]:
    """Generate conditional logic examples for ruff_check() (10 examples)."""
    examples = []

    # Example 1: Basic violation check
    examples.append(
        create_example(
            "Run ruff on src/ and report if violations found",
            """result = ruff_check("src/")
if result.violation_count > 0:
    print(f"Found {result.violation_count} linting violations")
else:
    print("No violations found")""",
        )
    )

    # Example 2: Fixable violations
    examples.append(
        create_example(
            "Check if ruff can auto-fix violations in src/",
            """result = ruff_check("src/")
if result.fixable_count > 0:
    print(f"{result.fixable_count} of {result.violation_count} violations can be auto-fixed")
else:
    print(f"None of the {result.violation_count} violations are auto-fixable")""",
        )
    )

    # Example 3: Success check
    examples.append(
        create_example(
            "Is src/punie/training/ ruff-clean?",
            """result = ruff_check("src/punie/training/")
if result.success:
    print("✓ All files pass ruff checks")
else:
    print(f"✗ Found {result.violation_count} violations ({result.fixable_count} fixable)")""",
        )
    )

    # Example 4: Threshold check
    examples.append(
        create_example(
            "Check if tests/ has fewer than 10 violations",
            """result = ruff_check("tests/")
if result.violation_count < 10:
    print(f"Acceptable: {result.violation_count} violations")
else:
    print(f"Too many violations: {result.violation_count}")""",
        )
    )

    # Example 5: Parse error check
    examples.append(
        create_example(
            "Run ruff and check for parsing issues",
            """result = ruff_check("src/")
if result.parse_error:
    print(f"Error parsing ruff output: {result.parse_error}")
else:
    print(f"Ruff check completed: {result.violation_count} violations")""",
        )
    )

    # Examples 6-10
    examples.append(
        create_example(
            "Check if all violations are fixable",
            """result = ruff_check("src/punie/agent/")
if result.fixable_count == result.violation_count:
    print("All violations can be auto-fixed")
else:
    manual_fixes = result.violation_count - result.fixable_count
    print(f"{manual_fixes} violations need manual fixes")""",
        )
    )

    examples.append(
        create_example(
            "Quick ruff check for config.py",
            """result = ruff_check("src/punie/agent/config.py")
if not result.success:
    print(f"File has {result.violation_count} violations")
else:
    print("File is ruff-clean")""",
        )
    )

    examples.append(
        create_example(
            "Check ruff status for scripts/",
            """result = ruff_check("scripts/")
status = "CLEAN" if result.success else "VIOLATIONS"
fixable = f" ({result.fixable_count} fixable)" if result.fixable_count > 0 else ""
print(f"Ruff: {status} - {result.violation_count} violations{fixable}")""",
        )
    )

    examples.append(
        create_example(
            "Check if typed_tools.py needs ruff fixes",
            """result = ruff_check("src/punie/agent/typed_tools.py")
if result.violation_count > 0:
    print(f"Needs fixes: {result.violation_count} violations")
    if result.fixable_count > 0:
        print(f"Run 'ruff check --fix' to auto-fix {result.fixable_count}")
else:
    print("No fixes needed")""",
        )
    )

    examples.append(
        create_example(
            "Compare violation counts across directories",
            """result_src = ruff_check("src/")
result_tests = ruff_check("tests/")
if result_src.violation_count > result_tests.violation_count:
    print(f"src/ has more violations: {result_src.violation_count} vs {result_tests.violation_count}")
else:
    print(f"tests/ has more violations: {result_tests.violation_count} vs {result_src.violation_count}")""",
        )
    )

    return examples


def generate_conditional_pytest() -> list[TrainingExample]:
    """Generate conditional logic examples for pytest_run() (10 examples)."""
    examples = []

    # Example 1: Basic pass/fail check
    examples.append(
        create_example(
            "Run tests and report if all passed",
            """result = pytest_run("tests/")
if result.success:
    print(f"✓ All {result.passed} tests passed")
else:
    print(f"✗ {result.failed} tests failed, {result.passed} passed")""",
        )
    )

    # Example 2: Check for failures
    examples.append(
        create_example(
            "Check if any tests failed",
            """result = pytest_run("tests/")
if result.failed > 0:
    print(f"Test failures detected: {result.failed} failed out of {result.passed + result.failed} total")
else:
    print(f"All {result.passed} tests passed successfully")""",
        )
    )

    # Example 3: Check for errors
    examples.append(
        create_example(
            "Run tests and check for errors vs failures",
            """result = pytest_run("tests/")
if result.errors > 0:
    print(f"Test errors (setup/teardown): {result.errors}")
if result.failed > 0:
    print(f"Test failures (assertions): {result.failed}")
if result.success:
    print("All tests passed")""",
        )
    )

    # Example 4: Duration check
    examples.append(
        create_example(
            "Check if tests run quickly",
            """result = pytest_run("tests/test_agent_config.py")
if result.duration < 1.0:
    print(f"Fast test suite: {result.duration:.2f}s")
else:
    print(f"Slow test suite: {result.duration:.2f}s")""",
        )
    )

    # Example 5: Skipped tests
    examples.append(
        create_example(
            "Check if any tests were skipped",
            """result = pytest_run("tests/")
if result.skipped > 0:
    print(f"Warning: {result.skipped} tests were skipped")
total = result.passed + result.failed + result.skipped
print(f"Total: {total} tests ({result.passed} passed, {result.failed} failed, {result.skipped} skipped)")""",
        )
    )

    # Examples 6-10
    examples.append(
        create_example(
            "Check if test file has failures",
            """result = pytest_run("tests/test_typed_tools.py")
if not result.success:
    print(f"test_typed_tools.py has {result.failed} failing tests")
else:
    print(f"test_typed_tools.py: all {result.passed} tests passed")""",
        )
    )

    examples.append(
        create_example(
            "Quick test status check",
            """result = pytest_run("tests/")
status = "PASS" if result.success else "FAIL"
print(f"Test suite: {status}")
print(f"  Passed: {result.passed}")
print(f"  Failed: {result.failed}")
print(f"  Duration: {result.duration:.2f}s")""",
        )
    )

    examples.append(
        create_example(
            "Check parse error in pytest output",
            """result = pytest_run("tests/")
if result.parse_error:
    print(f"Error parsing pytest output: {result.parse_error}")
else:
    print(f"Tests completed: {result.passed} passed, {result.failed} failed")""",
        )
    )

    examples.append(
        create_example(
            "Run specific test and check outcome",
            """result = pytest_run("tests/test_agent_config.py::test_default_config")
if result.passed == 1:
    print("Test passed successfully")
elif result.failed == 1:
    print("Test failed")
else:
    print("Test outcome unclear")""",
        )
    )

    examples.append(
        create_example(
            "Check test coverage completeness",
            """result = pytest_run("tests/")
total_tests = result.passed + result.failed + result.errors + result.skipped
if total_tests > 100:
    print(f"Good coverage: {total_tests} tests total")
else:
    print(f"Limited coverage: {total_tests} tests total")
print(f"Success rate: {result.passed / total_tests * 100:.1f}%")""",
        )
    )

    return examples


# Pattern 2: Field Access + Formatting (30 examples)


def generate_formatting_typecheck() -> list[TrainingExample]:
    """Generate field access + formatting examples for typecheck() (10 examples)."""
    examples = []

    # Example 1: Format error count
    examples.append(
        create_example(
            "How many type errors are in src/?",
            """result = typecheck("src/")
print(f"Type errors: {result.error_count}")
print(f"Warnings: {result.warning_count}")""",
        )
    )

    # Example 2: Success status
    examples.append(
        create_example(
            "Show type check status for src/punie/agent/",
            """result = typecheck("src/punie/agent/")
status = "PASS" if result.success else "FAIL"
print(f"Type check: {status}")
print(f"Errors: {result.error_count}, Warnings: {result.warning_count}")""",
        )
    )

    # Example 3: First error details
    examples.append(
        create_example(
            "Show the first type error in config.py",
            """result = typecheck("src/punie/agent/config.py")
if result.error_count > 0:
    first = result.errors[0]
    print(f"First error at line {first.line}: {first.message}")""",
        )
    )

    # Examples 4-10
    examples.append(
        create_example(
            "List all files with type errors",
            """result = typecheck("src/")
files_with_errors = set(e.file for e in result.errors)
print(f"Files with errors: {len(files_with_errors)}")
for file in sorted(files_with_errors):
    print(f"  {file}")""",
        )
    )

    examples.append(
        create_example(
            "Count errors by severity",
            """result = typecheck("src/")
errors = sum(1 for e in result.errors if e.severity == "error")
warnings = sum(1 for e in result.errors if e.severity == "warning")
print(f"Errors: {errors}, Warnings: {warnings}")""",
        )
    )

    examples.append(
        create_example(
            "Show type check summary",
            """result = typecheck("tests/")
print(f"Type Check Results:")
print(f"  Success: {result.success}")
print(f"  Errors: {result.error_count}")
print(f"  Warnings: {result.warning_count}")
print(f"  Total issues: {len(result.errors)}")""",
        )
    )

    examples.append(
        create_example(
            "Format first 3 errors nicely",
            """result = typecheck("src/")
print(f"First 3 errors (of {result.error_count}):")
for i, error in enumerate(result.errors[:3], 1):
    print(f"{i}. {error.file}:{error.line} - {error.code}")""",
        )
    )

    examples.append(
        create_example(
            "Show error codes distribution",
            """result = typecheck("src/punie/agent/")
codes = {}
for error in result.errors:
    codes[error.code] = codes.get(error.code, 0) + 1
print("Error codes:")
for code, count in sorted(codes.items()):
    print(f"  {code}: {count}")""",
        )
    )

    examples.append(
        create_example(
            "Pretty-print type check results",
            """result = typecheck("src/")
status_icon = "✓" if result.success else "✗"
print(f"{status_icon} Type check: {result.error_count} errors, {result.warning_count} warnings")""",
        )
    )

    examples.append(
        create_example(
            "Show percentage of warnings vs errors",
            """result = typecheck("src/")
total = result.error_count + result.warning_count
if total > 0:
    error_pct = result.error_count / total * 100
    print(f"Errors: {result.error_count} ({error_pct:.1f}%)")
    print(f"Warnings: {result.warning_count} ({100-error_pct:.1f}%)")""",
        )
    )

    return examples


def generate_formatting_ruff() -> list[TrainingExample]:
    """Generate field access + formatting examples for ruff_check() (10 examples)."""
    examples = []

    # Example 1: Format violation count
    examples.append(
        create_example(
            "How many ruff violations in src/?",
            """result = ruff_check("src/")
print(f"Violations: {result.violation_count}")
print(f"Fixable: {result.fixable_count}")""",
        )
    )

    # Example 2: First violation
    examples.append(
        create_example(
            "Show first ruff violation in src/",
            """result = ruff_check("src/")
if result.violation_count > 0:
    first = result.violations[0]
    print(f"{first.file}:{first.line} - {first.code}: {first.message}")""",
        )
    )

    # Examples 3-10
    examples.append(
        create_example(
            "Show ruff check summary",
            """result = ruff_check("src/punie/")
print(f"Ruff Check Results:")
print(f"  Total violations: {result.violation_count}")
print(f"  Auto-fixable: {result.fixable_count}")
print(f"  Manual fixes: {result.violation_count - result.fixable_count}")
print(f"  Status: {'PASS' if result.success else 'FAIL'}")""",
        )
    )

    examples.append(
        create_example(
            "List all violation codes",
            """result = ruff_check("src/")
codes = set(v.code for v in result.violations)
print(f"Violation codes ({len(codes)}):")
for code in sorted(codes):
    print(f"  {code}")""",
        )
    )

    examples.append(
        create_example(
            "Show fixable percentage",
            """result = ruff_check("tests/")
if result.violation_count > 0:
    fixable_pct = result.fixable_count / result.violation_count * 100
    print(f"{result.fixable_count} of {result.violation_count} violations are fixable ({fixable_pct:.1f}%)")""",
        )
    )

    examples.append(
        create_example(
            "Format first 5 violations",
            """result = ruff_check("src/")
print(f"First 5 violations (of {result.violation_count}):")
for v in result.violations[:5]:
    fix_marker = "[*]" if v.fixable else "[ ]"
    print(f"{fix_marker} {v.file}:{v.line} - {v.code}")""",
        )
    )

    examples.append(
        create_example(
            "Count violations by rule",
            """result = ruff_check("src/punie/agent/")
rule_counts = {}
for v in result.violations:
    rule_counts[v.code] = rule_counts.get(v.code, 0) + 1
print("Violations by rule:")
for rule, count in sorted(rule_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {rule}: {count}")""",
        )
    )

    examples.append(
        create_example(
            "Show files with most violations",
            """result = ruff_check("src/")
file_counts = {}
for v in result.violations:
    file_counts[v.file] = file_counts.get(v.file, 0) + 1
top_3 = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:3]
print("Files with most violations:")
for file, count in top_3:
    print(f"  {file}: {count}")""",
        )
    )

    examples.append(
        create_example(
            "Pretty-print ruff status",
            """result = ruff_check("scripts/")
icon = "✓" if result.success else "✗"
print(f"{icon} Ruff: {result.violation_count} violations ({result.fixable_count} fixable)")""",
        )
    )

    examples.append(
        create_example(
            "Show violation severity breakdown",
            """result = ruff_check("src/")
# Group by first letter of code (E=error, W=warning, F=fatal, etc)
by_severity = {}
for v in result.violations:
    severity = v.code[0]
    by_severity[severity] = by_severity.get(severity, 0) + 1
print("Violations by severity:")
for sev, count in sorted(by_severity.items()):
    print(f"  {sev}: {count}")""",
        )
    )

    return examples


def generate_formatting_pytest() -> list[TrainingExample]:
    """Generate field access + formatting examples for pytest_run() (10 examples)."""
    examples = []

    # Example 1: Format test counts
    examples.append(
        create_example(
            "Show test results summary",
            """result = pytest_run("tests/")
print(f"Tests: {result.passed} passed, {result.failed} failed")
print(f"Duration: {result.duration:.2f}s")""",
        )
    )

    # Example 2: First test name
    examples.append(
        create_example(
            "Show first test result",
            """result = pytest_run("tests/")
if len(result.tests) > 0:
    first = result.tests[0]
    print(f"{first.name}: {first.outcome} ({first.duration:.3f}s)")""",
        )
    )

    # Examples 3-10
    examples.append(
        create_example(
            "Show full test summary",
            """result = pytest_run("tests/")
total = result.passed + result.failed + result.errors + result.skipped
print(f"Test Summary:")
print(f"  Total: {total} tests")
print(f"  Passed: {result.passed}")
print(f"  Failed: {result.failed}")
print(f"  Errors: {result.errors}")
print(f"  Skipped: {result.skipped}")
print(f"  Duration: {result.duration:.2f}s")""",
        )
    )

    examples.append(
        create_example(
            "List all failed test names",
            """result = pytest_run("tests/")
failed_tests = [t.name for t in result.tests if t.outcome == "failed"]
print(f"Failed tests ({len(failed_tests)}):")
for name in failed_tests:
    print(f"  {name}")""",
        )
    )

    examples.append(
        create_example(
            "Show success rate",
            """result = pytest_run("tests/")
total = result.passed + result.failed
if total > 0:
    success_rate = result.passed / total * 100
    print(f"Success rate: {success_rate:.1f}% ({result.passed}/{total})")""",
        )
    )

    examples.append(
        create_example(
            "Format slowest tests",
            """result = pytest_run("tests/")
slowest = sorted(result.tests, key=lambda t: t.duration, reverse=True)[:3]
print("Slowest tests:")
for t in slowest:
    print(f"  {t.name}: {t.duration:.3f}s")""",
        )
    )

    examples.append(
        create_example(
            "Show test outcomes distribution",
            """result = pytest_run("tests/")
outcomes = {}
for test in result.tests:
    outcomes[test.outcome] = outcomes.get(test.outcome, 0) + 1
print("Test outcomes:")
for outcome, count in sorted(outcomes.items()):
    print(f"  {outcome}: {count}")""",
        )
    )

    examples.append(
        create_example(
            "Pretty-print test status",
            """result = pytest_run("tests/test_agent_config.py")
icon = "✓" if result.success else "✗"
print(f"{icon} Tests: {result.passed} passed, {result.failed} failed in {result.duration:.2f}s")""",
        )
    )

    examples.append(
        create_example(
            "Show average test duration",
            """result = pytest_run("tests/")
if len(result.tests) > 0:
    avg_duration = result.duration / len(result.tests)
    print(f"Average test duration: {avg_duration:.3f}s")
    print(f"Total duration: {result.duration:.2f}s for {len(result.tests)} tests")""",
        )
    )

    examples.append(
        create_example(
            "Format test file results",
            """result = pytest_run("tests/test_typed_tools.py")
total = result.passed + result.failed
print(f"test_typed_tools.py:")
print(f"  Status: {'PASS' if result.success else 'FAIL'}")
print(f"  Tests: {total} ({result.passed} passed, {result.failed} failed)")
print(f"  Time: {result.duration:.2f}s")""",
        )
    )

    return examples


# Pattern 3: Iteration (30 examples)


def generate_iteration_typecheck() -> list[TrainingExample]:
    """Generate iteration examples for typecheck() (10 examples)."""
    examples = []

    # Example 1: Basic error iteration
    examples.append(
        create_example(
            "List all type errors in src/",
            """result = typecheck("src/")
print(f"Type errors ({result.error_count}):")
for error in result.errors:
    print(f"  {error.file}:{error.line} - {error.message}")""",
        )
    )

    # Example 2: Iterate with severity filter
    examples.append(
        create_example(
            "Show only errors (not warnings) from src/punie/",
            """result = typecheck("src/punie/")
errors_only = [e for e in result.errors if e.severity == "error"]
print(f"Errors ({len(errors_only)}):")
for error in errors_only:
    print(f"  Line {error.line}: {error.message}")""",
        )
    )

    # Examples 3-10
    examples.append(
        create_example(
            "Group errors by file",
            """result = typecheck("src/")
by_file = {}
for error in result.errors:
    if error.file not in by_file:
        by_file[error.file] = []
    by_file[error.file].append(error)
for file, errors in sorted(by_file.items()):
    print(f"{file}: {len(errors)} errors")""",
        )
    )

    examples.append(
        create_example(
            "Show errors with line and column",
            """result = typecheck("src/punie/agent/")
for error in result.errors:
    print(f"{error.file}:{error.line}:{error.column} - {error.code}: {error.message}")""",
        )
    )

    examples.append(
        create_example(
            "Count errors by error code",
            """result = typecheck("src/")
code_counts = {}
for error in result.errors:
    code_counts[error.code] = code_counts.get(error.code, 0) + 1
print("Error codes:")
for code, count in sorted(code_counts.items()):
    print(f"  {code}: {count}")""",
        )
    )

    examples.append(
        create_example(
            "Show first 5 errors with details",
            """result = typecheck("tests/")
print(f"First 5 errors (of {result.error_count}):")
for i, error in enumerate(result.errors[:5], 1):
    print(f"{i}. {error.file}:{error.line}")
    print(f"   [{error.code}] {error.message}")""",
        )
    )

    examples.append(
        create_example(
            "Find unresolved reference errors",
            """result = typecheck("src/")
unresolved = [e for e in result.errors if "unresolved" in e.code.lower()]
print(f"Unresolved reference errors ({len(unresolved)}):")
for error in unresolved:
    print(f"  {error.file}:{error.line} - {error.message}")""",
        )
    )

    examples.append(
        create_example(
            "Show warnings only",
            """result = typecheck("src/")
warnings = [e for e in result.errors if e.severity == "warning"]
print(f"Warnings ({len(warnings)}):")
for warning in warnings:
    print(f"  {warning.file}:{warning.line} - {warning.message}")""",
        )
    )

    examples.append(
        create_example(
            "List unique files with errors",
            """result = typecheck("src/punie/")
files = set()
for error in result.errors:
    files.add(error.file)
print(f"Files with type errors ({len(files)}):")
for file in sorted(files):
    print(f"  {file}")""",
        )
    )

    examples.append(
        create_example(
            "Enumerate errors with index",
            """result = typecheck("src/punie/agent/config.py")
for index, error in enumerate(result.errors, 1):
    severity_icon = "E" if error.severity == "error" else "W"
    print(f"{index}. [{severity_icon}] Line {error.line}: {error.message}")""",
        )
    )

    return examples


def generate_iteration_ruff() -> list[TrainingExample]:
    """Generate iteration examples for ruff_check() (10 examples)."""
    examples = []

    # Example 1: Basic violation iteration
    examples.append(
        create_example(
            "List all ruff violations in src/",
            """result = ruff_check("src/")
print(f"Violations ({result.violation_count}):")
for v in result.violations:
    print(f"  {v.file}:{v.line} - {v.code}: {v.message}")""",
        )
    )

    # Example 2: Iterate fixable only
    examples.append(
        create_example(
            "Show only fixable violations",
            """result = ruff_check("src/punie/")
fixable = [v for v in result.violations if v.fixable]
print(f"Fixable violations ({len(fixable)}):")
for v in fixable:
    print(f"  {v.file}:{v.line} - {v.code}")""",
        )
    )

    # Examples 3-10
    examples.append(
        create_example(
            "Group violations by file",
            """result = ruff_check("src/")
by_file = {}
for v in result.violations:
    if v.file not in by_file:
        by_file[v.file] = []
    by_file[v.file].append(v)
for file, violations in sorted(by_file.items()):
    print(f"{file}: {len(violations)} violations")""",
        )
    )

    examples.append(
        create_example(
            "Show violations with fixable marker",
            """result = ruff_check("tests/")
for v in result.violations:
    marker = "[*]" if v.fixable else "[ ]"
    print(f"{marker} {v.file}:{v.line} - {v.code}")""",
        )
    )

    examples.append(
        create_example(
            "Count violations by rule code",
            """result = ruff_check("src/")
code_counts = {}
for v in result.violations:
    code_counts[v.code] = code_counts.get(v.code, 0) + 1
print("Violation counts:")
for code, count in sorted(code_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {code}: {count}")""",
        )
    )

    examples.append(
        create_example(
            "Show non-fixable violations",
            """result = ruff_check("src/punie/agent/")
non_fixable = [v for v in result.violations if not v.fixable]
print(f"Non-fixable violations ({len(non_fixable)}):")
for v in non_fixable:
    print(f"  {v.file}:{v.line} - {v.code}: {v.message}")""",
        )
    )

    examples.append(
        create_example(
            "List files with violations",
            """result = ruff_check("src/")
files = set()
for v in result.violations:
    files.add(v.file)
print(f"Files with violations ({len(files)}):")
for file in sorted(files):
    print(f"  {file}")""",
        )
    )

    examples.append(
        create_example(
            "Show first 10 violations",
            """result = ruff_check("tests/")
print(f"First 10 violations (of {result.violation_count}):")
for i, v in enumerate(result.violations[:10], 1):
    print(f"{i}. {v.file}:{v.line} - {v.code}")""",
        )
    )

    examples.append(
        create_example(
            "Find specific violation type",
            """result = ruff_check("src/")
f401_violations = [v for v in result.violations if v.code == "F401"]
print(f"F401 (unused import) violations ({len(f401_violations)}):")
for v in f401_violations:
    print(f"  {v.file}:{v.line} - {v.message}")""",
        )
    )

    examples.append(
        create_example(
            "Enumerate violations with details",
            """result = ruff_check("src/punie/agent/")
for index, v in enumerate(result.violations, 1):
    fix_status = "AUTO-FIX" if v.fixable else "MANUAL"
    print(f"{index}. [{fix_status}] {v.file}:{v.line}:{v.column}")
    print(f"   {v.code}: {v.message}")""",
        )
    )

    return examples


def generate_iteration_pytest() -> list[TrainingExample]:
    """Generate iteration examples for pytest_run() (10 examples)."""
    examples = []

    # Example 1: Basic test iteration
    examples.append(
        create_example(
            "List all test results",
            """result = pytest_run("tests/")
print(f"Test results ({len(result.tests)}):")
for test in result.tests:
    print(f"  {test.name}: {test.outcome}")""",
        )
    )

    # Example 2: Iterate failed tests
    examples.append(
        create_example(
            "Show all failed tests",
            """result = pytest_run("tests/")
failed = [t for t in result.tests if t.outcome == "failed"]
print(f"Failed tests ({len(failed)}):")
for test in failed:
    print(f"  {test.name}")
    if test.message:
        print(f"    {test.message}")""",
        )
    )

    # Examples 3-10
    examples.append(
        create_example(
            "Group tests by outcome",
            """result = pytest_run("tests/")
by_outcome = {}
for test in result.tests:
    if test.outcome not in by_outcome:
        by_outcome[test.outcome] = []
    by_outcome[test.outcome].append(test)
for outcome, tests in sorted(by_outcome.items()):
    print(f"{outcome}: {len(tests)} tests")""",
        )
    )

    examples.append(
        create_example(
            "Show tests with duration",
            """result = pytest_run("tests/")
for test in result.tests:
    print(f"{test.name}: {test.outcome} ({test.duration:.3f}s)")""",
        )
    )

    examples.append(
        create_example(
            "Find slow tests (>1s)",
            """result = pytest_run("tests/")
slow_tests = [t for t in result.tests if t.duration > 1.0]
print(f"Slow tests ({len(slow_tests)}):")
for test in slow_tests:
    print(f"  {test.name}: {test.duration:.2f}s")""",
        )
    )

    examples.append(
        create_example(
            "List passed tests with duration",
            """result = pytest_run("tests/test_agent_config.py")
passed = [t for t in result.tests if t.outcome == "passed"]
print(f"Passed tests ({len(passed)}):")
for test in passed:
    print(f"  {test.name} ({test.duration:.3f}s)")""",
        )
    )

    examples.append(
        create_example(
            "Show test file breakdown",
            """result = pytest_run("tests/")
by_file = {}
for test in result.tests:
    file = test.name.split("::")[0]
    by_file[file] = by_file.get(file, 0) + 1
print("Tests by file:")
for file, count in sorted(by_file.items()):
    print(f"  {file}: {count} tests")""",
        )
    )

    examples.append(
        create_example(
            "Enumerate all tests with status",
            """result = pytest_run("tests/")
for index, test in enumerate(result.tests, 1):
    status_icon = "✓" if test.outcome == "passed" else "✗"
    print(f"{index}. {status_icon} {test.name} ({test.duration:.3f}s)")""",
        )
    )

    examples.append(
        create_example(
            "Find skipped tests",
            """result = pytest_run("tests/")
skipped = [t for t in result.tests if t.outcome == "skipped"]
print(f"Skipped tests ({len(skipped)}):")
for test in skipped:
    print(f"  {test.name}")""",
        )
    )

    examples.append(
        create_example(
            "Show fastest tests",
            """result = pytest_run("tests/")
fastest = sorted(result.tests, key=lambda t: t.duration)[:5]
print("Fastest 5 tests:")
for test in fastest:
    print(f"  {test.name}: {test.duration:.3f}s")""",
        )
    )

    return examples


# Pattern 4: Multi-step Workflows (30 examples)


def generate_multistep_typecheck() -> list[TrainingExample]:
    """Generate multi-step workflow examples for typecheck() (10 examples)."""
    examples = []

    # Example 1: Check → read first error file
    examples.append(
        create_example(
            "Check types and show context for first error",
            """result = typecheck("src/punie/agent/")
if result.error_count > 0:
    first_error = result.errors[0]
    print(f"First error: {first_error.file}:{first_error.line}")
    # Read file to show context
    content = read_file(first_error.file)
    lines = content.split("\\n")
    # Show line with error
    print(f"  {lines[first_error.line - 1]}")""",
        )
    )

    # Example 2: Check → list files → read each
    examples.append(
        create_example(
            "Find files with type errors and count errors per file",
            """result = typecheck("src/")
file_errors = {}
for error in result.errors:
    file_errors[error.file] = file_errors.get(error.file, 0) + 1

print(f"Files with errors ({len(file_errors)}):")
for file, count in sorted(file_errors.items(), key=lambda x: x[1], reverse=True):
    print(f"  {file}: {count} errors")
    # Could read file here for more context""",
        )
    )

    # Examples 3-10
    examples.append(
        create_example(
            "Check types, then check if errors are in test files",
            """result = typecheck("src/")
if result.error_count > 0:
    test_errors = [e for e in result.errors if "test" in e.file]
    src_errors = [e for e in result.errors if "test" not in e.file]
    print(f"Source errors: {len(src_errors)}")
    print(f"Test errors: {len(test_errors)}")
    # Fix source errors first
    if len(src_errors) > 0:
        print(f"\\nFirst source error:")
        print(f"  {src_errors[0].file}:{src_errors[0].line} - {src_errors[0].message}")""",
        )
    )

    examples.append(
        create_example(
            "Check types and group by error severity",
            """result = typecheck("src/punie/")
errors = [e for e in result.errors if e.severity == "error"]
warnings = [e for e in result.errors if e.severity == "warning"]

print(f"Critical errors: {len(errors)}")
if len(errors) > 0:
    print("Top 3 errors:")
    for e in errors[:3]:
        print(f"  {e.file}:{e.line} - {e.code}")

print(f"\\nWarnings: {len(warnings)}")""",
        )
    )

    examples.append(
        create_example(
            "Check types and find most common error",
            """result = typecheck("src/")
if result.error_count > 0:
    code_counts = {}
    for error in result.errors:
        code_counts[error.code] = code_counts.get(error.code, 0) + 1

    most_common = max(code_counts.items(), key=lambda x: x[1])
    print(f"Most common error: {most_common[0]} ({most_common[1]} occurrences)")

    # Show examples of this error
    examples = [e for e in result.errors if e.code == most_common[0]][:3]
    for e in examples:
        print(f"  {e.file}:{e.line}")""",
        )
    )

    examples.append(
        create_example(
            "Type check and create fix plan",
            """result = typecheck("src/punie/agent/config.py")
if not result.success:
    print(f"Fix plan for config.py ({result.error_count} errors):")

    # Group by line number
    by_line = {}
    for error in result.errors:
        by_line[error.line] = by_line.get(error.line, 0) + 1

    print("Lines needing fixes:")
    for line in sorted(by_line.keys()):
        print(f"  Line {line}: {by_line[line]} errors")""",
        )
    )

    examples.append(
        create_example(
            "Check types and compare error counts",
            """result_agent = typecheck("src/punie/agent/")
result_training = typecheck("src/punie/training/")

print("Error comparison:")
print(f"  agent/: {result_agent.error_count} errors")
print(f"  training/: {result_training.error_count} errors")

if result_agent.error_count > result_training.error_count:
    print("\\nFocus on fixing agent/ first")
    # Show first error in agent/
    if len(result_agent.errors) > 0:
        print(f"  First error: {result_agent.errors[0].file}:{result_agent.errors[0].line}")""",
        )
    )

    examples.append(
        create_example(
            "Type check and identify files needing most work",
            """result = typecheck("src/")
file_counts = {}
for error in result.errors:
    file_counts[error.file] = file_counts.get(error.file, 0) + 1

# Find worst file
if file_counts:
    worst_file, worst_count = max(file_counts.items(), key=lambda x: x[1])
    print(f"File needing most work: {worst_file} ({worst_count} errors)")

    # Show all errors in that file
    file_errors = [e for e in result.errors if e.file == worst_file]
    print("\\nErrors in this file:")
    for e in file_errors:
        print(f"  Line {e.line}: {e.code} - {e.message}")""",
        )
    )

    examples.append(
        create_example(
            "Check and verify specific error type",
            """result = typecheck("src/")
unresolved_errors = [e for e in result.errors if "unresolved" in e.code.lower()]

print(f"Unresolved reference errors: {len(unresolved_errors)}")
if len(unresolved_errors) > 0:
    print("\\nAffected files:")
    files = set(e.file for e in unresolved_errors)
    for file in sorted(files):
        file_unresolved = [e for e in unresolved_errors if e.file == file]
        print(f"  {file}: {len(file_unresolved)} unresolved references")""",
        )
    )

    examples.append(
        create_example(
            "Type check and build fix priority list",
            """result = typecheck("src/punie/")
if result.error_count > 0:
    # Priority: errors before warnings
    errors = [e for e in result.errors if e.severity == "error"]
    warnings = [e for e in result.errors if e.severity == "warning"]

    print("Fix priority:")
    print(f"1. Fix {len(errors)} errors first")
    if len(errors) > 0:
        print(f"   Start with: {errors[0].file}:{errors[0].line}")
    print(f"2. Address {len(warnings)} warnings after")""",
        )
    )

    return examples


def generate_multistep_ruff() -> list[TrainingExample]:
    """Generate multi-step workflow examples for ruff_check() (10 examples)."""
    examples = []

    # Example 1: Check → show first violation location
    examples.append(
        create_example(
            "Find first ruff violation and show context",
            """result = ruff_check("src/punie/agent/")
if result.violation_count > 0:
    first = result.violations[0]
    print(f"First violation: {first.file}:{first.line}")
    print(f"  {first.code}: {first.message}")
    print(f"  Fixable: {'Yes' if first.fixable else 'No'}")

    # Read file for context
    content = read_file(first.file)
    lines = content.split("\\n")
    print(f"  Line: {lines[first.line - 1]}")""",
        )
    )

    # Example 2: Check → separate fixable/non-fixable
    examples.append(
        create_example(
            "Categorize violations by fixability",
            """result = ruff_check("src/")
fixable = [v for v in result.violations if v.fixable]
non_fixable = [v for v in result.violations if not v.fixable]

print(f"Fixable violations ({len(fixable)}):")
for v in fixable[:3]:
    print(f"  {v.file}:{v.line} - {v.code}")

print(f"\\nNon-fixable violations ({len(non_fixable)}):")
for v in non_fixable[:3]:
    print(f"  {v.file}:{v.line} - {v.code}")
    # These need manual review""",
        )
    )

    # Examples 3-10
    examples.append(
        create_example(
            "Check ruff and identify hotspot files",
            """result = ruff_check("src/")
file_counts = {}
for v in result.violations:
    file_counts[v.file] = file_counts.get(v.file, 0) + 1

top_5 = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5]
print("Files with most violations:")
for file, count in top_5:
    fixable_count = sum(1 for v in result.violations if v.file == file and v.fixable)
    print(f"  {file}: {count} violations ({fixable_count} fixable)")""",
        )
    )

    examples.append(
        create_example(
            "Run ruff and create fix plan by rule",
            """result = ruff_check("src/punie/")
if result.violation_count > 0:
    # Group by rule code
    by_rule = {}
    for v in result.violations:
        if v.code not in by_rule:
            by_rule[v.code] = []
        by_rule[v.code].append(v)

    print("Fix plan by rule:")
    for rule, violations in sorted(by_rule.items(), key=lambda x: len(x[1]), reverse=True):
        fixable = sum(1 for v in violations if v.fixable)
        print(f"  {rule}: {len(violations)} violations ({fixable} auto-fixable)")""",
        )
    )

    examples.append(
        create_example(
            "Check ruff and compare directories",
            """result_src = ruff_check("src/")
result_tests = ruff_check("tests/")

print("Ruff comparison:")
print(f"  src/: {result_src.violation_count} violations ({result_src.fixable_count} fixable)")
print(f"  tests/: {result_tests.violation_count} violations ({result_tests.fixable_count} fixable)")

# Focus on directory with more issues
if result_src.violation_count > result_tests.violation_count:
    print("\\nFocus on src/ first:")
    if len(result_src.violations) > 0:
        print(f"  {result_src.violations[0].file}:{result_src.violations[0].line} - {result_src.violations[0].code}")""",
        )
    )

    examples.append(
        create_example(
            "Run ruff and identify common patterns",
            """result = ruff_check("src/")
if result.violation_count > 0:
    # Find most common violation
    code_counts = {}
    for v in result.violations:
        code_counts[v.code] = code_counts.get(v.code, 0) + 1

    most_common = max(code_counts.items(), key=lambda x: x[1])
    print(f"Most common violation: {most_common[0]} ({most_common[1]} occurrences)")

    # Show where this violation occurs
    examples = [v for v in result.violations if v.code == most_common[0]][:5]
    print("Locations:")
    for v in examples:
        print(f"  {v.file}:{v.line}")""",
        )
    )

    examples.append(
        create_example(
            "Check ruff and build priority fix list",
            """result = ruff_check("scripts/")
if result.violation_count > 0:
    # Priority: non-fixable first (need manual work)
    non_fixable = [v for v in result.violations if not v.fixable]
    fixable = [v for v in result.violations if v.fixable]

    print("Fix priority:")
    print(f"1. Manual fixes needed: {len(non_fixable)}")
    if len(non_fixable) > 0:
        print(f"   Start with: {non_fixable[0].file}:{non_fixable[0].line}")
    print(f"2. Auto-fix available: {len(fixable)}")
    if len(fixable) > 0:
        print(f"   Run: ruff check --fix")""",
        )
    )

    examples.append(
        create_example(
            "Analyze ruff violations by severity",
            """result = ruff_check("src/")
if result.violation_count > 0:
    # Group by first letter (E=error, W=warning, F=fatal, etc)
    by_severity = {}
    for v in result.violations:
        severity = v.code[0]
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(v)

    print("Violations by severity:")
    for severity in sorted(by_severity.keys()):
        violations = by_severity[severity]
        fixable = sum(1 for v in violations if v.fixable)
        print(f"  {severity}: {len(violations)} ({fixable} fixable)")""",
        )
    )

    examples.append(
        create_example(
            "Find files clean except for one rule",
            """result = ruff_check("src/punie/agent/")
if result.violation_count > 0:
    # Find files with only one violation type
    by_file_and_code = {}
    for v in result.violations:
        if v.file not in by_file_and_code:
            by_file_and_code[v.file] = set()
        by_file_and_code[v.file].add(v.code)

    easy_fixes = {f: codes for f, codes in by_file_and_code.items() if len(codes) == 1}
    print(f"Files with single violation type ({len(easy_fixes)}):")
    for file, codes in sorted(easy_fixes.items()):
        code = list(codes)[0]
        count = sum(1 for v in result.violations if v.file == file)
        print(f"  {file}: {code} ({count} occurrences)")""",
        )
    )

    examples.append(
        create_example(
            "Check ruff and estimate fix effort",
            """result = ruff_check("src/")
if result.violation_count > 0:
    auto_fix_time = result.fixable_count * 0.1  # seconds
    manual_fix_time = (result.violation_count - result.fixable_count) * 60  # 1 min each

    print(f"Fix effort estimate:")
    print(f"  Auto-fix: {result.fixable_count} violations (~{auto_fix_time:.0f}s)")
    print(f"  Manual: {result.violation_count - result.fixable_count} violations (~{manual_fix_time/60:.0f}m)")
    print(f"  Total: ~{(auto_fix_time + manual_fix_time)/60:.0f} minutes")""",
        )
    )

    return examples


def generate_multistep_pytest() -> list[TrainingExample]:
    """Generate multi-step workflow examples for pytest_run() (10 examples)."""
    examples = []

    # Example 1: Run → show first failure detail
    examples.append(
        create_example(
            "Run tests and show details of first failure",
            """result = pytest_run("tests/")
if result.failed > 0:
    failed_tests = [t for t in result.tests if t.outcome == "failed"]
    first_failure = failed_tests[0]

    print(f"First failure: {first_failure.name}")
    if first_failure.message:
        print(f"  Error: {first_failure.message}")

    # Extract file and test name
    parts = first_failure.name.split("::")
    test_file = parts[0]
    print(f"  File: {test_file}")""",
        )
    )

    # Example 2: Run → categorize by file
    examples.append(
        create_example(
            "Run tests and group results by file",
            """result = pytest_run("tests/")
by_file = {}
for test in result.tests:
    file = test.name.split("::")[0]
    if file not in by_file:
        by_file[file] = {"passed": 0, "failed": 0}
    if test.outcome == "passed":
        by_file[file]["passed"] += 1
    elif test.outcome == "failed":
        by_file[file]["failed"] += 1

print("Test results by file:")
for file, counts in sorted(by_file.items()):
    total = counts["passed"] + counts["failed"]
    print(f"  {file}: {counts['passed']}/{total} passed")""",
        )
    )

    # Examples 3-10
    examples.append(
        create_example(
            "Run tests and identify slow test files",
            """result = pytest_run("tests/")
# Group tests by file with duration
by_file = {}
for test in result.tests:
    file = test.name.split("::")[0]
    if file not in by_file:
        by_file[file] = 0.0
    by_file[file] += test.duration

# Find slowest files
slowest = sorted(by_file.items(), key=lambda x: x[1], reverse=True)[:3]
print("Slowest test files:")
for file, duration in slowest:
    print(f"  {file}: {duration:.2f}s")""",
        )
    )

    examples.append(
        create_example(
            "Run tests and analyze failure patterns",
            """result = pytest_run("tests/")
if result.failed > 0:
    failed = [t for t in result.tests if t.outcome == "failed"]

    # Check if failures are concentrated
    failed_files = set(t.name.split("::")[0] for t in failed)

    print(f"Failure analysis:")
    print(f"  Total failures: {result.failed}")
    print(f"  Affected files: {len(failed_files)}")

    if len(failed_files) == 1:
        print(f"  All failures in: {list(failed_files)[0]}")
    else:
        print("  Failures spread across multiple files")""",
        )
    )

    examples.append(
        create_example(
            "Run tests and compare passed vs failed duration",
            """result = pytest_run("tests/")
passed_tests = [t for t in result.tests if t.outcome == "passed"]
failed_tests = [t for t in result.tests if t.outcome == "failed"]

if len(passed_tests) > 0:
    avg_passed = sum(t.duration for t in passed_tests) / len(passed_tests)
    print(f"Average passed test duration: {avg_passed:.3f}s")

if len(failed_tests) > 0:
    avg_failed = sum(t.duration for t in failed_tests) / len(failed_tests)
    print(f"Average failed test duration: {avg_failed:.3f}s")""",
        )
    )

    examples.append(
        create_example(
            "Run tests and create fix priority",
            """result = pytest_run("tests/")
if result.failed > 0:
    # Group failures by file
    by_file = {}
    for test in result.tests:
        if test.outcome == "failed":
            file = test.name.split("::")[0]
            if file not in by_file:
                by_file[file] = []
            by_file[file].append(test.name.split("::")[-1])

    print("Fix priority (files with most failures):")
    for file, test_names in sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {file}: {len(test_names)} failures")""",
        )
    )

    examples.append(
        create_example(
            "Run tests and check for flaky tests",
            """result = pytest_run("tests/")
# Run again and compare
result2 = pytest_run("tests/")

# Find tests with different outcomes
flaky = []
for test1 in result.tests:
    test2 = next((t for t in result2.tests if t.name == test1.name), None)
    if test2 and test1.outcome != test2.outcome:
        flaky.append(test1.name)

if len(flaky) > 0:
    print(f"Potentially flaky tests ({len(flaky)}):")
    for test in flaky:
        print(f"  {test}")
else:
    print("No flaky tests detected")""",
        )
    )

    examples.append(
        create_example(
            "Run tests and build coverage report",
            """result = pytest_run("tests/")
# Count tests per module
modules = {}
for test in result.tests:
    # Extract module from test path
    parts = test.name.split("/")
    if len(parts) > 1:
        module = parts[-1].split("::")[0].replace("test_", "").replace(".py", "")
        modules[module] = modules.get(module, 0) + 1

print("Test coverage by module:")
for module, count in sorted(modules.items(), key=lambda x: x[1], reverse=True):
    print(f"  {module}: {count} tests")""",
        )
    )

    examples.append(
        create_example(
            "Run tests and identify test patterns",
            """result = pytest_run("tests/")
# Analyze test names for patterns
patterns = {}
for test in result.tests:
    test_name = test.name.split("::")[-1]
    if test_name.startswith("test_default"):
        patterns["default_tests"] = patterns.get("default_tests", 0) + 1
    elif test_name.startswith("test_invalid"):
        patterns["invalid_tests"] = patterns.get("invalid_tests", 0) + 1
    elif test_name.startswith("test_error"):
        patterns["error_tests"] = patterns.get("error_tests", 0) + 1
    else:
        patterns["other_tests"] = patterns.get("other_tests", 0) + 1

print("Test patterns:")
for pattern, count in sorted(patterns.items()):
    print(f"  {pattern}: {count}")""",
        )
    )

    examples.append(
        create_example(
            "Run tests and calculate efficiency metrics",
            """result = pytest_run("tests/")
if len(result.tests) > 0:
    total_time = result.duration
    avg_time = total_time / len(result.tests)

    # Find outliers (>3x average)
    outliers = [t for t in result.tests if t.duration > avg_time * 3]

    print("Test suite efficiency:")
    print(f"  Total tests: {len(result.tests)}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Average: {avg_time:.3f}s per test")
    print(f"  Outliers (>3x avg): {len(outliers)}")

    if len(outliers) > 0:
        print("\\nSlowest tests:")
        for t in sorted(outliers, key=lambda x: x.duration, reverse=True)[:3]:
            print(f"  {t.name}: {t.duration:.2f}s")""",
        )
    )

    return examples


def main():
    """Generate all 120 field access examples and save to disk."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating Phase 26 field access training examples...")
    print()

    # Generate all patterns × tools
    all_examples: list[TrainingExample] = []

    # Pattern 1: Conditional Logic (30)
    print("Pattern 1: Conditional Logic")
    typecheck_cond = generate_conditional_typecheck()
    ruff_cond = generate_conditional_ruff()
    pytest_cond = generate_conditional_pytest()
    print(f"  typecheck: {len(typecheck_cond)} examples")
    print(f"  ruff_check: {len(ruff_cond)} examples")
    print(f"  pytest_run: {len(pytest_cond)} examples")
    all_examples.extend(typecheck_cond + ruff_cond + pytest_cond)

    # Pattern 2: Field Access + Formatting (30)
    print("\nPattern 2: Field Access + Formatting")
    typecheck_fmt = generate_formatting_typecheck()
    ruff_fmt = generate_formatting_ruff()
    pytest_fmt = generate_formatting_pytest()
    print(f"  typecheck: {len(typecheck_fmt)} examples")
    print(f"  ruff_check: {len(ruff_fmt)} examples")
    print(f"  pytest_run: {len(pytest_fmt)} examples")
    all_examples.extend(typecheck_fmt + ruff_fmt + pytest_fmt)

    # Pattern 3: Iteration (30)
    print("\nPattern 3: Iteration")
    typecheck_iter = generate_iteration_typecheck()
    ruff_iter = generate_iteration_ruff()
    pytest_iter = generate_iteration_pytest()
    print(f"  typecheck: {len(typecheck_iter)} examples")
    print(f"  ruff_check: {len(ruff_iter)} examples")
    print(f"  pytest_run: {len(pytest_iter)} examples")
    all_examples.extend(typecheck_iter + ruff_iter + pytest_iter)

    # Pattern 4: Multi-step Workflows (30)
    print("\nPattern 4: Multi-step Workflows")
    typecheck_multi = generate_multistep_typecheck()
    ruff_multi = generate_multistep_ruff()
    pytest_multi = generate_multistep_pytest()
    print(f"  typecheck: {len(typecheck_multi)} examples")
    print(f"  ruff_check: {len(ruff_multi)} examples")
    print(f"  pytest_run: {len(pytest_multi)} examples")
    all_examples.extend(typecheck_multi + ruff_multi + pytest_multi)

    # Save to JSONL
    output_file = OUTPUT_DIR / "field_access_examples.jsonl"
    with output_file.open("w") as f:
        for example in all_examples:
            # Convert to JSONL dict
            f.write(json.dumps(example.to_jsonl_dict()) + "\n")

    print(f"\n{'='*60}")
    print(f"Total examples generated: {len(all_examples)}")
    print(f"Saved to: {output_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
