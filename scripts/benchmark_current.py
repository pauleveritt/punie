#!/usr/bin/env python3
"""Benchmark current production model (Phase 27).

Measures:
- Disk size (GB)
- Runtime memory (GB)
- Load time (seconds)
- Generation time per query (seconds)
- Accuracy (discrimination: tool vs direct answers)

Query: "Show me how the protocol class is used in the codebase"
Expected: Should call a tool (grep/search)
"""

import json
import sys
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import generate, load

# Import shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from punie.agent.prompt_utils import format_prompt, is_tool_response


# Single protocol usage query
TEST_QUERY = {
    "query": "Show me how the protocol class is used in the codebase",
    "expected": "tool",
    "description": "Protocol usage search - should use tool",
}


def get_disk_size(path: Path) -> float:
    """Get total disk size of a directory in GB."""
    if not path.exists():
        return 0.0
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / 1024**3


def benchmark_model(model_path: str, model_name: str) -> dict:
    """Benchmark a single model."""
    print(f"\n{'='*80}")
    print(f"Benchmarking: {model_name}")
    print(f"Path: {model_path}")
    print('='*80)

    # Get disk size
    path = Path(model_path) if "/" in model_path else None
    disk_size = get_disk_size(path) if path else 0.0

    if disk_size > 0:
        print(f"Disk size: {disk_size:.2f} GB")
    else:
        print("Disk size: N/A (cached model)")

    # Load model
    print("Loading model...")
    start = time.time()
    try:
        result = load(model_path)
        model, tokenizer = result[0], result[1]
    except Exception as e:
        return {
            "model": model_name,
            "path": model_path,
            "error": f"Load failed: {e}",
        }

    load_time = time.time() - start
    print(f"✓ Loaded in {load_time:.2f}s")

    # Get memory usage
    memory_gb = mx.metal.get_active_memory() / 1024**3
    print(f"  Runtime memory: {memory_gb:.2f} GB")

    # Run warm-up query
    print("\nRunning warm-up query...")
    print(f"  Query: {TEST_QUERY['query']}")

    prompt = format_prompt(TEST_QUERY["query"], model_path)

    start = time.time()
    try:
        warmup_response = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=512,
            verbose=False,
        )
    except Exception as e:
        return {
            "model": model_name,
            "path": model_path,
            "error": f"Generation failed: {e}",
        }

    warmup_time = time.time() - start
    warmup_is_tool = is_tool_response(warmup_response)
    warmup_correct = warmup_is_tool == (TEST_QUERY["expected"] == "tool")

    print(f"  Expected: {TEST_QUERY['expected']}, Got: {'tool' if warmup_is_tool else 'direct'}")
    print(f"  Warm-up time: {warmup_time:.2f}s")

    # Run steady-state queries (3x)
    print("\nRunning steady-state queries (3x)...")
    times = []
    correct = 0

    for i in range(3):
        start = time.time()
        response = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=512,
            verbose=False,
        )
        elapsed = time.time() - start

        is_tool = is_tool_response(response)
        is_correct = is_tool == (TEST_QUERY["expected"] == "tool")

        times.append(elapsed)
        if is_correct:
            correct += 1

        status = "✓" if is_correct else "✗"
        print(f"  Query {i+1}: {elapsed:.2f}s {status}")

    avg_time = sum(times) / len(times)
    accuracy = 100 * (correct / len(times))

    # Calculate overall accuracy (including warm-up)
    total_correct = correct + (1 if warmup_correct else 0)
    total_queries = len(times) + 1
    overall_accuracy = 100 * (total_correct / total_queries)

    print(f"\n{'='*80}")
    print("Results:")
    print(f"  Accuracy: {overall_accuracy:.0f}% ({total_correct}/{total_queries} correct)")
    print(f"  Warm-up time: {warmup_time:.2f}s")
    print(f"  Steady-state avg: {avg_time:.2f}s")
    print('='*80)

    return {
        "model": model_name,
        "path": model_path,
        "disk_size_gb": disk_size if disk_size > 0 else None,
        "memory_gb": memory_gb,
        "load_time_s": load_time,
        "warmup_time_s": warmup_time,
        "steady_state_avg_s": avg_time,
        "steady_state_times_s": times,
        "accuracy_percent": overall_accuracy,
        "warmup_correct": warmup_correct,
        "steady_state_correct": correct,
        "total_correct": total_correct,
        "total_queries": total_queries,
    }


def main():
    """Run benchmark on Phase 27 model."""
    model_path = "fused_model_qwen3_phase27_cleaned_5bit"
    model_name = "Phase 27 (Current production)"

    print("Current Production Model Benchmark")
    print("="*80)
    print(f"Query: '{TEST_QUERY['query']}'")
    print(f"Expected: Should call a tool (grep/search)")
    print()

    result = benchmark_model(model_path, model_name)

    # Save results
    output_file = Path("benchmark_current_results.json")
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n✓ Results saved to: {output_file}")

    # Save text output
    text_output = Path("benchmark_current_output.txt")
    with open(text_output, "w") as f:
        f.write("Current Production Model Benchmark\n")
        f.write("="*80 + "\n")
        f.write(f"Model: {model_name}\n")
        f.write(f"Path: {model_path}\n")
        f.write(f"Query: '{TEST_QUERY['query']}'\n")
        f.write(f"Expected: Should call a tool\n")
        f.write("\n")
        if "error" in result:
            f.write("="*80 + "\n")
            f.write(f"ERROR: {result['error']}\n")
            f.write("="*80 + "\n")
        else:
            f.write("="*80 + "\n")
            f.write("RESULTS\n")
            f.write("="*80 + "\n")
            disk = f"{result['disk_size_gb']:.2f} GB" if result.get('disk_size_gb') else "N/A"
            f.write(f"Disk size:          {disk}\n")
            f.write(f"Memory:             {result['memory_gb']:.2f} GB\n")
            f.write(f"Load time:          {result['load_time_s']:.2f}s\n")
            f.write(f"Warm-up time:       {result['warmup_time_s']:.2f}s\n")
            f.write(f"Steady-state avg:   {result['steady_state_avg_s']:.2f}s\n")
            f.write(f"Accuracy:           {result['accuracy_percent']:.0f}% ({result['total_correct']}/{result['total_queries']})\n")
            f.write("="*80 + "\n")

    print(f"✓ Text output saved to: {text_output}")


if __name__ == "__main__":
    main()
