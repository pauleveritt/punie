#!/usr/bin/env python3
"""Phase 26 validation suite: 25-query test for field access patterns.

This suite tests whether the model learned to access structured fields on
typed tool results. Phase 23 baseline: 0% field access rate.

Categories:
  A. Single-tool discrimination (5 queries, 100% target)
  B. Conditional logic (5 queries, 80% target)
  C. Field access (5 queries, 80% target)
  D. Iteration (5 queries, 80% target)
  E. Multi-step workflows (5 queries, 60% target)

Overall target: 80%+ (20/25)
Critical metric: Field access rate ≥80% across B-E
"""

import json
import sys
import time
from pathlib import Path

from mlx_lm import generate, load

# Import shared prompt formatting utility
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from punie.agent.prompt_utils import format_prompt


# Test queries organized by category
TEST_QUERIES = {
    "A_discrimination": [
        ("What is dependency injection?", "direct", "Concept question - should not call tools"),
        ("What's the difference between Protocol and ABC?", "direct", "Comparison question - should not call tools"),
        ("When should I use TypedDict?", "direct", "Best practice question - should not call tools"),
        ("Find all classes in src/", "tool", "Search query - should call tool"),
        ("Check types in src/punie/agent/", "tool", "Type check query - should call tool"),
    ],
    "B_conditional": [
        ("Check types in src/ and tell me if there are errors", "field_access", "Should access result.error_count"),
        ("Run ruff on src/ and report if violations found", "field_access", "Should access result.violation_count"),
        ("Run tests and tell me if all passed", "field_access", "Should access result.success or result.failed"),
        ("Check if src/punie/ has more than 5 type warnings", "field_access", "Should access result.warning_count"),
        ("Is src/punie/agent/ ruff-clean?", "field_access", "Should access result.success"),
    ],
    "C_field_access": [
        ("How many type errors are in src/?", "field_access", "Should print result.error_count"),
        ("Show me the first type error in src/", "field_access", "Should access result.errors[0]"),
        ("How many ruff violations are fixable in src/?", "field_access", "Should access result.fixable_count"),
        ("What's the success rate of the test suite?", "field_access", "Should access result.passed/total"),
        ("List all violation codes found by ruff", "field_access", "Should iterate result.violations"),
    ],
    "D_iteration": [
        ("List all type errors in src/punie/", "field_access", "Should iterate result.errors"),
        ("Show me all failed tests", "field_access", "Should iterate result.tests with filter"),
        ("Group ruff violations by file", "field_access", "Should iterate result.violations"),
        ("Show first 3 type errors with line numbers", "field_access", "Should iterate result.errors[:3]"),
        ("Find all fixable ruff violations", "field_access", "Should iterate with v.fixable filter"),
    ],
    "E_multistep": [
        ("Check types and read the file with the most errors", "field_access", "Check → count by file → read"),
        ("Run tests and show details of first failure", "field_access", "Run → filter failed → access first"),
        ("Find the most common ruff violation", "field_access", "Check → count by code → find max"),
        ("Check types and show errors only (not warnings)", "field_access", "Check → filter by severity"),
        ("Run ruff and compare fixable vs non-fixable", "field_access", "Check → calculate both counts"),
    ],
}


def check_field_access_in_response(response: str, query_type: str) -> bool:
    """Check if response contains field access patterns.

    Args:
        response: Model response text
        query_type: Expected query type ("direct", "tool", "field_access")

    Returns:
        True if response matches expected type
    """
    # For direct answers, check that NO tool was called
    if query_type == "direct":
        has_tool_call = "<tool_call>" in response or "```json" in response
        return not has_tool_call

    # For basic tool queries, just check that a tool was called
    if query_type == "tool":
        return "<tool_call>" in response or "```json" in response

    # For field_access queries, check for actual field access patterns
    if query_type == "field_access":
        if "<tool_call>" not in response and "```json" not in response:
            return False  # No tool call at all

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


