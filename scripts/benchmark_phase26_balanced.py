#!/usr/bin/env python3
"""Benchmark Phase 26 balanced model with warm-up and comparison to available phases.

Tests the standard 5-query benchmark:
1. Find all Django view functions (tool)
2. Show me the implementation of UserSerializer (tool)
3. What is dependency injection in Django? (direct)
4. Find all uses of async/await in the codebase (tool)
5. What's the difference between Django ORM and raw SQL? (direct)

Measures:
- Disk size (GB)
- Runtime memory (GB)
- Load time (seconds)
- Warm-up time (first query)
- Steady-state avg (queries 2-5)
- Accuracy (discrimination: tool vs direct)
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


# Standard test queries (3 tool, 2 direct)
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


def get_disk_size(path: Path) -> float:
    """Get total disk size of a directory in GB."""
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / 1024**3


def benchmark_model(model_path: str, verbose: bool = True) -> dict:
    """Benchmark a single model."""
    path = Path(model_path)

    if not path.exists():
        return {
            "model": model_path,
            "error": "Model not found",
        }

    if verbose:
        print(f"\n{'='*80}")
        print(f"Benchmarking: {model_path}")
        print('='*80)

    # Get disk size
    disk_size = get_disk_size(path)
    if verbose:
        print(f"Disk size: {disk_size:.2f} GB")

    # Load model
    if verbose:
        print("Loading model...")
    start = time.time()
    try:
        result = load(model_path)
        model, tokenizer = result[0], result[1]
    except Exception as e:
        return {
            "model": model_path,
            "error": f"Load failed: {e}",
        }

    load_time = time.time() - start
    if verbose:
        print(f"✓ Loaded in {load_time:.2f}s")

    # Get memory usage
    memory_gb = mx.get_active_memory() / 1024**3
    if verbose:
        print(f"  Runtime memory: {memory_gb:.2f} GB")

    # Run test queries
    if verbose:
        print("\nRunning test queries...")
    results = []
    total_gen_time = 0
    steady_state_gen_time = 0  # Excludes first query
    warmup_time = 0
    correct = 0

    for i, test in enumerate(TEST_QUERIES, 1):
        is_warmup = (i == 1)

        if verbose:
            warmup_marker = " [WARM-UP]" if is_warmup else ""
            print(f"\n[{i}/5] {test['description']}{warmup_marker}")
            print(f"  Query: {test['query']}")

        # Use shared utility to guarantee consistency
        prompt = format_prompt(test["query"], model_path)

        # Generate response
        start = time.time()
        try:
            response_text = generate(
                model,
                tokenizer,
                prompt=prompt,
                max_tokens=512,
                verbose=False,
            )
        except Exception as e:
            if verbose:
                print(f"  ✗ Generation failed: {e}")
            continue

        gen_time = time.time() - start
        total_gen_time += gen_time

        if is_warmup:
            warmup_time = gen_time
        else:
            steady_state_gen_time += gen_time

        # Check if tool was used
        used_tool = is_tool_response(response_text)
        expected_tool = test["expected"] == "tool"
        is_correct = used_tool == expected_tool
        correct += is_correct

        status = "✓" if is_correct else "✗"
        if verbose:
            print(f"  Expected: {test['expected']}, Got: {'tool' if used_tool else 'direct'} {status}")
            print(f"  Time: {gen_time:.2f}s")

        results.append({
            "query": test["query"],
            "expected": test["expected"],
            "got": "tool" if used_tool else "direct",
            "correct": is_correct,
            "time": gen_time,
            "is_warmup": is_warmup,
        })

    accuracy = (correct / len(TEST_QUERIES)) * 100 if results else 0
    avg_gen_time = total_gen_time / len(results) if results else 0
    steady_state_avg = steady_state_gen_time / (len(results) - 1) if len(results) > 1 else 0

    if verbose:
        print(f"\n{'='*80}")
        print(f"Results: {correct}/{len(TEST_QUERIES)} correct ({accuracy:.0f}%)")
        print(f"Timing breakdown:")
        print(f"  Warm-up (Q1): {warmup_time:.2f}s")
        print(f"  Steady-state avg (Q2-Q5): {steady_state_avg:.2f}s")
        print(f"  Overall avg (Q1-Q5): {avg_gen_time:.2f}s")
        print('='*80)

    return {
        "model": model_path,
        "disk_size_gb": disk_size,
        "memory_gb": memory_gb,
        "load_time_s": load_time,
        "warmup_time_s": warmup_time,
        "steady_state_avg_s": steady_state_avg,
        "avg_gen_time_s": avg_gen_time,
        "total_gen_time_s": total_gen_time,
        "accuracy_pct": accuracy,
        "correct": correct,
        "total": len(TEST_QUERIES),
        "results": results,
    }


def print_comparison_table(benchmarks: list[dict]) -> None:
    """Print formatted comparison table."""
    print("\n" + "="*110)
    print("PHASE BENCHMARK COMPARISON")
    print("="*110)
    print()

    # Header
    print(f"{'Model':<40} {'Disk':<8} {'Memory':<8} {'Load':<7} {'Warmup':<8} {'Steady':<8} {'Accuracy':<10}")
    print(f"{'':40} {'(GB)':<8} {'(GB)':<8} {'(s)':<7} {'(s)':<8} {'(s)':<8} {'(%)':<10}")
    print("-" * 110)

    # Sort by phase number
    def get_phase_num(b):
        if "error" in b:
            return 999
        path = b["model"]
        if "phase21" in path:
            return 21
        elif "phase22" in path:
            return 22
        elif "phase23" in path:
            return 23
        elif "phase26" in path and "balanced" in path:
            return 26.5  # Sort after regular phase26
        elif "phase26" in path:
            return 26
        return 99

    benchmarks_sorted = sorted(benchmarks, key=get_phase_num)

    # Print each model
    for b in benchmarks_sorted:
        if "error" in b:
            model_name = Path(b["model"]).name
            print(f"{model_name:<40} {'N/A':<8} {'N/A':<8} {'N/A':<7} {'N/A':<8} {'N/A':<8} {'ERROR':<10}")
            print(f"  Error: {b['error']}")
        else:
            model_name = Path(b["model"]).name
            print(
                f"{model_name:<40} "
                f"{b['disk_size_gb']:>6.2f}  "
                f"{b['memory_gb']:>6.2f}  "
                f"{b['load_time_s']:>5.2f}  "
                f"{b['warmup_time_s']:>6.2f}  "
                f"{b['steady_state_avg_s']:>6.2f}  "
                f"{b['accuracy_pct']:>7.0f}%"
            )

    print("-" * 110)

    # Find baseline and latest
    phase21 = next((b for b in benchmarks if "phase21" in b["model"] and "error" not in b), None)
    phase26_balanced = next((b for b in benchmarks if "phase26" in b["model"] and "balanced" in b["model"] and "error" not in b), None)

    if phase26_balanced:
        print("\nPhase 26 Balanced (Latest):")
        print(f"  Disk: {phase26_balanced['disk_size_gb']:.2f} GB")
        print(f"  Memory: {phase26_balanced['memory_gb']:.2f} GB")
        print(f"  Load: {phase26_balanced['load_time_s']:.2f}s")
        print(f"  Warm-up: {phase26_balanced['warmup_time_s']:.2f}s")
        print(f"  Steady-state: {phase26_balanced['steady_state_avg_s']:.2f}s")
        print(f"  Accuracy: {phase26_balanced['accuracy_pct']:.0f}% ({phase26_balanced['correct']}/{phase26_balanced['total']})")

    if phase21 and phase26_balanced:
        print(f"\nPhase 26 Balanced vs Phase 21 (XML baseline):")
        print(f"  Disk: {phase21['disk_size_gb']:.2f} GB → {phase26_balanced['disk_size_gb']:.2f} GB ({phase26_balanced['disk_size_gb']/phase21['disk_size_gb']*100-100:+.0f}%)")
        print(f"  Memory: {phase21['memory_gb']:.2f} GB → {phase26_balanced['memory_gb']:.2f} GB ({phase26_balanced['memory_gb']/phase21['memory_gb']*100-100:+.0f}%)")
        print(f"  Load: {phase21['load_time_s']:.2f}s → {phase26_balanced['load_time_s']:.2f}s ({phase26_balanced['load_time_s']/phase21['load_time_s']*100-100:+.0f}%)")
        print(f"  Steady-state: {phase21['steady_state_avg_s']:.2f}s → {phase26_balanced['steady_state_avg_s']:.2f}s ({phase26_balanced['steady_state_avg_s']/phase21['steady_state_avg_s']*100-100:+.0f}%)")
        print(f"  Accuracy: {phase21['accuracy_pct']:.0f}% → {phase26_balanced['accuracy_pct']:.0f}% ({phase26_balanced['accuracy_pct']-phase21['accuracy_pct']:+.0f} points)")

    # Speed ranking
    print("\nSpeed Ranking (Steady-State, Q2-Q5):")
    speed_sorted = [b for b in benchmarks if "error" not in b]
    speed_sorted.sort(key=lambda x: x["steady_state_avg_s"])
    for i, b in enumerate(speed_sorted, 1):
        model_name = Path(b["model"]).name
        marker = " ⭐" if "balanced" in b["model"] else ""
        print(f"  {i}. {model_name}{marker}: {b['steady_state_avg_s']:.2f}s")

    # Quality ranking
    print("\nAccuracy Ranking:")
    quality_sorted = [b for b in benchmarks if "error" not in b]
    quality_sorted.sort(key=lambda x: x["accuracy_pct"], reverse=True)
    for i, b in enumerate(quality_sorted, 1):
        model_name = Path(b["model"]).name
        marker = " ⭐" if "balanced" in b["model"] else ""
        print(f"  {i}. {model_name}{marker}: {b['accuracy_pct']:.0f}% ({b['correct']}/{b['total']})")

    print()


def main():
    """Run benchmark on Phase 26 balanced and compare with available phases."""
    # Check what models are available
    all_models = [
        "fused_model_qwen3_phase21_xml_5bit",
        "fused_model_qwen3_phase22_code_5bit",
        "fused_model_qwen3_phase23_ty_5bit",
        "fused_model_qwen3_phase26_5bit",
        "fused_model_qwen3_phase26_6bit",
        "fused_model_qwen3_phase26_balanced_5bit",  # NEW
    ]

    available_models = [m for m in all_models if Path(m).exists()]

    print("="*110)
    print("PHASE 26 BALANCED BENCHMARK")
    print("="*110)
    print()
    print("Available models to test:")
    for model in available_models:
        print(f"  ✓ {model}")
    print()
    print(f"Testing {len(available_models)} models with 5 standard queries (3 tool, 2 direct)")
    print()

    benchmarks = []
    for model in available_models:
        result = benchmark_model(model, verbose=True)
        benchmarks.append(result)

        # Clear memory between models
        mx.clear_cache()

    # Print comparison
    print_comparison_table(benchmarks)

    # Save results
    output_file = Path("logs/phase26_balanced_benchmark.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w") as f:
        json.dump(benchmarks, f, indent=2)

    print(f"Results saved to: {output_file}")


if __name__ == "__main__":
    main()
