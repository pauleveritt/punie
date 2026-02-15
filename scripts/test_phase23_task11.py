#!/usr/bin/env python3
"""
Task 11: Phase 23 End-to-End Validation Test
Automated 15-query test suite for typed tools validation.
"""

import json
import sys
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import generate, load

# Import shared prompt formatting utility
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from punie.agent.prompt_utils import format_prompt


# Test queries organized by category
TEST_QUERIES = {
    "A. Single-Tool Discrimination": [
        {
            "query": "Check types in src/punie/agent/",
            "expected": "tool",
            "should_access_fields": False,
            "description": "Should call typecheck()",
        },
        {
            "query": "What type errors are in config.py?",
            "expected": "tool",
            "should_access_fields": False,
            "description": "Should call typecheck() on config.py",
        },
        {
            "query": "What is a Protocol in Python typing?",
            "expected": "direct",
            "should_access_fields": False,
            "description": "Direct answer, no tool call",
        },
        {
            "query": "Show me the TypeCheckResult model",
            "expected": "tool",
            "should_access_fields": False,
            "description": "Should call read_file()",
        },
        {
            "query": "What's the difference between TypeCheckResult and TypeCheckError?",
            "expected": "direct",
            "should_access_fields": False,
            "description": "Direct answer from training data",
        },
    ],
    "B. Multi-Step Workflows": [
        {
            "query": "Check types in stubs.py and list each error with its line number",
            "expected": "tool",
            "should_access_fields": True,
            "description": "Should access result.errors",
        },
        {
            "query": "Check types in both stubs.py and typed_tools.py",
            "expected": "tool",
            "should_access_fields": False,
            "description": "Should make two typecheck() calls",
        },
        {
            "query": "If there are any type errors in config.py, show me the first one",
            "expected": "tool",
            "should_access_fields": True,
            "description": "Should use result.error_count, result.errors[0]",
        },
        {
            "query": "Check types in factory.py and count how many errors there are",
            "expected": "tool",
            "should_access_fields": True,
            "description": "Should access result.error_count",
        },
        {
            "query": "Are there any type errors in toolset.py? If yes, how many?",
            "expected": "tool",
            "should_access_fields": True,
            "description": "Conditional logic based on result fields",
        },
    ],
    "C. Phase 22 Regression": [
        {
            "query": "Read the README.md file",
            "expected": "tool",
            "should_access_fields": False,
            "description": "Should call read_file()",
        },
        {
            "query": "Find all Python files in src/punie/",
            "expected": "tool",
            "should_access_fields": False,
            "description": "Should call run_command()",
        },
        {
            "query": "What is dependency injection?",
            "expected": "direct",
            "should_access_fields": False,
            "description": "Direct answer",
        },
        {
            "query": "Show me the AgentConfig class",
            "expected": "tool",
            "should_access_fields": False,
            "description": "Should call read_file() or grep",
        },
        {
            "query": "Explain the difference between unittest and pytest",
            "expected": "direct",
            "should_access_fields": False,
            "description": "Direct answer",
        },
    ],
}


def is_tool_call(response: str) -> bool:
    """Check if response contains a tool call."""
    return "<tool_call>" in response or "execute_code" in response


def accesses_structured_fields(response: str) -> bool:
    """Check if response accesses TypeCheckResult fields."""
    field_patterns = [
        "result.errors",
        "result.error_count",
        "result.success",
        ".errors[",
        ".error_count",
    ]
    return any(pattern in response for pattern in field_patterns)


def run_test_suite(model, tokenizer, model_path: str):
    """Run all 15 test queries and collect results."""
    results = {}
    query_num = 0

    for category, queries in TEST_QUERIES.items():
        print(f"\n{'='*80}")
        print(f"{category}")
        print('='*80)

        category_results = []

        for test in queries:
            query_num += 1
            print(f"\n[{query_num}/15] {test['description']}")
            print(f"  Query: {test['query']}")

            # Use shared utility to guarantee consistency with training format
            prompt = format_prompt(test["query"], model_path)

            # Generate response
            start = time.time()
            response = generate(
                model,
                tokenizer,
                prompt=prompt,
                max_tokens=512,
                verbose=False,
            )
            gen_time = time.time() - start

            # Analyze response
            has_tool = is_tool_call(response)
            has_fields = accesses_structured_fields(response)

            expected_tool = test["expected"] == "tool"
            correct = has_tool == expected_tool

            # For multi-step queries, check field access
            if test["should_access_fields"]:
                fields_correct = has_fields
            else:
                fields_correct = True  # N/A for this query

            status = "✓" if (correct and fields_correct) else "✗"

            print(f"  Expected: {test['expected']}, Got: {'tool' if has_tool else 'direct'} {status}")
            print(f"  Time: {gen_time:.2f}s")

            if test["should_access_fields"]:
                field_status = "✓" if has_fields else "✗"
                print(f"  Structured fields: {'accessed' if has_fields else 'NOT accessed'} {field_status}")

            category_results.append({
                "query": test["query"],
                "expected": test["expected"],
                "got": "tool" if has_tool else "direct",
                "correct": correct,
                "should_access_fields": test["should_access_fields"],
                "fields_accessed": has_fields,
                "fields_correct": fields_correct,
                "time": gen_time,
                "response_preview": response[:200],
            })

        results[category] = category_results

    return results


