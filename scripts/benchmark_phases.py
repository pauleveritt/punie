#!/usr/bin/env python3
"""Comprehensive benchmark comparing Phase 21, 22, 23, and 26 models.

Measures:
- Disk size (GB)
- Runtime memory (GB)
- Load time (seconds)
- Generation time per query (seconds)
- Accuracy (discrimination: tool vs direct answers)

Models tested:
- Phase 21: XML format (5-bit)
- Phase 22: Code Mode (5-bit)
- Phase 23: Typed tools (5-bit)
- Phase 26: Field access (6-bit)
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


# Test queries (3 tool, 2 direct) - same as Phase 8 benchmark
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


# Removed: Use shared is_tool_response() from prompt_utils instead


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
    memory_gb = mx.metal.get_active_memory() / 1024**3
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

        # Generate response with deterministic temperature
        start = time.time()
        try:
            response_text = generate(
                model,
                tokenizer,
                prompt=prompt,
                max_tokens=512,
                temp=0,  # Deterministic generation
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
        "avg_gen_time_s": avg_gen_time,  # Includes warm-up (for backward compat)
        "total_gen_time_s": total_gen_time,
        "accuracy_pct": accuracy,
        "correct": correct,
        "total": len(TEST_QUERIES),
        "results": results,
    }


def print_comparison_table(benchmarks: list[dict]) -> None:
    """Print formatted comparison table."""
    print("\n" + "="*100)
    print("COMPREHENSIVE BENCHMARK COMPARISON")
    print("="*100)
    print()

    # Header
    print(f"{'Model':<35} {'Disk':<8} {'Memory':<8} {'Load':<7} {'Warmup':<8} {'Steady':<8} {'Accuracy':<10}")
    print(f"{'':35} {'(GB)':<8} {'(GB)':<8} {'(s)':<7} {'(s)':<8} {'(s)':<8} {'(%)':<10}")
    print("-" * 110)

    # Sort by phase number (extract from path)
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
        elif "phase26" in path:
            return 26
        return 99

    benchmarks_sorted = sorted(benchmarks, key=get_phase_num)

    # Print each model
    for b in benchmarks_sorted:
        if "error" in b:
            model_name = Path(b["model"]).name
            print(f"{model_name:<35} {'N/A':<8} {'N/A':<8} {'N/A':<7} {'N/A':<8} {'N/A':<8} {'ERROR':<10}")
            print(f"  Error: {b['error']}")
        else:
            model_name = Path(b["model"]).name
            print(
                f"{model_name:<35} "
                f"{b['disk_size_gb']:>6.2f}  "
                f"{b['memory_gb']:>6.2f}  "
                f"{b['load_time_s']:>5.2f}  "
                f"{b['warmup_time_s']:>6.2f}  "
                f"{b['steady_state_avg_s']:>6.2f}  "
                f"{b['accuracy_pct']:>7.0f}%"
            )

    print("-" * 110)

    # Calculate improvements from Phase 21 (baseline)
    phase21 = next((b for b in benchmarks if "phase21" in b["model"] and "error" not in b), None)
    phase26 = next((b for b in benchmarks if "phase26" in b["model"] and "error" not in b), None)

    if phase21 and phase26:
        print("\nPhase 26 vs Phase 21 (baseline):")
        print(f"  Disk size: {phase21['disk_size_gb']:.2f} GB → {phase26['disk_size_gb']:.2f} GB ({phase26['disk_size_gb']/phase21['disk_size_gb']*100-100:+.0f}%)")
        print(f"  Memory: {phase21['memory_gb']:.2f} GB → {phase26['memory_gb']:.2f} GB ({phase26['memory_gb']/phase21['memory_gb']*100-100:+.0f}%)")
        print(f"  Load time: {phase21['load_time_s']:.2f}s → {phase26['load_time_s']:.2f}s ({phase26['load_time_s']/phase21['load_time_s']*100-100:+.0f}%)")
        print(f"  Warm-up: {phase21['warmup_time_s']:.2f}s → {phase26['warmup_time_s']:.2f}s ({phase26['warmup_time_s']/phase21['warmup_time_s']*100-100:+.0f}%)")
        print(f"  Steady-state: {phase21['steady_state_avg_s']:.2f}s → {phase26['steady_state_avg_s']:.2f}s ({phase26['steady_state_avg_s']/phase21['steady_state_avg_s']*100-100:+.0f}%)")
        print(f"  Accuracy: {phase21['accuracy_pct']:.0f}% → {phase26['accuracy_pct']:.0f}% ({phase26['accuracy_pct']-phase21['accuracy_pct']:+.0f} points)")

    # Speed ranking (steady-state, excludes warm-up)
    print("\nSpeed Ranking (Steady-State Avg, Q2-Q5):")
    speed_sorted = [b for b in benchmarks if "error" not in b]
    speed_sorted.sort(key=lambda x: x["steady_state_avg_s"])
    for i, b in enumerate(speed_sorted, 1):
        model_name = Path(b["model"]).name
        print(f"  {i}. {model_name}: {b['steady_state_avg_s']:.2f}s (warmup: {b['warmup_time_s']:.2f}s)")

    # Quality ranking
    print("\nQuality Ranking (Accuracy):")
    quality_sorted = [b for b in benchmarks if "error" not in b]
    quality_sorted.sort(key=lambda x: x["accuracy_pct"], reverse=True)
    for i, b in enumerate(quality_sorted, 1):
        model_name = Path(b["model"]).name
        print(f"  {i}. {model_name}: {b['accuracy_pct']:.0f}% ({b['correct']}/{b['total']})")

    print()


def main():
    """Run comprehensive benchmark across all phases."""
    models = [
        "fused_model_qwen3_phase21_xml_5bit",
        "fused_model_qwen3_phase22_code_5bit",
        "fused_model_qwen3_phase23_ty_5bit",
        "fused_model_qwen3_phase26_5bit",
        "fused_model_qwen3_phase26_6bit",
    ]

    print("="*100)
    print("COMPREHENSIVE PHASE BENCHMARK")
    print("="*100)
    print()
    print("Models to test:")
    for model in models:
        exists = "✓" if Path(model).exists() else "✗"
        print(f"  {exists} {model}")
    print()

    benchmarks = []
    for model in models:
        result = benchmark_model(model, verbose=True)
        benchmarks.append(result)

        # Clear memory between models
        mx.metal.clear_cache()

    # Print comparison table
    print_comparison_table(benchmarks)

    # Save results to JSON
    output_file = Path("logs/phase_benchmark_comparison.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w") as f:
        json.dump(benchmarks, f, indent=2)

    print(f"Results saved to: {output_file}")


if __name__ == "__main__":
    main()
