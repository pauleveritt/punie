"""Generate Phase 27 rebalance examples (ruff, pytest, typecheck, cross-tool workflows).

Creates 120 examples:
- 40 ruff_check examples (currently 2.8% → target ~8%)
- 40 pytest_run examples (currently 3.8% → target ~8%)
- 20 typecheck examples (maintain representation)
- 20 cross-tool workflows (e.g., ruff → fix → pytest → typecheck)

All examples follow Phase 26 structural norms:
- 100% system messages
- ~37% multi-turn (5-message format)
- ~33% preambles
- Code Mode format (<tool_call><function=execute_code>)
"""

import json
import random
from pathlib import Path

# Set seed for reproducibility
random.seed(44)


def create_ruff_check_examples() -> list[dict]:
    """Create 40 ruff_check examples."""
    examples = []

    queries = [
        ("Lint src/ with ruff", "src"),
        ("Check code style in src/", "src"),
        ("Run ruff on the project", "."),
        ("Check for linting violations", "src"),
        ("Lint src/services/", "src/services"),
        ("Check code quality in src/", "src"),
        ("Run ruff linter on src/", "src"),
        ("Check for fixable violations", "src"),
        ("Lint src/models/", "src/models"),
        ("Check code style violations", "src"),
        ("Run ruff check on src/", "src"),
        ("Show linting issues in src/", "src"),
        ("Check src/ for style violations", "src"),
        ("Lint src/api/", "src/api"),
        ("Run ruff on src/utils/", "src/utils"),
        ("Check for code violations", "src"),
        ("Lint the codebase", "."),
        ("Check src/db/ for violations", "src/db"),
        ("Run linter on src/", "src"),
        ("Check code quality", "src"),
    ]

    for query, path in queries:
        # Single-turn
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = ruff_check("{path}")\nif result.success:\n    print("No violations found")\nelse:\n    print(f"Found {{result.violation_count}} violations")\n    print(f"Fixable: {{result.fixable_count}}")\n    for v in result.violations[:5]:\n        fix_str = "[*]" if v.fixable else ""\n        print(f"  {{v.file}}:{{v.line}} {{v.code}} {{fix_str}} {{v.message}}")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn with field access
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll run ruff and check for violations.",
                },
                {
                    "role": "user",
                    "content": "Show me the results.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = ruff_check("{path}")\nprint(f"Success: {{result.success}}")\nprint(f"Violations: {{result.violation_count}}")\nprint(f"Fixable: {{result.fixable_count}}")\n\nif not result.success:\n    # Group by code\n    by_code = {{}}\n    for v in result.violations:\n        if v.code not in by_code:\n            by_code[v.code] = 0\n        by_code[v.code] += 1\n    print("\\nBy rule:")\n    for code, count in sorted(by_code.items(), key=lambda x: x[1], reverse=True)[:5]:\n        print(f"  {{code}}: {{count}}")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:40]


def create_pytest_run_examples() -> list[dict]:
    """Create 40 pytest_run examples."""
    examples = []

    queries = [
        ("Run tests in tests/", "tests"),
        ("Execute pytest on tests/", "tests"),
        ("Run all tests", "tests"),
        ("Execute test suite", "tests"),
        ("Run pytest on tests/unit/", "tests/unit"),
        ("Execute tests in tests/", "tests"),
        ("Run test suite in tests/", "tests"),
        ("Execute pytest", "tests"),
        ("Run tests/integration/", "tests/integration"),
        ("Execute unit tests", "tests/unit"),
        ("Run pytest for tests/", "tests"),
        ("Execute all tests", "tests"),
        ("Run tests/models/", "tests/models"),
        ("Execute pytest suite", "tests"),
        ("Run tests/services/", "tests/services"),
        ("Execute test files", "tests"),
        ("Run pytest tests", "tests"),
        ("Execute tests/api/", "tests/api"),
        ("Run all test files", "tests"),
        ("Execute pytest runner", "tests"),
    ]

    for query, path in queries:
        # Single-turn
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = pytest_run("{path}")\nif result.success:\n    print(f"All {{result.passed}} tests passed!")\nelse:\n    print(f"Tests: {{result.passed}} passed, {{result.failed}} failed")\n    if result.failed > 0:\n        for test in result.tests:\n            if test.outcome == "failed":\n                print(f"  FAIL: {{test.name}}")\nprint(f"Duration: {{result.duration:.2f}}s")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn with analysis
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll run the test suite.",
                },
                {
                    "role": "user",
                    "content": "Show me the results.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = pytest_run("{path}")\nprint(f"Success: {{result.success}}")\nprint(f"Passed: {{result.passed}}")\nprint(f"Failed: {{result.failed}}")\nprint(f"Skipped: {{result.skipped}}")\nprint(f"Duration: {{result.duration:.2f}}s")\n\nif result.failed > 0:\n    print(f"\\nFailed tests:")\n    for test in result.tests:\n        if test.outcome == "failed":\n            print(f"  {{test.name}}")\n            if test.message:\n                print(f"    {{test.message[:100]}}")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:40]


def create_typecheck_examples() -> list[dict]:
    """Create 20 typecheck examples."""
    examples = []

    queries = [
        ("Type check src/", "src"),
        ("Run ty on src/", "src"),
        ("Check types in src/", "src"),
        ("Type check src/services/", "src/services"),
        ("Run type checker on src/", "src"),
        ("Check for type errors", "src"),
        ("Run ty type checker", "src"),
        ("Type check src/models/", "src/models"),
        ("Check types in project", "src"),
        ("Run type checking", "src"),
    ]

    for query, path in queries:
        # Single-turn
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = typecheck("{path}")\nif result.success:\n    print("No type errors found")\nelse:\n    print(f"Found {{result.error_count}} errors")\n    for error in result.errors[:5]:\n        print(f"  {{error.file}}:{{error.line}} {{error.code}} - {{error.message}}")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn
        if len(examples) % 2 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll run the type checker.",
                },
                {
                    "role": "user",
                    "content": "Show me any errors.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = typecheck("{path}")\nprint(f"Success: {{result.success}}")\nprint(f"Errors: {{result.error_count}}")\nprint(f"Warnings: {{result.warning_count}}")\n\nif result.error_count > 0:\n    for error in result.errors:\n        print(f"{{error.severity.upper()}}: {{error.file}}:{{error.line}}")\n        print(f"  {{error.message}}")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:20]


def create_cross_tool_workflow_examples() -> list[dict]:
    """Create 20 cross-tool workflow examples."""
    examples = []

    workflows = [
        ("Check code quality: run ruff, then pytest, then typecheck", "src", "tests"),
        ("Quality check src/: lint, test, type check", "src", "tests"),
        ("Run full quality suite on src/", "src", "tests"),
        ("Check src/ with all quality tools", "src", "tests"),
        ("Verify code quality: ruff + pytest + ty", "src", "tests"),
        ("Run quality checks on src/", "src", "tests"),
        ("Full quality check: lint, test, types", "src", "tests"),
        ("Check code health in src/", "src", "tests"),
        ("Run complete quality suite", "src", "tests"),
        ("Quality verify src/ with all tools", "src", "tests"),
    ]

    for query, src_path, test_path in workflows:
        # Multi-step workflow
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\n# Run all quality checks\nprint("Running quality checks...")\n\n# 1. Linting\nprint("\\n1. Linting with ruff:")\nruff = ruff_check("{src_path}")\nprint(f"   Violations: {{ruff.violation_count}}")\nif ruff.fixable_count > 0:\n    print(f"   Fixable: {{ruff.fixable_count}}")\n\n# 2. Type checking\nprint("\\n2. Type checking with ty:")\nty = typecheck("{src_path}")\nprint(f"   Errors: {{ty.error_count}}")\nprint(f"   Warnings: {{ty.warning_count}}")\n\n# 3. Testing\nprint("\\n3. Running tests:")\ntests = pytest_run("{test_path}")\nprint(f"   Passed: {{tests.passed}}")\nprint(f"   Failed: {{tests.failed}}")\nprint(f"   Duration: {{tests.duration:.2f}}s")\n\n# Summary\nprint("\\n=== Summary ===")\nall_pass = ruff.success and ty.success and tests.success\nif all_pass:\n    print("✓ All quality checks passed!")\nelse:\n    print("✗ Quality checks failed:")\n    if not ruff.success:\n        print(f"  - {{ruff.violation_count}} lint violations")\n    if not ty.success:\n        print(f"  - {{ty.error_count}} type errors")\n    if not tests.success:\n        print(f"  - {{tests.failed}} test failures")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn workflow with preamble
        if len(examples) % 2 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll run a complete quality check with ruff, ty, and pytest.",
                },
                {
                    "role": "user",
                    "content": "Show me the results.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\n# Quick quality check\nruff = ruff_check("{src_path}")\nty = typecheck("{src_path}")\ntests = pytest_run("{test_path}")\n\n# Calculate scores\ntotal_issues = ruff.violation_count + ty.error_count + tests.failed\nquality_score = 100 if total_issues == 0 else max(0, 100 - total_issues * 5)\n\nprint(f"Quality Score: {{quality_score}}/100")\nprint(f"\\nBreakdown:")\nprint(f"  Lint: {{\'✓\' if ruff.success else \'✗\'}} ({{ruff.violation_count}} violations)")\nprint(f"  Types: {{\'✓\' if ty.success else \'✗\'}} ({{ty.error_count}} errors)")\nprint(f"  Tests: {{\'✓\' if tests.success else \'✗\'}} ({{tests.passed}}/{{tests.passed + tests.failed}} passed)")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:20]


def main():
    """Generate all Phase 27 rebalance examples."""
    output_dir = Path("data/phase27_rebalance")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_examples = []

    print("Generating ruff_check examples...")
    all_examples.extend(create_ruff_check_examples())

    print("Generating pytest_run examples...")
    all_examples.extend(create_pytest_run_examples())

    print("Generating typecheck examples...")
    all_examples.extend(create_typecheck_examples())

    print("Generating cross-tool workflow examples...")
    all_examples.extend(create_cross_tool_workflow_examples())

    # Shuffle examples
    random.shuffle(all_examples)

    # Save as JSONL
    output_file = output_dir / "phase27_rebalance_examples.jsonl"
    with open(output_file, "w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")

    print(f"\nGenerated {len(all_examples)} rebalance examples")
    print(f"Saved to: {output_file}")

    # Print distribution
    single_turn = sum(1 for ex in all_examples if len(ex["messages"]) == 3)
    multi_turn = sum(1 for ex in all_examples if len(ex["messages"]) > 3)
    print("\nDistribution:")
    print(f"  Single-turn: {single_turn} ({single_turn/len(all_examples)*100:.1f}%)")
    print(f"  Multi-turn: {multi_turn} ({multi_turn/len(all_examples)*100:.1f}%)")


if __name__ == "__main__":
    main()
