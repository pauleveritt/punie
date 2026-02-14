"""Benchmark Phase 5 model vs. base model: speed, memory, and quality."""

import argparse
import os
import time
from pathlib import Path
from typing import Literal

import mlx.core as mx
from mlx_lm import load, generate

# Test queries covering different scenarios
TEST_QUERIES = [
    {
        "id": "concept",
        "query": "What is dependency injection?",
        "type": "direct",
        "description": "Concept question - should give direct answer",
    },
    {
        "id": "comparison",
        "query": "What is the difference between a Registry and a Container?",
        "type": "direct",
        "description": "Comparison question - should give direct answer",
    },
    {
        "id": "search",
        "query": "Find all classes that inherit from Protocol",
        "type": "tool",
        "description": "Search query - should use tool",
    },
    {
        "id": "read",
        "query": "Show me the basic injection example",
        "type": "tool",
        "description": "Read file query - should use tool",
    },
    {
        "id": "best_practice",
        "query": "When should I use svcs vs a DI framework?",
        "type": "direct",
        "description": "Best practice question - should give direct answer",
    },
]

SYSTEM_MSG = "You are Punie, an AI coding assistant that helps with Python development via PyCharm."

# Model configurations
MODEL_CONFIGS = {
    "base": {
        "name": "Base (4-bit)",
        "description": "Qwen2.5-Coder-7B-Instruct-4bit (no fine-tuning)",
        "model_path": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        "adapter_path": None,
        "disk_path": None,  # Downloaded to cache, not local
    },
    "adapter": {
        "name": "Phase 5 Adapter",
        "description": "Base + LoRA adapters (244 examples)",
        "model_path": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        "adapter_path": "./adapters",
        "disk_path": "./adapters",
    },
    "fused-4bit": {
        "name": "Phase 5 Fused (4-bit)",
        "description": "Broken: LoRA merged + re-quantized to 4-bit",
        "model_path": "./fused_model",
        "adapter_path": None,
        "disk_path": "./fused_model",
    },
    "fused-f16": {
        "name": "Phase 5 Fused (float16)",
        "description": "LoRA merged to full precision float16",
        "model_path": "./fused_model_f16",
        "adapter_path": None,
        "disk_path": "./fused_model_f16",
    },
    "fused-8bit": {
        "name": "Phase 5 Fused (8-bit)",
        "description": "LoRA merged + quantized to 8-bit",
        "model_path": "./fused_model_8bit",
        "adapter_path": None,
        "disk_path": "./fused_model_8bit",
    },
}

# Default configs to run (excludes broken fused-4bit)
DEFAULT_CONFIGS = ["base", "adapter", "fused-f16", "fused-8bit"]


def get_directory_size(path: str | None) -> float | None:
    """Get total size of directory in GB."""
    if not path or not os.path.exists(path):
        return None

    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total += os.path.getsize(filepath)

    return total / (1024**3)  # Convert to GB


def format_prompt(query: str) -> str:
    """Format query as chat prompt."""
    return f"<|im_start|>system\n{SYSTEM_MSG}<|im_end|>\n<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n"


def has_tool_call(response: str) -> bool:
    """Check if response contains a tool call."""
    return (
        "I'll use the" in response
        or ("```json" in response and '"name":' in response)
    )


def evaluate_quality(
    response: str, expected_type: Literal["tool", "direct"]
) -> dict[str, bool | str]:
    """Evaluate response quality."""
    actual_type = "tool" if has_tool_call(response) else "direct"
    correct_type = actual_type == expected_type

    # Check response length
    reasonable_length = 50 < len(response) < 500

    # Check for common issues
    has_repetition = any(
        response.count(phrase) > 2
        for phrase in response.split(".")[:5]
    )
    has_truncation = response.endswith("...")

    return {
        "correct_type": correct_type,
        "actual_type": actual_type,
        "reasonable_length": reasonable_length,
        "has_repetition": has_repetition,
        "has_truncation": has_truncation,
        "response_length": len(response),
    }