def calculate_metrics(results):
    """Calculate pass/fail metrics."""
    metrics = {}

    for category, queries in results.items():
        total = len(queries)
        correct = sum(1 for q in queries if q["correct"] and q["fields_correct"])
        accuracy = (correct / total * 100) if total > 0 else 0

        # Count field access for multi-step queries
        field_queries = [q for q in queries if q["should_access_fields"]]
        if field_queries:
            field_correct = sum(1 for q in field_queries if q["fields_accessed"])
            field_accuracy = (field_correct / len(field_queries) * 100)
        else:
            field_accuracy = None

        metrics[category] = {
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "field_queries": len(field_queries),
            "field_correct": len([q for q in field_queries if q["fields_accessed"]]) if field_queries else 0,
            "field_accuracy": field_accuracy,
        }

    return metrics


def print_summary(metrics):
    """Print test summary."""
    print("\n" + "="*80)
    print("TASK 11 VALIDATION SUMMARY")
    print("="*80)

    total_queries = 0
    total_correct = 0

    for category, stats in metrics.items():
        total_queries += stats["total"]
        total_correct += stats["correct"]

        print(f"\n{category}:")
        print(f"  Accuracy: {stats['accuracy']:.1f}% ({stats['correct']}/{stats['total']})")

        if stats["field_accuracy"] is not None:
            print(f"  Structured field access: {stats['field_accuracy']:.1f}% ({stats['field_correct']}/{stats['field_queries']})")

    overall_accuracy = (total_correct / total_queries * 100) if total_queries > 0 else 0

    print(f"\n{'='*80}")
    print(f"OVERALL: {overall_accuracy:.1f}% ({total_correct}/{total_queries})")
    print("="*80)

    # Success thresholds from checklist
    print("\nSuccess Criteria:")
    print(f"  A. Single-tool discrimination: {metrics['A. Single-Tool Discrimination']['accuracy']:.1f}% (target: 100%, min: 80%)")
    print(f"  B. Multi-step workflows: {metrics['B. Multi-Step Workflows']['accuracy']:.1f}% (target: 80%, min: 60%)")
    print(f"  C. Phase 22 regression: {metrics['C. Phase 22 Regression']['accuracy']:.1f}% (target: 100%, min: 100%)")

    # Field access for multi-step
    if metrics['B. Multi-Step Workflows']['field_accuracy'] is not None:
        print(f"  Structured field access: {metrics['B. Multi-Step Workflows']['field_accuracy']:.1f}% (critical for typed tools)")

    # Overall verdict
    print("\nVerdict:")
    a_pass = metrics['A. Single-Tool Discrimination']['accuracy'] >= 80
    b_pass = metrics['B. Multi-Step Workflows']['accuracy'] >= 60
    c_pass = metrics['C. Phase 22 Regression']['accuracy'] >= 100
    field_pass = metrics['B. Multi-Step Workflows']['field_accuracy'] >= 60 if metrics['B. Multi-Step Workflows']['field_accuracy'] is not None else True

    if a_pass and b_pass and c_pass and field_pass:
        print("✅ PASS - Phase 23 typed tools validated!")
    else:
        print("❌ FAIL - Issues detected:")
        if not a_pass:
            print("  - Single-tool discrimination below threshold")
        if not b_pass:
            print("  - Multi-step workflows below threshold")
        if not c_pass:
            print("  - Phase 22 regression detected")
        if not field_pass:
            print("  - Model not accessing structured fields (critical gap)")


def main():
    model_path = "fused_model_qwen3_phase23_ty_5bit"

    print("="*80)
    print("Task 11: Phase 23 End-to-End Validation")
    print("="*80)
    print(f"Model: {model_path}")
    print("Queries: 15 (5 per category)")
    print()

    # Load model
    print("Loading model...")
    start = time.time()
    model, tokenizer = load(model_path)
    load_time = time.time() - start
    print(f"✓ Loaded in {load_time:.2f}s")

    memory_gb = mx.metal.get_active_memory() / 1024**3
    print(f"  Memory: {memory_gb:.2f} GB")

    # Run tests
    results = run_test_suite(model, tokenizer, model_path)

    # Calculate metrics
    metrics = calculate_metrics(results)

    # Print summary
    print_summary(metrics)

    # Save results
    output_dir = Path("logs")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "phase23_task11_results.json"

    with output_file.open("w") as f:
        json.dump({
            "metrics": metrics,
            "results": results,
            "load_time": load_time,
            "memory_gb": memory_gb,
        }, f, indent=2)

    print(f"\n✅ Results saved to {output_file}")


if __name__ == "__main__":
    main()
