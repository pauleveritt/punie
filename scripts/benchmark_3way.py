#!/usr/bin/env python3
"""3-way benchmark: Base Qwen3 → Phase 21 (pre-code-tools) → Phase 27 (current).

Measures the progression of:
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


def benchmark_model(model_path: str, model_name: str, verbose: bool = True) -> dict:
    """Benchmark a single model."""
    if verbose:
        print(f"\n{'='*80}")
        print(f"Benchmarking: {model_name}")
        print(f"Path: {model_path}")
        print('='*80)

    # Get disk size
    path = Path(model_path) if "/" in model_path else None
    disk_size = get_disk_size(path) if path else 0.0

    if verbose:
        if disk_size > 0:
            print(f"Disk size: {disk_size:.2f} GB")
        else:
            print("Disk size: N/A (cached model)")

    # Load model
    if verbose:
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
    if verbose:
        print(f"✓ Loaded in {load_time:.2f}s")

    # Get memory usage
    memory_gb = mx.metal.get_active_memory() / 1024**3
    if verbose:
        print(f"  Runtime memory: {memory_gb:.2f} GB")

    # Run warm-up query
    if verbose:
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
    warmup_used_tool = is_tool_response(warmup_response)

    if verbose:
        print(f"  Expected: {TEST_QUERY['expected']}, Got: {'tool' if warmup_used_tool else 'direct'}")
        print(f"  Warm-up time: {warmup_time:.2f}s")

    # Run steady-state queries (3 more times)
    if verbose:
        print("\nRunning steady-state queries (3x)...")

    steady_times = []
    all_correct = warmup_used_tool == (TEST_QUERY["expected"] == "tool")

    for i in range(3):
        start = time.time()
        try:
            response = generate(
                model,
                tokenizer,
                prompt=prompt,
                max_tokens=512,
                verbose=False,
            )
        except Exception as e:
            if verbose:
                print(f"  Query {i+1} failed: {e}")
            continue

        gen_time = time.time() - start
        steady_times.append(gen_time)
        used_tool = is_tool_response(response)
        is_correct = used_tool == (TEST_QUERY["expected"] == "tool")
        all_correct = all_correct and is_correct

        if verbose:
            status = "✓" if is_correct else "✗"
            print(f"  Query {i+1}: {gen_time:.2f}s {status}")

    steady_state_avg = sum(steady_times) / len(steady_times) if steady_times else 0
    accuracy = 100 if all_correct else 0

    if verbose:
        print(f"\n{'='*80}")
        print(f"Results:")
        print(f"  Accuracy: {'100%' if all_correct else '0% (at least one failure)'}")
        print(f"  Warm-up time: {warmup_time:.2f}s")
        print(f"  Steady-state avg: {steady_state_avg:.2f}s")
        print('='*80)

    return {
        "model": model_name,
        "path": model_path,
        "disk_size_gb": disk_size,
        "memory_gb": memory_gb,
        "load_time_s": load_time,
        "warmup_time_s": warmup_time,
        "steady_state_avg_s": steady_state_avg,
        "accuracy_pct": accuracy,
        "all_correct": all_correct,
    }


def main():
    """Run 3-way comparison."""
    print("3-Way Model Comparison")
    print("=" * 80)
    print("Query: 'Show me how the protocol class is used in the codebase'")
    print("Expected: Should call a tool (grep/search)")
    print()

    models = [
        {
            "name": "Base Qwen3-30B-A3B",
            "path": "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
        },
        {
            "name": "Phase 21 (XML, pre-code-tools)",
            "path": "fused_model_qwen3_phase21_5bit",
        },
        {
            "name": "Phase 27 (Current production)",
            "path": "fused_model_qwen3_phase27_cleaned_5bit",
        },
    ]

    results = []
    for model_info in models:
        result = benchmark_model(model_info["path"], model_info["name"])
        results.append(result)

        # Clear model from memory between tests
        import gc
        gc.collect()
        mx.metal.clear_cache()

    # Print comparison table
    print("\n" + "=" * 80)
    print("COMPARISON TABLE")
    print("=" * 80)
    print()
    print(f"{'Model':<35} {'Disk':>8} {'Memory':>8} {'Load':>7} {'Warmup':>8} {'Steady':>8} {'Accuracy':>10}")
    print(f"{'':35} {'(GB)':>8} {'(GB)':>8} {'(s)':>7} {'(s)':>8} {'(s)':>8} {'':>10}")
    print("-" * 80)

    for r in results:
        if "error" in r:
            print(f"{r['model']:<35} ERROR: {r['error']}")
        else:
            disk = f"{r['disk_size_gb']:.1f}" if r['disk_size_gb'] > 0 else "N/A"
            print(
                f"{r['model']:<35} "
                f"{disk:>8} "
                f"{r['memory_gb']:>8.1f} "
                f"{r['load_time_s']:>7.1f} "
                f"{r['warmup_time_s']:>8.2f} "
                f"{r['steady_state_avg_s']:>8.2f} "
                f"{r['accuracy_pct']:>9.0f}%"
            )

    print("=" * 80)

    # Save results
    output_file = Path("benchmark_3way_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Results saved to: {output_file}")


if __name__ == "__main__":
    main()
