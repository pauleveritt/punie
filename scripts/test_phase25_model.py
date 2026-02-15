#!/usr/bin/env python3
"""Test Phase 25b 7B model with 20-query suite and comparison to 30B.

Usage:
  python scripts/test_phase25_model.py fused_model_qwen25_phase25b_7b_6bit
  python scripts/test_phase25_model.py fused_model_qwen25_phase25b_7b_6bit --compare
"""

import argparse
import json
import sys
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import generate, load

# Import shared prompt formatting utility
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from punie.agent.prompt_utils import format_prompt as format_prompt_util


# 20-query test suite (13 tool + 7 direct)
TEST_QUERIES = [
    # Tool queries - typecheck (3)
    {
        "query": "Run type checking on src/punie/agent/typed_tools.py",
        "expected": "tool",
        "tool": "typecheck",
        "description": "Typecheck query - should use typecheck()",
    },
    {
        "query": "Check types in the entire src/ directory",
        "expected": "tool",
        "tool": "typecheck",
        "description": "Typecheck query - should use typecheck()",
    },
    {
        "query": "Are there any type errors in tests/?",
        "expected": "tool",
        "tool": "typecheck",
        "description": "Typecheck query - should use typecheck()",
    },
    # Tool queries - ruff_check (3)
    {
        "query": "Check code quality in src/punie/agent/",
        "expected": "tool",
        "tool": "ruff_check",
        "description": "Ruff query - should use ruff_check()",
    },
    {
        "query": "Run linter on the codebase",
        "expected": "tool",
        "tool": "ruff_check",
        "description": "Ruff query - should use ruff_check()",
    },
    {
        "query": "Are there any style violations in scripts/?",
        "expected": "tool",
        "tool": "ruff_check",
        "description": "Ruff query - should use ruff_check()",
    },
    # Tool queries - pytest_run (3)
    {
        "query": "Run tests in tests/test_config.py",
        "expected": "tool",
        "tool": "pytest_run",
        "description": "Pytest query - should use pytest_run()",
    },
    {
        "query": "Execute the full test suite",
        "expected": "tool",
        "tool": "pytest_run",
        "description": "Pytest query - should use pytest_run()",
    },
    {
        "query": "Are all tests passing?",
        "expected": "tool",
        "tool": "pytest_run",
        "description": "Pytest query - should use pytest_run()",
    },
    # Tool queries - read/search (4)
    {
        "query": "Show me the implementation of AgentConfig",
        "expected": "tool",
        "tool": "read_file",
        "description": "Read query - should use read_file()",
    },
    {
        "query": "Find all uses of PydanticAI in the codebase",
        "expected": "tool",
        "tool": "run_command",
        "description": "Search query - should use run_command(grep)",
    },
    {
        "query": "What's in the README.md file?",
        "expected": "tool",
        "tool": "read_file",
        "description": "Read query - should use read_file()",
    },
    {
        "query": "Find all Python files in src/punie/",
        "expected": "tool",
        "tool": "run_command",
        "description": "Search query - should use run_command(find)",
    },
    # Direct answers - concepts (3)
    {
        "query": "What is Code Mode in Punie?",
        "expected": "direct",
        "tool": None,
        "description": "Concept question - should answer directly",
    },
    {
        "query": "Explain how typed tools work",
        "expected": "direct",
        "tool": None,
        "description": "Concept question - should answer directly",
    },
    {
        "query": "What is the Agent Communication Protocol?",
        "expected": "direct",
        "tool": None,
        "description": "Concept question - should answer directly",
    },
    # Direct answers - comparisons (2)
    {
        "query": "What's the difference between typecheck and ruff_check?",
        "expected": "direct",
        "tool": None,
        "description": "Comparison question - should answer directly",
    },
    {
        "query": "When should I use pytest_run vs running tests manually?",
        "expected": "direct",
        "tool": None,
        "description": "Comparison question - should answer directly",
    },
    # Direct answers - best practices (2)
    {
        "query": "What are best practices for using Pydantic models?",
        "expected": "direct",
        "tool": None,
        "description": "Best practice question - should answer directly",
    },
    {
        "query": "How should I structure my training data?",
        "expected": "direct",
        "tool": None,
        "description": "Best practice question - should answer directly",
    },
]


def format_prompt(query: str, model_path: str) -> str:
    """Format query in chat template with tool definitions.

    Uses shared utility to guarantee consistency with training format.
    """
    system_prompt = """You are Punie, an AI coding assistant that helps with Python development via PyCharm.

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{"type": "function", "function": {"name": "execute_code", "description": "Execute Python code. Available functions: read_file(path), write_file(path, content), run_command(command), typecheck(path), ruff_check(path), pytest_run(path). Use print() to show output.", "parameters": {"type": "object", "properties": {"code": {"type": "string", "description": "Python code to execute"}}, "required": ["code"]}}}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>"""

    # Use shared utility with custom system message
    return format_prompt_util(query, model_path, system_message=system_prompt)


