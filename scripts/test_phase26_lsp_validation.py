#!/usr/bin/env python
"""Validation suite for Phase 26 LSP navigation model.

Tests 25 queries across 5 categories:
1. Navigation discrimination (5) - picks goto_definition/find_references appropriately
2. Single goto_definition + field access (5)
3. Single find_references + field access (5)
4. Multi-step workflows (5)
5. Direct answers (5) - no tool calls

Targets:
- Overall: >=80% accuracy (20/25)
- Field access: >=80% of tool call queries access structured fields
- Tool discrimination: >=90% correct tool choice

Usage:
    uv run python scripts/test_phase26_lsp_validation.py <model_path>
"""

import json
import re
import sys
import time
from pathlib import Path

import mlx_lm

# Import format_prompt for consistency (Phase 26.1 lesson)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from punie.agent.prompt_utils import format_prompt


def run_inference(model, tokenizer, model_path: str, query: str) -> tuple[str, float]:
    """Run inference on a single query.

    Args:
        model: Loaded MLX model
        tokenizer: Loaded tokenizer
        model_path: Path to model (for prompt formatting)
        query: User query

    Returns:
        Tuple of (generated_text, generation_time)
    """
    prompt = format_prompt(query, model_path)

    start = time.time()
    response = mlx_lm.generate(
        model=model,
        tokenizer=tokenizer,
        prompt=prompt,
        max_tokens=512,
        verbose=False,
    )
    elapsed = time.time() - start

    return response, elapsed


def check_field_access(response: str) -> bool:
    """Check if response accesses structured fields.

    Args:
        response: Model response

    Returns:
        True if response accesses fields like .locations[0], .reference_count, etc.
    """
    field_patterns = [
        r"\.locations\[",
        r"\.locations\s*\[",
        r"\.references\s*\[",
        r"\.reference_count",
        r"\.error_count",
        r"\.success",
        r"for\s+\w+\s+in\s+result\.(locations|references|errors)",
    ]

    return any(re.search(pattern, response) for pattern in field_patterns)


def check_tool_call(response: str, expected_tool: str | None) -> bool:
    """Check if response calls the expected tool.

    Args:
        response: Model response
        expected_tool: Expected tool name (goto_definition, find_references, None for direct answer)

    Returns:
        True if tool call matches expectation
    """
    has_tool_call = "<tool_call>" in response

    if expected_tool is None:
        # Expect no tool call (direct answer)
        return not has_tool_call

    if not has_tool_call:
        # Expected tool call but didn't get one
        return False

    # Check if correct tool is called
    return expected_tool + "(" in response


