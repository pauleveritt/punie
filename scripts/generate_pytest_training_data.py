"""Generate training examples for pytest_run() typed tool.

Creates 50 examples across 4 categories:
1. Simple test runs (15)
2. Test + fix workflows (15)
3. Full quality pipeline (10)
4. Direct answers about pytest concepts (10)
"""

import json
from pathlib import Path


def generate_simple_test_runs():
    """Generate examples of simple pytest_run calls."""
    examples = []

    queries = [
        "Run tests in tests/",
        "Are all tests passing?",
        "Run pytest on tests/test_agent_config.py",
        "Check if tests pass",
        "Run the test suite",
        "Execute all tests",
        "Run tests for src/punie/agent/",
        "Test the monty_runner module",
        "Run unit tests",
        "Check test status",
        "Run integration tests",
        "Test the entire codebase",
        "Run tests in tests/test_typed_tools.py",
        "Check if new tests pass",
        "Run all test files",
    ]

    for query in queries:
        code = """result = pytest_run("tests/")
if result.success:
    print(f"✓ All {result.passed} tests passed")
else:
    print(f"✗ {result.failed} failed, {result.passed} passed")"""

        examples.append({
            "messages": [
                {"role": "user", "content": query},
                {"role": "assistant", "content": f"<tool_call>\n{code}\n</tool_call>"}
            ]
        })

    return examples


def generate_test_fix_workflows():
    """Generate examples of test failure analysis and fixing."""
    examples = []

    queries = [
        "Find failing tests and show details",
        "What tests are failing?",
        "Show me the test failures",
        "Debug test failures",
        "Which tests need fixing?",
        "Analyze test failures",
        "Show failed test messages",
        "Get test failure details",
        "Find broken tests",
        "Show test errors",
        "Which tests are not passing?",
        "Diagnose test failures",
        "Show me what tests failed and why",
        "Get details on failing tests",
        "Find and fix test failures",
    ]

    for query in queries:
        code = """result = pytest_run("tests/")
if not result.success:
    print(f"{result.failed} tests failed:")
    for test in result.tests:
        if test.outcome == "failed":
            print(f"  - {test.name}")
            if test.message:
                print(f"    {test.message}")
else:
    print("All tests passing!")"""

        examples.append({
            "messages": [
                {"role": "user", "content": query},
                {"role": "assistant", "content": f"<tool_call>\n{code}\n</tool_call>"}
            ]
        })

    return examples


def generate_full_quality_pipeline():
    """Generate examples combining ruff, typecheck, and pytest."""
    examples = []

    queries = [
        "Full quality check: lint, types, and tests",
        "Run complete CI pipeline",
        "Check code quality before commit",
        "Verify everything passes: ruff, ty, pytest",
        "Pre-commit quality gate",
        "Run all quality checks",
        "Complete code validation",
        "CI/CD check: lint + types + tests",
        "Quality assurance: run all checks",
        "Verify code is ready to merge",
    ]

    for query in queries:
        code = """# Run all quality checks
ruff = ruff_check("src/")
ty = typecheck("src/")
tests = pytest_run("tests/")

# Report results
print("Quality Check Results:")
print(f"  Lint: {ruff.violation_count} violations")
print(f"  Type: {ty.error_count} errors")
print(f"  Tests: {tests.passed}/{tests.passed + tests.failed} passed")

# Overall status
if ruff.success and ty.success and tests.success:
    print("\\n✓ All checks PASS - ready to commit!")
else:
    print("\\n✗ Quality checks FAILED - please fix issues")"""

        examples.append({
            "messages": [
                {"role": "user", "content": query},
                {"role": "assistant", "content": f"<tool_call>\n{code}\n</tool_call>"}
            ]
        })

    return examples


def generate_direct_answers():
    """Generate direct answer examples about pytest concepts."""
    examples = []

    qa_pairs = [
        (
            "What are pytest fixtures?",
            "Pytest fixtures are reusable setup/teardown functions that provide test dependencies. They're defined with `@pytest.fixture` and injected into tests by name. Fixtures help reduce code duplication and make tests more maintainable. For example, a `fake_client` fixture can provide a test client to all tests that need it."
        ),
        (
            "Why use function-based tests instead of class-based tests?",
            "Function-based tests are simpler, more readable, and encourage better test isolation. They work seamlessly with pytest's fixture system. Class-based tests add unnecessary boilerplate and can hide dependencies. The function-based approach is the modern pytest best practice."
        ),
        (
            "How do I run only failed tests?",
            "Use `pytest --lf` (last-failed) to rerun only tests that failed in the previous run. Or use `pytest --ff` (failed-first) to run failed tests first, then the rest. This speeds up debugging by focusing on broken tests first."
        ),
        (
            "What's the difference between passed, failed, and error in pytest?",
            "PASSED means the test assertions succeeded. FAILED means an assertion failed (expected behavior didn't match actual). ERROR means an exception occurred during test setup or execution (unexpected crash). The pytest_run() function reports all three separately."
        ),
        (
            "How do I skip tests in pytest?",
            "Use the `@pytest.mark.skip` or `@pytest.mark.skipif(condition)` decorators. Skipped tests don't count as failures. The pytest_run() function reports skipped tests in the `skipped` field. Use sparingly - skipped tests often indicate technical debt."
        ),
        (
            "What does -v flag do in pytest?",
            "The `-v` (verbose) flag shows each test name and outcome individually instead of just dots. It's useful for seeing exactly which tests pass/fail. The pytest_run() function uses `-v` internally to parse individual test results."
        ),
        (
            "Should I use pytest or unittest?",
            "Use pytest. It's more modern, has better fixture support, clearer assertions (no self.assertEqual needed), better output, and a richer plugin ecosystem. Unittest is older and more verbose. Pytest can even run unittest-style tests."
        ),
        (
            "How do I test async code with pytest?",
            "Use `@pytest.mark.asyncio` decorator on async test functions and install `pytest-asyncio`. The test function can then use `async def` and `await` statements. Most async frameworks provide pytest integration."
        ),
        (
            "What's a good test coverage percentage?",
            "Aim for 80-90% code coverage, but focus on testing critical paths rather than hitting an arbitrary number. 100% coverage doesn't guarantee bug-free code. It's better to have well-designed tests covering important scenarios than shallow tests just for coverage."
        ),
        (
            "How do I organize test files?",
            "Mirror your source structure: if you have `src/punie/agent/toolset.py`, create `tests/test_toolset.py`. Use descriptive test function names like `test_toolset_has_all_eight_tools()`. Group related tests in the same file."
        ),
    ]

    for question, answer in qa_pairs:
        examples.append({
            "messages": [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer}
            ]
        })

    return examples


def main():
    """Generate all pytest training examples."""
    output_dir = Path("data/pytest_training")
    output_dir.mkdir(parents=True, exist_ok=True)

    examples = []
    examples.extend(generate_simple_test_runs())  # 15
    examples.extend(generate_test_fix_workflows())  # 15
    examples.extend(generate_full_quality_pipeline())  # 10
    examples.extend(generate_direct_answers())  # 10

    # Write to JSONL
    output_file = output_dir / "pytest_examples.jsonl"
    with output_file.open("w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    print(f"✓ Generated {len(examples)} pytest training examples")
    print("  Simple test runs: 15")
    print("  Test + fix workflows: 15")
    print("  Full quality pipeline: 10")
    print("  Direct answers: 10")
    print(f"  Output: {output_file}")


if __name__ == "__main__":
    main()