def benchmark_model(
    config_name: str,
    config: dict,
    queries: list[dict] = TEST_QUERIES,
) -> dict:
    """Benchmark a model on test queries."""
    print(f"\n{'=' * 80}")
    print(f"Benchmarking: {config['name']}")
    print(f"Description: {config['description']}")
    print(f"Model path: {config['model_path']}")
    if config['adapter_path']:
        print(f"Adapter: {config['adapter_path']}")
    print(f"{'=' * 80}\n")

    # Calculate disk size
    disk_size_gb = get_directory_size(config['disk_path'])
    if disk_size_gb:
        print(f"Disk size: {disk_size_gb:.2f} GB")

    # Load model
    print("Loading model...")
    start_load = time.time()
    model, tokenizer = load(
        config['model_path'],
        adapter_path=config['adapter_path'],
    )
    load_time = time.time() - start_load
    print(f"✓ Model loaded in {load_time:.2f}s")

    # Get initial memory
    initial_memory = mx.metal.get_active_memory() / 1024**3  # GB
    peak_memory = initial_memory

    # Warm-up query to eliminate Metal JIT compilation variance
    print("Running warm-up query...")
    warmup_prompt = format_prompt("What is Python?")
    generate(model, tokenizer, prompt=warmup_prompt, max_tokens=50, verbose=False)
    print("✓ Warm-up complete\n")

    results = []

    for i, test_case in enumerate(queries, 1):
        query = test_case["query"]
        expected_type = test_case["type"]
        description = test_case["description"]

        print(f"\n{i}. {description}")
        print(f"   Query: \"{query[:60]}{'...' if len(query) > 60 else ''}\"")

        # Generate response
        prompt = format_prompt(query)
        start_gen = time.time()

        response = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=300,
            verbose=False,
        )

        gen_time = time.time() - start_gen

        # Check memory
        current_memory = mx.metal.get_active_memory() / 1024**3
        peak_memory = max(peak_memory, current_memory)

        # Evaluate quality
        quality = evaluate_quality(response, expected_type)

        # Store results
        result = {
            "id": test_case["id"],
            "query": query,
            "expected_type": expected_type,
            "actual_type": quality["actual_type"],
            "correct_type": quality["correct_type"],
            "gen_time": gen_time,
            "response_length": quality["response_length"],
            "reasonable_length": quality["reasonable_length"],
            "has_repetition": quality["has_repetition"],
            "has_truncation": quality["has_truncation"],
            "response": response[:200] + ("..." if len(response) > 200 else ""),
        }
        results.append(result)

        # Print summary
        status = "✅" if quality["correct_type"] else "❌"
        print(f"   {status} Expected: {expected_type.upper()}, Actual: {quality['actual_type'].upper()}")
        print(f"   Time: {gen_time:.2f}s, Length: {quality['response_length']} chars")
        print(f"   Response: {result['response'][:100]}...")

    # Calculate aggregate metrics
    correct_count = sum(1 for r in results if r["correct_type"])
    accuracy = (correct_count / len(results) * 100) if results else 0
    avg_time = sum(r["gen_time"] for r in results) / len(results) if results else 0

    summary = {
        "config_name": config_name,
        "model_name": config["name"],
        "description": config["description"],
        "load_time": load_time,
        "initial_memory_gb": initial_memory,
        "peak_memory_gb": peak_memory,
        "disk_size_gb": disk_size_gb,
        "num_queries": len(results),
        "correct_count": correct_count,
        "accuracy_pct": accuracy,
        "avg_gen_time": avg_time,
        "total_time": sum(r["gen_time"] for r in results),
        "results": results,
    }

    return summary


