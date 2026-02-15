#!/usr/bin/env python3
"""Test a single quantized model for accuracy.

Usage:
  python scripts/test_single_model.py fused_model_qwen3_phase8_8bit
  python scripts/test_single_model.py fused_model_qwen3_phase8_6bit
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


# Test queries (3 tool, 2 direct)
TEST_QUERIES = [
    {
        "query": "Find all Django view functions",
        "expected": "tool",
        "description": "Search query - should use run_command",
    },
    {
        "query": "Show me the implementation of UserSerializer",
        "expected": "tool",
        "description": "Read query - should use read_file",
    },
    {
        "query": "What is dependency injection in Django?",
        "expected": "direct",
        "description": "Concept question - should answer directly",
    },
    {
        "query": "Find all uses of async/await in the codebase",
        "expected": "tool",
        "description": "Search query - should use run_command",
    },
    {
        "query": "What's the difference between Django ORM and raw SQL?",
        "expected": "direct",
        "description": "Comparison question - should answer directly",
    },
]


def is_tool_response(response: str) -> bool:
    """Check if response contains a tool call (XML format)."""
    return "<tool_call>" in response and "<function=" in response


def get_disk_size(path: Path) -> float:
    """Get total disk size in GB."""
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / 1024**3


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/test_single_model.py <model_path>")
        print("Example: python scripts/test_single_model.py fused_model_qwen3_phase8_6bit")
        sys.exit(1)

    model_path = sys.argv[1]
    path = Path(model_path)

    if not path.exists():
        print(f"❌ Model not found at {model_path}")
        sys.exit(1)

    print("="*80)
    print(f"TESTING: {model_path}")
    print("="*80)

    # Get disk size
    disk_size = get_disk_size(path)
    print(f"Disk size: {disk_size:.2f} GB")

    # Load model
    print("Loading model...")
    start = time.time()
    result = load(model_path)
    model, tokenizer = result[0], result[1]
    load_time = time.time() - start
    print(f"✓ Loaded in {load_time:.2f}s")

    # Get memory usage
    memory_gb = mx.metal.get_active_memory() / 1024**3
    print(f"  Runtime memory: {memory_gb:.2f} GB")

    # Run test queries
    print("\nRunning test queries...")
    results = []
    total_gen_time = 0

    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/5] {test['description']}")
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

        # Check if tool was used
        used_tool = is_tool_response(response_text)
        expected_tool = test["expected"] == "tool"
        correct = used_tool == expected_tool

        status = "✓" if correct else "✗"
        print(f"  Expected: {test['expected']}, Got: {'tool' if used_tool else 'direct'} {status}")
        print(f"  Time: {gen_time:.2f}s")

        results.append({
            "query": test["query"],
            "expected": test["expected"],
            "got": "tool" if used_tool else "direct",
            "correct": correct,
            "time": gen_time,
        })

    # Calculate metrics
    accuracy = sum(1 for r in results if r["correct"]) / len(results) * 100
    avg_gen_time = total_gen_time / len(results)

    print(f"\n{'='*80}")
    print("RESULTS:")
    print(f"  Disk size: {disk_size:.2f} GB")
    print(f"  Runtime memory: {memory_gb:.2f} GB")
    print(f"  Load time: {load_time:.2f}s")
    print(f"  Avg generation time: {avg_gen_time:.2f}s")
    print(f"  Accuracy: {accuracy:.1f}% ({sum(1 for r in results if r['correct'])}/{len(results)})")
    print('='*80)

    # Save results
    output_dir = Path("logs")
    output_dir.mkdir(exist_ok=True)

    model_name = path.name
    output_file = output_dir / f"{model_name}_results.json"

    with output_file.open("w") as f:
        json.dump({
            "model": model_path,
            "disk_size_gb": disk_size,
            "load_time": load_time,
            "memory_gb": memory_gb,
            "avg_gen_time": avg_gen_time,
            "accuracy": accuracy,
            "results": results,
        }, f, indent=2)

    print(f"\n✅ Results saved to {output_file}")


if __name__ == "__main__":
    main()
