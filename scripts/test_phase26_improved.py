#!/usr/bin/env python3
"""Improved Phase 26 validation suite with strict scoring.

Fixes identified in Phase 26 analysis:
1. Tool identity checking - Verifies correct tool is called for each query
2. AST validation - Ensures generated code is syntactically valid
3. Schema validation - Checks that accessed fields exist on Pydantic models
4. Dual scoring - Reports both "soft" (substring matching) and "strict" (all checks pass)

Key improvements:
- Detects when model calls run_command() instead of typed tools (typecheck, ruff_check, pytest_run)
- Catches hallucinated fields (e.g., result.violation_list doesn't exist on RuffResult)
- Identifies typos in field names (e.g., result.violiolations → result.violations)
- Validates that field access is semantically appropriate (e.g., result.failed is int, not list)

Categories:
  A. Single-tool discrimination (5 queries, 100% target)
  B. Conditional logic (5 queries, 80% target)
  C. Field access (5 queries, 80% target)
  D. Iteration (5 queries, 80% target)
  E. Multi-step workflows (5 queries, 60% target)

Overall target: 80%+ (20/25)
Critical metric: Strict accuracy ≥80% (validates code quality, not just pattern matching)
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Literal

from mlx_lm import generate, load

# Import shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from punie.agent.prompt_utils import (
    extract_tool_calls_from_response,
    format_prompt,
    is_tool_response,
    validate_python_code,
)

# Type for expected tool
ExpectedTool = Literal["typecheck", "ruff_check", "pytest_run", "run_command", "any"]

# Test queries organized by category with expected tools
TEST_QUERIES = {
    "A_discrimination": [
        ("What is dependency injection?", "direct", None, "Concept question - should not call tools"),
        ("What's the difference between Protocol and ABC?", "direct", None, "Comparison question - should not call tools"),
        ("When should I use TypedDict?", "direct", None, "Best practice question - should not call tools"),
        ("Find all classes in src/", "tool", "any", "Search query - should call tool"),
        ("Check types in src/punie/agent/", "tool", "typecheck", "Type check query - should call typecheck"),
    ],
    "B_conditional": [
        ("Check types in src/ and tell me if there are errors", "field_access", "typecheck", "Should access result.error_count"),
        ("Run ruff on src/ and report if violations found", "field_access", "ruff_check", "Should access result.violation_count"),
        ("Run tests and tell me if all passed", "field_access", "pytest_run", "Should access result.success or result.failed"),
        ("Check if src/punie/ has more than 5 type warnings", "field_access", "typecheck", "Should access result.warning_count"),
        ("Is src/punie/agent/ ruff-clean?", "field_access", "ruff_check", "Should access result.success"),
    ],
    "C_field_access": [
        ("How many type errors are in src/?", "field_access", "typecheck", "Should print result.error_count"),
        ("Show me the first type error in src/", "field_access", "typecheck", "Should access result.errors[0]"),
        ("How many ruff violations are fixable in src/?", "field_access", "ruff_check", "Should access result.fixable_count"),
        ("What's the success rate of the test suite?", "field_access", "pytest_run", "Should access result.passed/total"),
        ("List all violation codes found by ruff", "field_access", "ruff_check", "Should iterate result.violations"),
    ],
    "D_iteration": [
        ("List all type errors in src/punie/", "field_access", "typecheck", "Should iterate result.errors"),
        ("Show me all failed tests", "field_access", "pytest_run", "Should iterate result.tests with filter"),
        ("Group ruff violations by file", "field_access", "ruff_check", "Should iterate result.violations"),
        ("Show first 3 type errors with line numbers", "field_access", "typecheck", "Should iterate result.errors[:3]"),
        ("Find all fixable ruff violations", "field_access", "ruff_check", "Should iterate with v.fixable filter"),
    ],
    "E_multistep": [
        ("Check types and read the file with the most errors", "field_access", "typecheck", "Check → count by file → read"),
        ("Run tests and show details of first failure", "field_access", "pytest_run", "Run → filter failed → access first"),
        ("Find the most common ruff violation", "field_access", "ruff_check", "Check → count by code → find max"),
        ("Check types and show errors only (not warnings)", "field_access", "typecheck", "Check → filter by severity"),
        ("Run ruff and compare fixable vs non-fixable", "field_access", "ruff_check", "Check → calculate both counts"),
    ],
}


# Schema definitions: valid fields for each typed tool result
TYPECHECK_FIELDS = {
    "success", "error_count", "warning_count", "errors", "parse_error",
    # Fields on TypeCheckError nested objects
    "file", "line", "column", "severity", "code", "message",
}

RUFF_FIELDS = {
    "success", "violation_count", "fixable_count", "violations", "parse_error",
    # Fields on RuffViolation nested objects
    "file", "line", "column", "code", "message", "fixable",
}

PYTEST_FIELDS = {
    "success", "passed", "failed", "errors", "skipped", "duration", "tests", "parse_error",
    # Fields on TestCase nested objects
    "name", "outcome", "message",
}


def check_tool_identity(code: str, expected_tool: ExpectedTool | None) -> tuple[bool, str | None]:
    """Check if code calls the expected tool.

    Args:
        code: Python code to check
        expected_tool: Expected tool name ("typecheck", "ruff_check", "pytest_run", "any", or None)

    Returns:
        Tuple of (is_correct, error_message)
    """
    if expected_tool is None or expected_tool == "any":
        return (True, None)

    # Check for tool function calls
    has_typecheck = "typecheck(" in code
    has_ruff = "ruff_check(" in code
    has_pytest = "pytest_run(" in code
    has_run_command = "run_command(" in code

    # If expected tool is called, that's correct
    if expected_tool == "typecheck" and has_typecheck:
        return (True, None)
    elif expected_tool == "ruff_check" and has_ruff:
        return (True, None)
    elif expected_tool == "pytest_run" and has_pytest:
        return (True, None)
    elif expected_tool == "run_command" and has_run_command:
        return (True, None)

    # If wrong tool was called, that's incorrect
    if has_run_command:
        return (False, f"Called run_command() instead of {expected_tool}()")
    elif has_typecheck and expected_tool != "typecheck":
        return (False, f"Called typecheck() instead of {expected_tool}()")
    elif has_ruff and expected_tool != "ruff_check":
        return (False, f"Called ruff_check() instead of {expected_tool}()")
    elif has_pytest and expected_tool != "pytest_run":
        return (False, f"Called pytest_run() instead of {expected_tool}()")

    # No tool call found when one was expected
    return (False, f"Expected {expected_tool}() but no tool call found")


def check_schema_validity(code: str, expected_tool: ExpectedTool | None) -> tuple[bool, list[str]]:
    """Check if field accesses in code are valid according to Pydantic schema.

    Args:
        code: Python code to check
        expected_tool: Expected tool (determines which schema to validate against)

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    if expected_tool is None or expected_tool == "any":
        return (True, [])

    # Determine which schema to use
    if expected_tool == "typecheck":
        valid_fields = TYPECHECK_FIELDS
    elif expected_tool == "ruff_check":
        valid_fields = RUFF_FIELDS
    elif expected_tool == "pytest_run":
        valid_fields = PYTEST_FIELDS
    else:
        return (True, [])  # No schema validation for run_command

    # Extract field accesses: result.field_name or result.field_name[...]
    # Also check for nested accesses like error.file, violation.code, test.name
    field_pattern = r"\bresult\.(\w+)|(?:error|violation|test|v|e|t)\.(\w+)"
    matches = re.finditer(field_pattern, code)

    errors = []
    seen_fields = set()

    for match in matches:
        field = match.group(1) or match.group(2)
        if field and field not in seen_fields:
            seen_fields.add(field)
            if field not in valid_fields:
                errors.append(f"Field '{field}' does not exist on {expected_tool} result model")

    # Check for common typos
    if "violiolations" in code:  # Actual typo found in Phase 26 results
        errors.append("Typo: 'violiolations' → should be 'violations'")

    is_valid = len(errors) == 0
    return (is_valid, errors)