def print_comparison(summaries: list[dict]) -> None:
    """Print comparison table for N models."""
    if len(summaries) < 2:
        print("Need at least 2 models to compare")
        return

    base_summary = summaries[0]  # Use first as baseline

    print("\n" + "=" * 100)
    print(f"COMPARISON: {' vs. '.join(s['model_name'] for s in summaries)}")
    print("=" * 100)

    # Speed comparison
    print("\n📊 SPEED")
    print("-" * 100)

    # Header
    header = f"{'Metric':<25}"
    for s in summaries:
        header += f" {s['model_name']:<15}"
    for i in range(1, len(summaries)):
        header += f" {summaries[i]['model_name']} vs Base"
    print(header)
    print("-" * 100)

    # Load time
    row = f"{'Load Time':<25}"
    for s in summaries:
        row += f" {s['load_time']:>6.2f}s{'':<8}"
    for i in range(1, len(summaries)):
        diff = summaries[i]["load_time"] - base_summary["load_time"]
        pct = (diff / base_summary["load_time"] * 100) if base_summary["load_time"] > 0 else 0
        row += f" {diff:>+5.2f}s ({pct:+.0f}%){'':<5}"
    print(row)

    # Avg generation time
    row = f"{'Avg Generation Time':<25}"
    for s in summaries:
        row += f" {s['avg_gen_time']:>6.2f}s{'':<8}"
    for i in range(1, len(summaries)):
        diff = summaries[i]["avg_gen_time"] - base_summary["avg_gen_time"]
        pct = (diff / base_summary["avg_gen_time"] * 100) if base_summary["avg_gen_time"] > 0 else 0
        row += f" {diff:>+5.2f}s ({pct:+.0f}%){'':<5}"
    print(row)

    # Total time
    row = f"{'Total Generation Time':<25}"
    for s in summaries:
        row += f" {s['total_time']:>6.2f}s{'':<8}"
    for i in range(1, len(summaries)):
        diff = summaries[i]["total_time"] - base_summary["total_time"]
        pct = (diff / base_summary["total_time"] * 100) if base_summary["total_time"] > 0 else 0
        row += f" {diff:>+5.2f}s ({pct:+.0f}%){'':<5}"
    print(row)

    # Memory comparison
    print("\n💾 MEMORY")
    print("-" * 100)

    header = f"{'Metric':<25}"
    for s in summaries:
        header += f" {s['model_name']:<15}"
    for i in range(1, len(summaries)):
        header += f" {summaries[i]['model_name']} vs Base"
    print(header)
    print("-" * 100)

    # Disk size
    row = f"{'Disk Size':<25}"
    for s in summaries:
        if s['disk_size_gb']:
            row += f" {s['disk_size_gb']:>6.2f} GB{'':<6}"
        else:
            row += f" {'N/A':<15}"
    for i in range(1, len(summaries)):
        if summaries[i]['disk_size_gb'] and base_summary['disk_size_gb']:
            diff = summaries[i]["disk_size_gb"] - base_summary["disk_size_gb"]
            pct = (diff / base_summary["disk_size_gb"] * 100) if base_summary["disk_size_gb"] > 0 else 0
            row += f" {diff:>+5.2f} GB ({pct:+.0f}%){'':<5}"
        else:
            row += f" {'N/A':<20}"
    print(row)

    # Peak memory
    row = f"{'Peak Memory':<25}"
    for s in summaries:
        row += f" {s['peak_memory_gb']:>6.2f} GB{'':<6}"
    for i in range(1, len(summaries)):
        diff = summaries[i]["peak_memory_gb"] - base_summary["peak_memory_gb"]
        pct = (diff / base_summary["peak_memory_gb"] * 100) if base_summary["peak_memory_gb"] > 0 else 0
        row += f" {diff:>+5.2f} GB ({pct:+.0f}%){'':<5}"
    print(row)

    # Quality comparison
    print("\n🎯 QUALITY")
    print("-" * 100)

    header = f"{'Metric':<25}"
    for s in summaries:
        header += f" {s['model_name']:<15}"
    for i in range(1, len(summaries)):
        header += f" {summaries[i]['model_name']} vs Base"
    print(header)
    print("-" * 100)

    # Discrimination accuracy
    row = f"{'Discrimination Accuracy':<25}"
    for s in summaries:
        row += f" {s['correct_count']}/{s['num_queries']} ({s['accuracy_pct']:>5.1f}%){'':<2}"
    for i in range(1, len(summaries)):
        diff = summaries[i]["accuracy_pct"] - base_summary["accuracy_pct"]
        row += f" {diff:>+5.1f}pp{'':<15}"
    print(row)

    # Per-query comparison
    print("\n📋 PER-QUERY COMPARISON")
    print("-" * 100)

    header = f"{'Query':<15}"
    for s in summaries:
        header += f" {s['model_name'][:10]:<12}"
    for s in summaries:
        header += f" {s['model_name'][:10]} Time"
    print(header)
    print("-" * 100)

    for query_idx in range(len(base_summary["results"])):
        row = f"{summaries[0]['results'][query_idx]['id']:<15}"

        # Status for each model
        for s in summaries:
            r = s["results"][query_idx]
            status = "✅" if r["correct_type"] else "❌"
            row += f" {status} {r['actual_type'][:4]:<6}"

        # Time for each model
        for s in summaries:
            r = s["results"][query_idx]
            row += f" {r['gen_time']:>5.2f}s{'':<5}"

        print(row)

    # Summary verdict
    print("\n" + "=" * 100)
    print("VERDICT")
    print("=" * 100)

    for i in range(1, len(summaries)):
        s = summaries[i]
        acc_diff = s["accuracy_pct"] - base_summary["accuracy_pct"]
        time_diff = s["avg_gen_time"] - base_summary["avg_gen_time"]
        time_pct = (time_diff / base_summary["avg_gen_time"] * 100) if base_summary["avg_gen_time"] > 0 else 0
        mem_diff = s["peak_memory_gb"] - base_summary["peak_memory_gb"]
        mem_pct = (mem_diff / base_summary["peak_memory_gb"] * 100) if base_summary["peak_memory_gb"] > 0 else 0

        print(f"\n{s['model_name']}:")

        # Quality
        if s["accuracy_pct"] > base_summary["accuracy_pct"]:
            print(f"  🎯 Quality: ✅ BETTER (+{acc_diff:.1f}pp)")
        elif s["accuracy_pct"] == base_summary["accuracy_pct"]:
            print(f"  🎯 Quality: ➡️  SAME")
        else:
            print(f"  🎯 Quality: ⚠️  WORSE ({acc_diff:.1f}pp)")

        # Speed
        if abs(time_pct) < 5:
            print(f"  ⚡ Speed: ➡️  SIMILAR (±{abs(time_pct):.1f}%)")
        elif time_pct < 0:
            print(f"  ⚡ Speed: ✅ FASTER ({time_pct:.1f}%)")
        else:
            print(f"  ⚡ Speed: ⚠️  SLOWER (+{time_pct:.1f}%)")

        # Memory
        if abs(mem_pct) < 5:
            print(f"  💾 Memory: ➡️  SIMILAR (±{abs(mem_pct):.1f}%)")
        elif mem_pct < 0:
            print(f"  💾 Memory: ✅ LESS ({mem_pct:.1f}%)")
        else:
            print(f"  💾 Memory: ⚠️  MORE (+{mem_pct:.1f}%)")

    # Overall recommendation
    print("\n💡 OVERALL RECOMMENDATION:")

    # Find best quality configs
    max_accuracy = max(s["accuracy_pct"] for s in summaries)
    best_quality = [s for s in summaries if s["accuracy_pct"] == max_accuracy]

    if len(best_quality) == 1:
        print(f"  Best quality: {best_quality[0]['model_name']} ({max_accuracy:.1f}% accuracy)")
    else:
        # Among best quality, find fastest
        best = min(best_quality, key=lambda s: s["avg_gen_time"])
        print(f"  ✅ WINNER: {best['model_name']}")
        print(f"     • Same quality as others ({max_accuracy:.1f}% accuracy)")
        print(f"     • Fastest among top performers ({best['avg_gen_time']:.2f}s avg)")
        if best['disk_size_gb']:
            print(f"     • Disk size: {best['disk_size_gb']:.2f} GB")

    print("\n" + "=" * 100)