def is_code_mode_response(response: str) -> bool:
    """Check if response uses Code Mode (execute_code)."""
    return "```python" in response and "execute_code" in response


def is_xml_tool_response(response: str) -> bool:
    """Check if response uses XML tool format (legacy)."""
    return "<tool_call>" in response and "<function=" in response


def is_json_tool_call(response: str) -> bool:
    """Check if response uses Qwen2.5 JSON tool format."""
    return "<tool_call>" in response and '"name"' in response and '"execute_code"' in response


def get_disk_size(path: Path) -> float:
    """Get total disk size in GB."""
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / 1024**3


def test_model(model_path: str, verbose: bool = True) -> dict:
    """Test a single model and return results."""
    path = Path(model_path)

    if not path.exists():
        print(f"❌ Model not found at {model_path}")
        sys.exit(1)

    if verbose:
        print("=" * 80)
        print(f"TESTING: {model_path}")
        print("=" * 80)

    # Get disk size
    disk_size = get_disk_size(path)
    if verbose:
        print(f"Disk size: {disk_size:.2f} GB")

    # Load model
    if verbose:
        print("Loading model...")
    start = time.time()
    result = load(model_path)
    model, tokenizer = result[0], result[1]
    load_time = time.time() - start
    if verbose:
        print(f"✓ Loaded in {load_time:.2f}s")

    # Get memory usage
    memory_gb = mx.metal.get_active_memory() / 1024**3
    if verbose:
        print(f"  Runtime memory: {memory_gb:.2f} GB")

    # Run test queries
    if verbose:
        print("\nRunning 20-query test suite...")
    results = []
    total_gen_time = 0

    for i, test in enumerate(TEST_QUERIES, 1):
        if verbose:
            print(f"\n[{i}/20] {test['description']}")
            print(f"  Query: {test['query']}")

        # Use shared utility to guarantee consistency with training format
        prompt = format_prompt(test["query"], model_path)

        # Generate response
        start = time.time()
        response_text = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=512,
            verbose=False,
        )
        gen_time = time.time() - start
        total_gen_time += gen_time

        # Check response type
        is_code_mode = is_code_mode_response(response_text)
        is_xml_tool = is_xml_tool_response(response_text)
        is_json_tool = is_json_tool_call(response_text)
        used_tool = is_code_mode or is_xml_tool or is_json_tool

        expected_tool = test["expected"] == "tool"
        correct = used_tool == expected_tool

        if verbose:
            status = "✓" if correct else "✗"
            if is_json_tool:
                format_type = "json"
            elif is_code_mode:
                format_type = "code"
            elif is_xml_tool:
                format_type = "xml"
            else:
                format_type = "direct"
            print(f"  Expected: {test['expected']}, Got: {'tool' if used_tool else 'direct'} ({format_type}) {status}")
            print(f"  Time: {gen_time:.2f}s")

        results.append({
            "query": test["query"],
            "expected": test["expected"],
            "expected_tool": test["tool"],
            "got": "tool" if used_tool else "direct",
            "format": "json" if is_json_tool else ("code" if is_code_mode else ("xml" if is_xml_tool else "direct")),
            "correct": correct,
            "time": gen_time,
        })

    # Calculate metrics
    accuracy = sum(1 for r in results if r["correct"]) / len(results) * 100
    avg_gen_time = total_gen_time / len(results)
    json_mode_count = sum(1 for r in results if r["format"] == "json")
    json_mode_pct = json_mode_count / len([r for r in results if r["got"] == "tool"]) * 100 if any(r["got"] == "tool" for r in results) else 0

    if verbose:
        print(f"\n{'='*80}")
        print("RESULTS:")
        print(f"  Disk size: {disk_size:.2f} GB")
        print(f"  Runtime memory: {memory_gb:.2f} GB")
        print(f"  Load time: {load_time:.2f}s")
        print(f"  Avg generation time: {avg_gen_time:.2f}s")
        print(f"  Accuracy: {accuracy:.1f}% ({sum(1 for r in results if r['correct'])}/{len(results)})")
        print(f"  JSON format usage: {json_mode_pct:.1f}% ({json_mode_count} tool queries)")
        print("=" * 80)

    return {
        "model": model_path,
        "disk_size_gb": disk_size,
        "load_time": load_time,
        "memory_gb": memory_gb,
        "avg_gen_time": avg_gen_time,
        "accuracy": accuracy,
        "json_mode_pct": json_mode_pct,
        "results": results,
    }