# Test queries
QUERIES = [
    # Category 1: Navigation discrimination (5)
    {
        "query": "Where is the UserService class defined?",
        "category": "discrimination",
        "expected_tool": "goto_definition",
        "expect_field_access": True,
    },
    {
        "query": "Show me all places where parse_ty_output is used",
        "category": "discrimination",
        "expected_tool": "find_references",
        "expect_field_access": True,
    },
    {
        "query": "Find the definition of calculate_total method",
        "category": "discrimination",
        "expected_tool": "goto_definition",
        "expect_field_access": True,
    },
    {
        "query": "How many times is process_order called in the codebase?",
        "category": "discrimination",
        "expected_tool": "find_references",
        "expect_field_access": True,
    },
    {
        "query": "Where does BaseModel come from in typed_tools.py?",
        "category": "discrimination",
        "expected_tool": "goto_definition",
        "expect_field_access": True,
    },
    # Category 2: Single goto_definition + field access (5)
    {
        "query": "Find TypeCheckResult definition and show the file path",
        "category": "goto_def_fields",
        "expected_tool": "goto_definition",
        "expect_field_access": True,
    },
    {
        "query": "Is OLD_CONSTANT still defined in the config?",
        "category": "goto_def_fields",
        "expected_tool": "goto_definition",
        "expect_field_access": True,
    },
    {
        "query": "What file is process_order defined in?",
        "category": "goto_def_fields",
        "expected_tool": "goto_definition",
        "expect_field_access": True,
    },
    {
        "query": "Check if MissingClass is defined anywhere",
        "category": "goto_def_fields",
        "expected_tool": "goto_definition",
        "expect_field_access": True,
    },
    {
        "query": "Find where ValidationError exception is defined",
        "category": "goto_def_fields",
        "expected_tool": "goto_definition",
        "expect_field_access": True,
    },
    # Category 3: Single find_references + field access (5)
    {
        "query": "Count how many references to calculate_total exist",
        "category": "find_refs_fields",
        "expected_tool": "find_references",
        "expect_field_access": True,
    },
    {
        "query": "Which files reference TypeCheckResult?",
        "category": "find_refs_fields",
        "expected_tool": "find_references",
        "expect_field_access": True,
    },
    {
        "query": "Is unused_helper_function referenced anywhere?",
        "category": "find_refs_fields",
        "expected_tool": "find_references",
        "expect_field_access": True,
    },
    {
        "query": "List all references to DATABASE_URL",
        "category": "find_refs_fields",
        "expected_tool": "find_references",
        "expect_field_access": True,
    },
    {
        "query": "Show the first 3 places where UserService is used",
        "category": "find_refs_fields",
        "expected_tool": "find_references",
        "expect_field_access": True,
    },
    # Category 4: Multi-step workflows (5)
    {
        "query": "Find UserService definition and check its file for type errors",
        "category": "workflow",
        "expected_tool": "goto_definition",  # Should use both goto_definition and typecheck
        "expect_field_access": True,
    },
    {
        "query": "Find all files using parse_ty_output and check them for type errors",
        "category": "workflow",
        "expected_tool": "find_references",
        "expect_field_access": True,
    },
    {
        "query": "Check if old_helper_function is defined but unused",
        "category": "workflow",
        "expected_tool": "goto_definition",  # Uses both goto_definition and find_references
        "expect_field_access": True,
    },
    {
        "query": "Find TypeCheckResult definition and read its implementation",
        "category": "workflow",
        "expected_tool": "goto_definition",
        "expect_field_access": True,
    },
    {
        "query": "Before renaming UserService, check where it's used",
        "category": "workflow",
        "expected_tool": "find_references",
        "expect_field_access": True,
    },
    # Category 5: Direct answers (5) - no tool calls
    {
        "query": "What is the Language Server Protocol?",
        "category": "direct",
        "expected_tool": None,
        "expect_field_access": False,
    },
    {
        "query": "When should I use goto_definition instead of grep?",
        "category": "direct",
        "expected_tool": None,
        "expect_field_access": False,
    },
    {
        "query": "Why does LSP use 0-based line numbers?",
        "category": "direct",
        "expected_tool": None,
        "expect_field_access": False,
    },
    {
        "query": "What's the advantage of typed tools over raw text output?",
        "category": "direct",
        "expected_tool": None,
        "expect_field_access": False,
    },
    {
        "query": "What LSP features does Phase 26 support?",
        "category": "direct",
        "expected_tool": None,
        "expect_field_access": False,
    },
]