def main():
    """Run benchmark comparison."""
    parser = argparse.ArgumentParser(
        description="Benchmark Phase 5 models with various configurations"
    )
    parser.add_argument(
        "--configs",
        nargs="+",
        choices=list(MODEL_CONFIGS.keys()),
        default=DEFAULT_CONFIGS,
        help=f"Model configurations to benchmark (default: {', '.join(DEFAULT_CONFIGS)})",
    )
    args = parser.parse_args()

    print("\n" + "=" * 100)
    print("PHASE 5 MODEL BENCHMARK")
    print("=" * 100)
    print("\nConfigurations to test:")
    for config_name in args.configs:
        config = MODEL_CONFIGS[config_name]
        print(f"  • {config['name']}: {config['description']}")

    print("\nMetrics:")
    print("  • Speed: Load time + generation time per query")
    print("  • Memory: Disk size + peak runtime memory")
    print("  • Quality: Discrimination accuracy (tool vs direct answer)")

    # Benchmark each configuration
    summaries = []
    for config_name in args.configs:
        config = MODEL_CONFIGS[config_name]

        # Skip if model doesn't exist locally
        if config['disk_path'] and not os.path.exists(config['disk_path']):
            print(f"\n⚠️  Skipping {config['name']} - not found at {config['disk_path']}")
            continue

        summary = benchmark_model(config_name, config)
        summaries.append(summary)

    # Print comparison
    if len(summaries) >= 2:
        print_comparison(summaries)
    elif len(summaries) == 1:
        print("\n⚠️  Only one model benchmarked - need at least 2 for comparison")
    else:
        print("\n❌ No models benchmarked")


if __name__ == "__main__":
    main()