def compare_models(model_7b: str, model_30b: str):
    """Compare 7B and 30B models side-by-side."""
    print("=" * 80)
    print("PHASE 25: 7B vs 30B COMPARISON")
    print("=" * 80)
    print()

    # Test 7B
    print("Testing 7B model...")
    results_7b = test_model(model_7b, verbose=True)
    print()

    # Clear memory
    mx.metal.clear_cache()

    # Test 30B
    print("\nTesting 30B model...")
    results_30b = test_model(model_30b, verbose=True)
    print()

    # Comparison table
    print("=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Metric':<25} {'7B':<20} {'30B':<20} {'Improvement':<15}")
    print("-" * 80)

    # Disk size
    size_7b = results_7b["disk_size_gb"]
    size_30b = results_30b["disk_size_gb"]
    size_improvement = (size_30b - size_7b) / size_30b * 100
    print(f"{'Disk size (GB)':<25} {size_7b:<20.2f} {size_30b:<20.2f} {size_improvement:>6.1f}%")

    # Memory
    mem_7b = results_7b["memory_gb"]
    mem_30b = results_30b["memory_gb"]
    mem_improvement = (mem_30b - mem_7b) / mem_30b * 100
    print(f"{'Runtime memory (GB)':<25} {mem_7b:<20.2f} {mem_30b:<20.2f} {mem_improvement:>6.1f}%")

    # Speed
    speed_7b = results_7b["avg_gen_time"]
    speed_30b = results_30b["avg_gen_time"]
    speed_multiplier = speed_30b / speed_7b
    print(f"{'Avg gen time (s)':<25} {speed_7b:<20.2f} {speed_30b:<20.2f} {speed_multiplier:>6.1f}x faster")

    # Accuracy
    acc_7b = results_7b["accuracy"]
    acc_30b = results_30b["accuracy"]
    acc_ratio = acc_7b / acc_30b * 100
    print(f"{'Accuracy (%)':<25} {acc_7b:<20.1f} {acc_30b:<20.1f} {acc_ratio:>6.1f}% of 30B")

    # JSON format
    json_7b = results_7b.get("json_mode_pct", 0)
    json_30b = results_30b.get("json_mode_pct", 0)
    print(f"{'JSON format usage (%)':<25} {json_7b:<20.1f} {json_30b:<20.1f}")

    print("=" * 80)
    print()

    # Decision
    print("DECISION CRITERIA:")
    if acc_ratio >= 90:
        print(f"✅ 7B achieves {acc_ratio:.1f}% of 30B accuracy (>=90% threshold)")
        print(f"✅ {speed_multiplier:.1f}x faster with {size_improvement:.0f}% less disk space")
        print("🎯 RECOMMENDATION: Use 7B as primary model")
    elif acc_ratio >= 70:
        print(f"⚠️  7B achieves {acc_ratio:.1f}% of 30B accuracy (70-90% range)")
        print("🎯 RECOMMENDATION: Split by use case (7B for simple, 30B for complex)")
    else:
        print(f"❌ 7B achieves {acc_ratio:.1f}% of 30B accuracy (<70% threshold)")
        print("🎯 RECOMMENDATION: Stick with 30B")

    print("=" * 80)

    # Save comparison
    output_dir = Path("logs")
    output_dir.mkdir(exist_ok=True)
    comparison_file = output_dir / "phase25b_comparison.json"

    with comparison_file.open("w") as f:
        json.dump(
            {
                "7b": results_7b,
                "30b": results_30b,
                "comparison": {
                    "size_improvement_pct": size_improvement,
                    "memory_improvement_pct": mem_improvement,
                    "speed_multiplier": speed_multiplier,
                    "accuracy_ratio_pct": acc_ratio,
                },
            },
            f,
            indent=2,
        )

    print(f"\n✅ Comparison saved to {comparison_file}")


def main():
    parser = argparse.ArgumentParser(description="Test Phase 25b 7B model")
    parser.add_argument("model", nargs="?", default="fused_model_qwen25_phase25b_7b_6bit",
                        help="Model path to test")
    parser.add_argument("--compare", action="store_true",
                        help="Compare 7B vs 30B models")
    args = parser.parse_args()

    if args.compare:
        # Compare mode
        model_7b = "fused_model_qwen25_phase25b_7b_6bit"
        model_30b = "fused_model_qwen3_phase23_ty_5bit"

        if not Path(model_7b).exists():
            print(f"❌ 7B model not found at {model_7b}")
            print("Run ./scripts/run_phase25.sh first")
            sys.exit(1)

        if not Path(model_30b).exists():
            print(f"❌ 30B model not found at {model_30b}")
            print("This is the Phase 23 baseline model")
            sys.exit(1)

        compare_models(model_7b, model_30b)
    else:
        # Single model test
        results = test_model(args.model, verbose=True)

        # Save results
        output_dir = Path("logs")
        output_dir.mkdir(exist_ok=True)

        model_name = Path(args.model).name
        output_file = output_dir / f"{model_name}_results.json"

        with output_file.open("w") as f:
            json.dump(results, f, indent=2)

        print(f"\n✅ Results saved to {output_file}")


if __name__ == "__main__":
    main()