def main():
    """Run validation suite."""
    if len(sys.argv) != 2:
        print("Usage: python test_phase26_lsp_validation.py <model_path>")
        sys.exit(1)

    model_path = sys.argv[1]
    print(f"Testing model: {model_path}")
    print(f"Total queries: {len(QUERIES)}")
    print("=" * 80)

    # Load model once
    print("\nLoading model...")
    model, tokenizer = mlx_lm.load(model_path)
    print("Model loaded!\n")

    results = {
        "overall": {"correct": 0, "total": len(QUERIES)},
        "field_access": {"correct": 0, "total": 0},  # Only count tool call queries
        "tool_discrimination": {"correct": 0, "total": len(QUERIES)},
        "by_category": {},
        "generation_times": [],
        "responses": [],  # Save all responses for debugging
    }

    for i, test in enumerate(QUERIES, 1):
        query = test["query"]
        category = test["category"]
        expected_tool = test["expected_tool"]
        expect_field_access = test["expect_field_access"]

        print(f"\n[{i}/{len(QUERIES)}] {category}: {query[:60]}...")

        # Run inference
        response, gen_time = run_inference(model, tokenizer, model_path, query)
        results["generation_times"].append(gen_time)

        # Check tool discrimination
        tool_correct = check_tool_call(response, expected_tool)
        if tool_correct:
            results["tool_discrimination"]["correct"] += 1

        # Check field access (only for tool call queries)
        field_access_correct = False
        if expected_tool is not None:  # Tool call expected
            results["field_access"]["total"] += 1
            has_field_access = check_field_access(response)
            field_access_correct = has_field_access if expect_field_access else not has_field_access
            if field_access_correct:
                results["field_access"]["correct"] += 1

        # Overall correctness (tool + field access for tool calls, just tool for direct)
        overall_correct = tool_correct and (field_access_correct if expected_tool else True)
        if overall_correct:
            results["overall"]["correct"] += 1

        # Track by category
        if category not in results["by_category"]:
            results["by_category"][category] = {"correct": 0, "total": 0}
        results["by_category"][category]["total"] += 1
        if overall_correct:
            results["by_category"][category]["correct"] += 1

        # Save response for debugging
        results["responses"].append({
            "query": query,
            "category": category,
            "expected_tool": expected_tool,
            "response": response,
            "tool_correct": tool_correct,
            "field_access_correct": field_access_correct if expected_tool else None,
            "overall_correct": overall_correct,
            "generation_time": gen_time,
        })

        # Print status
        status = "✓" if overall_correct else "✗"
        tool_status = "✓" if tool_correct else "✗"
        field_status = "✓" if field_access_correct else "✗" if expected_tool else "N/A"
        print(f"  {status} Overall | {tool_status} Tool | {field_status} Fields | {gen_time:.2f}s")

    # Print summary
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    overall_pct = results["overall"]["correct"] / results["overall"]["total"] * 100
    print(f"\nOverall: {results['overall']['correct']}/{results['overall']['total']} ({overall_pct:.1f}%)")

    tool_pct = results["tool_discrimination"]["correct"] / results["tool_discrimination"]["total"] * 100
    print(f"Tool discrimination: {results['tool_discrimination']['correct']}/{results['tool_discrimination']['total']} ({tool_pct:.1f}%)")

    if results["field_access"]["total"] > 0:
        field_pct = results["field_access"]["correct"] / results["field_access"]["total"] * 100
        print(f"Field access: {results['field_access']['correct']}/{results['field_access']['total']} ({field_pct:.1f}%)")

    print("\nBy category:")
    for cat, data in sorted(results["by_category"].items()):
        pct = data["correct"] / data["total"] * 100
        print(f"  {cat}: {data['correct']}/{data['total']} ({pct:.1f}%)")

    avg_time = sum(results["generation_times"]) / len(results["generation_times"])
    print(f"\nAvg generation time: {avg_time:.2f}s")

    # Check if targets met
    print("\n" + "=" * 80)
    print("TARGETS")
    print("=" * 80)
    overall_target = overall_pct >= 80
    tool_target = tool_pct >= 90
    field_target = field_pct >= 80 if results["field_access"]["total"] > 0 else True

    print(f"Overall >=80%: {'✓ PASS' if overall_target else '✗ FAIL'} ({overall_pct:.1f}%)")
    print(f"Tool discrimination >=90%: {'✓ PASS' if tool_target else '✗ FAIL'} ({tool_pct:.1f}%)")
    if results["field_access"]["total"] > 0:
        print(f"Field access >=80%: {'✓ PASS' if field_target else '✗ FAIL'} ({field_pct:.1f}%)")

    all_pass = overall_target and tool_target and field_target
    print(f"\n{'✓ ALL TARGETS MET' if all_pass else '✗ TARGETS NOT MET'}")

    # Save results
    output_file = Path("logs") / f"phase26_lsp_validation_{Path(model_path).name}.json"
    output_file.parent.mkdir(exist_ok=True)
    with output_file.open("w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_file}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