def check_semantic_validity(code: str, expected_tool: ExpectedTool | None) -> tuple[bool, list[str]]:
    """Check if field accesses are semantically valid (e.g., indexing an int).

    Args:
        code: Python code to check
        expected_tool: Expected tool (determines semantic rules)

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    if expected_tool != "pytest_run":
        return (True, [])  # Only pytest has known semantic issues

    errors = []

    # Check for result.failed[...] - failed is int, not list
    if "result.failed[" in code:
        errors.append("result.failed is int, not list - cannot index it")

    # Check for result.passed[...] - passed is int, not list
    if "result.passed[" in code:
        errors.append("result.passed is int, not list - cannot index it")

    # Check for fields that don't exist on TestCase (common from Phase 26 logs)
    if "result.tests[" in code or "for test in result.tests" in code:
        if ".location" in code and "test.location" in code:
            errors.append("TestCase has no 'location' field (has: name, outcome, duration, message)")
        if ".stack" in code and "test.stack" in code:
            errors.append("TestCase has no 'stack' field (closest is 'message')")

    is_valid = len(errors) == 0
    return (is_valid, errors)


def soft_check_field_access(response: str, query_type: str) -> bool:
    """Original soft checking logic (substring matching).

    This is the Phase 26.0 validator - generous, doesn't verify correctness.
    Kept for comparison purposes.
    """
    if query_type == "direct":
        return not is_tool_response(response)

    if query_type == "tool":
        return is_tool_response(response)

    if query_type == "field_access":
        if not is_tool_response(response):
            return False

        # Check for common field access patterns
        field_patterns = [
            "result.error_count",
            "result.warning_count",
            "result.success",
            "result.errors",
            "result.violation_count",
            "result.fixable_count",
            "result.violations",
            "result.passed",
            "result.failed",
            "result.tests",
            ".errors[",
            ".violations[",
            ".tests[",
            "for error in result.errors",
            "for v in result.violations",
            "for test in result.tests",
        ]

        return any(pattern in response for pattern in field_patterns)

    return False


def strict_check_field_access(
    response: str, query_type: str, expected_tool: ExpectedTool | None
) -> tuple[bool, list[str]]:
    """Strict checking with tool identity, AST, and schema validation.

    Returns:
        Tuple of (is_correct, list_of_issues)
    """
    issues = []

    # Check 1: Basic gate (same as soft)
    if query_type == "direct":
        if is_tool_response(response):
            issues.append("Direct query but tool was called")
            return (False, issues)
        return (True, [])

    if query_type == "tool" or query_type == "field_access":
        if not is_tool_response(response):
            issues.append("Expected tool call but none found")
            return (False, issues)

        # Extract tool call code
        code_blocks = extract_tool_calls_from_response(response)
        if not code_blocks:
            issues.append("Tool call marker present but no code extracted")
            return (False, issues)

        # Validate each code block
        for i, code in enumerate(code_blocks):
            # Check 2: AST validation
            is_valid_syntax, syntax_error = validate_python_code(code)
            if not is_valid_syntax:
                issues.append(f"Code block {i+1} has syntax error: {syntax_error}")

            # Check 3: Tool identity
            if expected_tool:
                tool_correct, tool_error = check_tool_identity(code, expected_tool)
                if not tool_correct:
                    issues.append(f"Code block {i+1}: {tool_error}")

            # Check 4: Schema validation (only for field_access queries)
            if query_type == "field_access" and expected_tool:
                schema_valid, schema_errors = check_schema_validity(code, expected_tool)
                if not schema_valid:
                    for error in schema_errors:
                        issues.append(f"Code block {i+1}: {error}")

                # Check 5: Semantic validation
                semantic_valid, semantic_errors = check_semantic_validity(code, expected_tool)
                if not semantic_valid:
                    for error in semantic_errors:
                        issues.append(f"Code block {i+1}: {error}")

        is_correct = len(issues) == 0
        return (is_correct, issues)

    return (False, ["Unknown query type"])


def run_validation_suite(model_path: str) -> dict:
    """Run full 25-query validation suite with dual scoring."""
    print(f"Loading model: {model_path}")
    model_and_tokenizer = load(model_path)
    if isinstance(model_and_tokenizer, tuple):
        model, tokenizer = model_and_tokenizer
    else:
        model = model_and_tokenizer
        tokenizer = None
    print("Model loaded successfully\n")

    results = {}
    soft_correct = 0
    strict_correct = 0
    total_queries = 0
    soft_field_access_correct = 0
    strict_field_access_correct = 0
    field_access_total = 0

    for category, queries in TEST_QUERIES.items():
        print(f"\n{'='*80}")
        print(f"Category {category.replace('_', ' ').title()}")
        print(f"{'='*80}\n")

        category_results = []
        category_soft = 0
        category_strict = 0

        for i, (query, expected_type, expected_tool, description) in enumerate(queries, 1):
            print(f"Query {i}/5: {query}")
            print(f"Expected: {expected_type}" + (f" (tool: {expected_tool})" if expected_tool else ""))
            print(f"Description: {description}")

            # Generate response
            prompt = format_prompt(query, model_path)
            start_time = time.time()

            response = generate(
                model,
                tokenizer,
                prompt=prompt,
                max_tokens=500,
                temp=0,  # Deterministic generation
            )

            elapsed = time.time() - start_time

            # Soft scoring (original)
            soft_pass = soft_check_field_access(response, expected_type)

            # Strict scoring (new)
            strict_pass, strict_issues = strict_check_field_access(response, expected_type, expected_tool)

            # Update counters
            soft_correct += soft_pass
            strict_correct += strict_pass
            category_soft += soft_pass
            category_strict += strict_pass
            total_queries += 1

            # Track field access specifically (categories B-E)
            if expected_type == "field_access":
                field_access_total += 1
                soft_field_access_correct += soft_pass
                strict_field_access_correct += strict_pass

            # Print result
            soft_status = "✓" if soft_pass else "✗"
            strict_status = "✓" if strict_pass else "✗"
            print(f"Soft: {soft_status}  Strict: {strict_status} ({elapsed:.2f}s)")

            if not strict_pass and strict_issues:
                print("Issues found:")
                for issue in strict_issues:
                    print(f"  - {issue}")

            print(f"Response preview: {response[:150]}...")
            print()

            category_results.append({
                "query": query,
                "expected_type": expected_type,
                "expected_tool": expected_tool,
                "description": description,
                "response": response,
                "soft_correct": soft_pass,
                "strict_correct": strict_pass,
                "strict_issues": strict_issues,
                "elapsed_seconds": elapsed,
            })

        category_soft_accuracy = category_soft / len(queries) * 100
        category_strict_accuracy = category_strict / len(queries) * 100
        print(f"Category soft: {category_soft}/{len(queries)} ({category_soft_accuracy:.1f}%)")
        print(f"Category strict: {category_strict}/{len(queries)} ({category_strict_accuracy:.1f}%)")

        results[category] = {
            "queries": category_results,
            "soft_correct": category_soft,
            "strict_correct": category_strict,
            "total": len(queries),
            "soft_accuracy": category_soft_accuracy,
            "strict_accuracy": category_strict_accuracy,
        }

    # Calculate overall metrics
    soft_accuracy = soft_correct / total_queries * 100
    strict_accuracy = strict_correct / total_queries * 100
    soft_field_rate = soft_field_access_correct / field_access_total * 100 if field_access_total > 0 else 0
    strict_field_rate = strict_field_access_correct / field_access_total * 100 if field_access_total > 0 else 0

    print(f"\n{'='*80}")
    print("OVERALL RESULTS")
    print(f"{'='*80}")
    print("\nSOFT SCORING (Phase 26.0 - substring matching):")
    print(f"  Total: {soft_correct}/{total_queries} ({soft_accuracy:.1f}%)")
    print(f"  Field access rate: {soft_field_access_correct}/{field_access_total} ({soft_field_rate:.1f}%)")

    print("\nSTRICT SCORING (Phase 26.1 - full validation):")
    print(f"  Total: {strict_correct}/{total_queries} ({strict_accuracy:.1f}%)")
    print(f"  Field access rate: {strict_field_access_correct}/{field_access_total} ({strict_field_rate:.1f}%)")

    print(f"\nACCURACY GAP: {soft_accuracy - strict_accuracy:.1f} percentage points")
    print("This gap represents code that LOOKS right but would FAIL at runtime\n")

    # Category breakdown
    print("Category Breakdown (Soft / Strict):")
    for category, category_result in results.items():
        soft_pct = category_result['soft_accuracy']
        strict_pct = category_result['strict_accuracy']
        gap = soft_pct - strict_pct
        print(f"  {category}: {soft_pct:.0f}% / {strict_pct:.0f}% (gap: {gap:.0f} pts)")

    print()

    # Success criteria
    print("Success Criteria (Strict):")
    print(f"  Overall ≥80%: {'✓ PASS' if strict_accuracy >= 80 else '✗ FAIL'} ({strict_accuracy:.1f}%)")
    print(f"  Field access ≥80%: {'✓ PASS' if strict_field_rate >= 80 else '✗ FAIL'} ({strict_field_rate:.1f}%)")
    discrimination_strict = results['A_discrimination']['strict_accuracy']
    print(f"  Discrimination 100%: {'✓ PASS' if discrimination_strict == 100 else '✗ FAIL'} ({discrimination_strict:.1f}%)")

    return {
        "model_path": model_path,
        "total_queries": total_queries,
        "soft_correct": soft_correct,
        "strict_correct": strict_correct,
        "soft_accuracy": soft_accuracy,
        "strict_accuracy": strict_accuracy,
        "accuracy_gap": soft_accuracy - strict_accuracy,
        "soft_field_access_correct": soft_field_access_correct,
        "strict_field_access_correct": strict_field_access_correct,
        "field_access_total": field_access_total,
        "soft_field_access_rate": soft_field_rate,
        "strict_field_access_rate": strict_field_rate,
        "by_category": results,
    }


def main():
    """Run improved Phase 26 validation suite."""
    if len(sys.argv) < 2:
        print("Usage: python test_phase26_improved.py <model_path>")
        print("Example: python test_phase26_improved.py fused_model_qwen3_phase26_5bit")
        sys.exit(1)

    model_path = sys.argv[1]

    if not Path(model_path).exists():
        print(f"Error: Model path not found: {model_path}")
        sys.exit(1)

    print("="*80)
    print("Phase 26 Improved Validation Suite")
    print("="*80)
    print(f"Model: {model_path}")
    print("Queries: 25 (5 categories × 5 queries)")
    print("Scoring: Dual (soft + strict)")
    print("Target: 80%+ strict accuracy")
    print("="*80)
    print()

    # Run validation
    results = run_validation_suite(model_path)

    # Save results to JSON
    model_name = Path(model_path).name
    output_file = Path(f"logs/phase26_improved_{model_name}.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    # Exit code based on strict success criteria
    strict_overall_pass = results["strict_accuracy"] >= 80
    strict_field_pass = results["strict_field_access_rate"] >= 80
    discrimination_pass = results["by_category"]["A_discrimination"]["strict_accuracy"] == 100

    if strict_overall_pass and strict_field_pass and discrimination_pass:
        print("\n✓ All strict success criteria met!")
        sys.exit(0)
    else:
        print("\n✗ Some strict success criteria not met")
        sys.exit(1)


if __name__ == "__main__":
    main()