def run_validation_suite(model_path: str) -> dict:
    """Run full 25-query validation suite.

    Args:
        model_path: Path to model directory

    Returns:
        Dict with results by category and overall metrics
    """
    print(f"Loading model: {model_path}")
    model_and_tokenizer = load(model_path)
    # mlx_lm.load returns (model, tokenizer) tuple
    if isinstance(model_and_tokenizer, tuple):
        model, tokenizer = model_and_tokenizer
    else:
        model = model_and_tokenizer
        tokenizer = None
    print("Model loaded successfully\n")

    results = {}
    total_correct = 0
    total_queries = 0
    field_access_correct = 0
    field_access_total = 0

    for category, queries in TEST_QUERIES.items():
        print(f"\n{'='*60}")
        print(f"Category {category.replace('_', ' ').title()}")
        print(f"{'='*60}\n")

        category_results = []
        category_correct = 0

        for i, (query, expected_type, description) in enumerate(queries, 1):
            print(f"Query {i}/5: {query}")
            print(f"Expected: {expected_type}")
            print(f"Description: {description}")

            # Generate response
            # Use shared utility to guarantee consistency with training format
            prompt = format_prompt(query, model_path)
            start_time = time.time()

            response = generate(
                model,
                tokenizer,
                prompt=prompt,
                max_tokens=500,
            )

            elapsed = time.time() - start_time

            # Check if response is correct
            is_correct = check_field_access_in_response(response, expected_type)
            category_correct += is_correct
            total_correct += is_correct
            total_queries += 1

            # Track field access specifically (categories B-E)
            if expected_type == "field_access":
                field_access_total += 1
                field_access_correct += is_correct

            # Print result
            status = "✓ PASS" if is_correct else "✗ FAIL"
            print(f"Result: {status} ({elapsed:.2f}s)")
            print(f"Response preview: {response[:200]}...")
            print()

            category_results.append({
                "query": query,
                "expected_type": expected_type,
                "description": description,
                "response": response,
                "correct": is_correct,
                "elapsed_seconds": elapsed,
            })

        category_accuracy = category_correct / len(queries) * 100
        print(f"Category accuracy: {category_correct}/{len(queries)} ({category_accuracy:.1f}%)")

        results[category] = {
            "queries": category_results,
            "correct": category_correct,
            "total": len(queries),
            "accuracy": category_accuracy,
        }

    # Calculate overall metrics
    overall_accuracy = total_correct / total_queries * 100
    field_access_rate = (
        field_access_correct / field_access_total * 100 if field_access_total > 0 else 0
    )

    print(f"\n{'='*60}")
    print("OVERALL RESULTS")
    print(f"{'='*60}")
    print(f"Total: {total_correct}/{total_queries} ({overall_accuracy:.1f}%)")
    print(f"Field access rate: {field_access_correct}/{field_access_total} ({field_access_rate:.1f}%)")
    print()

    # Category breakdown
    for category, category_result in results.items():
        print(f"  {category}: {category_result['correct']}/{category_result['total']} ({category_result['accuracy']:.1f}%)")

    print()

    # Success criteria
    print("Success Criteria:")
    print(f"  Overall ≥80%: {'✓ PASS' if overall_accuracy >= 80 else '✗ FAIL'} ({overall_accuracy:.1f}%)")
    print(f"  Field access ≥80%: {'✓ PASS' if field_access_rate >= 80 else '✗ FAIL'} ({field_access_rate:.1f}%)")
    print(f"  Discrimination 100%: {'✓ PASS' if results['A_discrimination']['accuracy'] == 100 else '✗ FAIL'} ({results['A_discrimination']['accuracy']:.1f}%)")

    return {
        "model_path": model_path,
        "total_correct": total_correct,
        "total_queries": total_queries,
        "overall_accuracy": overall_accuracy,
        "field_access_correct": field_access_correct,
        "field_access_total": field_access_total,
        "field_access_rate": field_access_rate,
        "by_category": results,
    }


def main():
    """Run Phase 26 validation suite."""
    if len(sys.argv) < 2:
        print("Usage: python test_phase26_validation.py <model_path>")
        print("Example: python test_phase26_validation.py fused_model_qwen3_phase26_6bit")
        sys.exit(1)

    model_path = sys.argv[1]

    if not Path(model_path).exists():
        print(f"Error: Model path not found: {model_path}")
        sys.exit(1)

    print("="*60)
    print("Phase 26 Validation Suite")
    print("="*60)
    print(f"Model: {model_path}")
    print("Queries: 25 (5 categories × 5 queries)")
    print("Target: 80%+ overall, 80%+ field access rate")
    print("="*60)
    print()

    # Run validation
    results = run_validation_suite(model_path)

    # Save results to JSON
    model_name = Path(model_path).name
    output_file = Path(f"logs/phase26_validation_{model_name}.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    # Exit code based on success criteria
    overall_pass = results["overall_accuracy"] >= 80
    field_access_pass = results["field_access_rate"] >= 80
    discrimination_pass = results["by_category"]["A_discrimination"]["accuracy"] == 100

    if overall_pass and field_access_pass and discrimination_pass:
        print("\n✓ All success criteria met!")
        sys.exit(0)
    else:
        print("\n✗ Some success criteria not met")
        sys.exit(1)


if __name__ == "__main__":
    main()
