"""Benchmark Phase 5 model vs. base model: speed, memory, and quality."""

import time
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
    model_name: str,
    adapter_path: str | None = None,
    queries: list[dict] = TEST_QUERIES,
) -> dict:
    """Benchmark a model on test queries."""
    print(f"\n{'=' * 80}")
    print(f"Benchmarking: {model_name}")
    if adapter_path:
        print(f"Adapter: {adapter_path}")
    print(f"{'=' * 80}\n")

    # Load model
    print("Loading model...")
    start_load = time.time()
    model, tokenizer = load(
        "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        adapter_path=adapter_path,
    )
    load_time = time.time() - start_load
    print(f"✓ Model loaded in {load_time:.2f}s")

    # Get initial memory
    initial_memory = mx.metal.get_active_memory() / 1024**3  # GB
    peak_memory = initial_memory

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
        "model_name": model_name,
        "adapter_path": adapter_path,
        "load_time": load_time,
        "initial_memory_gb": initial_memory,
        "peak_memory_gb": peak_memory,
        "num_queries": len(results),
        "correct_count": correct_count,
        "accuracy_pct": accuracy,
        "avg_gen_time": avg_time,
        "total_time": sum(r["gen_time"] for r in results),
        "results": results,
    }

    return summary


def print_comparison(base_summary: dict, phase5_summary: dict) -> None:
    """Print comparison table."""
    print("\n" + "=" * 80)
    print("COMPARISON: Base Model vs. Phase 5 Fine-Tuned")
    print("=" * 80)

    # Speed comparison
    print("\n📊 SPEED")
    print("-" * 80)
    print(f"{'Metric':<30} {'Base Model':<20} {'Phase 5':<20} {'Diff':<10}")
    print("-" * 80)

    load_diff = phase5_summary["load_time"] - base_summary["load_time"]
    load_pct = (load_diff / base_summary["load_time"] * 100) if base_summary["load_time"] > 0 else 0
    print(
        f"{'Model Load Time':<30} "
        f"{base_summary['load_time']:>6.2f}s{'':<13} "
        f"{phase5_summary['load_time']:>6.2f}s{'':<13} "
        f"{load_diff:>+6.2f}s ({load_pct:+.1f}%)"
    )

    time_diff = phase5_summary["avg_gen_time"] - base_summary["avg_gen_time"]
    time_pct = (time_diff / base_summary["avg_gen_time"] * 100) if base_summary["avg_gen_time"] > 0 else 0
    print(
        f"{'Avg Generation Time':<30} "
        f"{base_summary['avg_gen_time']:>6.2f}s{'':<13} "
        f"{phase5_summary['avg_gen_time']:>6.2f}s{'':<13} "
        f"{time_diff:>+6.2f}s ({time_pct:+.1f}%)"
    )

    total_diff = phase5_summary["total_time"] - base_summary["total_time"]
    total_pct = (total_diff / base_summary["total_time"] * 100) if base_summary["total_time"] > 0 else 0
    print(
        f"{'Total Generation Time':<30} "
        f"{base_summary['total_time']:>6.2f}s{'':<13} "
        f"{phase5_summary['total_time']:>6.2f}s{'':<13} "
        f"{total_diff:>+6.2f}s ({total_pct:+.1f}%)"
    )

    # Memory comparison
    print("\n💾 MEMORY")
    print("-" * 80)
    print(f"{'Metric':<30} {'Base Model':<20} {'Phase 5':<20} {'Diff':<10}")
    print("-" * 80)

    peak_diff = phase5_summary["peak_memory_gb"] - base_summary["peak_memory_gb"]
    peak_pct = (peak_diff / base_summary["peak_memory_gb"] * 100) if base_summary["peak_memory_gb"] > 0 else 0
    print(
        f"{'Peak Memory':<30} "
        f"{base_summary['peak_memory_gb']:>6.2f} GB{'':<12} "
        f"{phase5_summary['peak_memory_gb']:>6.2f} GB{'':<12} "
        f"{peak_diff:>+6.2f} GB ({peak_pct:+.1f}%)"
    )

    # Quality comparison
    print("\n🎯 QUALITY")
    print("-" * 80)
    print(f"{'Metric':<30} {'Base Model':<20} {'Phase 5':<20} {'Diff':<10}")
    print("-" * 80)

    acc_diff = phase5_summary["accuracy_pct"] - base_summary["accuracy_pct"]
    print(
        f"{'Discrimination Accuracy':<30} "
        f"{base_summary['correct_count']}/{base_summary['num_queries']} "
        f"({base_summary['accuracy_pct']:>5.1f}%){'':<6} "
        f"{phase5_summary['correct_count']}/{phase5_summary['num_queries']} "
        f"({phase5_summary['accuracy_pct']:>5.1f}%){'':<6} "
        f"{acc_diff:>+5.1f}pp"
    )

    # Per-query comparison
    print("\n📋 PER-QUERY COMPARISON")
    print("-" * 80)
    print(f"{'Query':<15} {'Base':<10} {'Phase 5':<10} {'Base Time':<12} {'P5 Time':<12} {'Speedup'}")
    print("-" * 80)

    for base_r, p5_r in zip(base_summary["results"], phase5_summary["results"]):
        base_status = "✅" if base_r["correct_type"] else "❌"
        p5_status = "✅" if p5_r["correct_type"] else "❌"
        speedup = ((base_r["gen_time"] - p5_r["gen_time"]) / base_r["gen_time"] * 100) if base_r["gen_time"] > 0 else 0

        print(
            f"{base_r['id']:<15} "
            f"{base_status} {base_r['actual_type'][:4]:<5} "
            f"{p5_status} {p5_r['actual_type'][:4]:<5} "
            f"{base_r['gen_time']:>6.2f}s{'':<5} "
            f"{p5_r['gen_time']:>6.2f}s{'':<5} "
            f"{speedup:>+6.1f}%"
        )

    # Summary
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    if phase5_summary["accuracy_pct"] > base_summary["accuracy_pct"]:
        print(f"✅ Quality: Phase 5 is BETTER (+{acc_diff:.1f}pp accuracy)")
    elif phase5_summary["accuracy_pct"] == base_summary["accuracy_pct"]:
        print("➡️  Quality: SAME accuracy")
    else:
        print(f"⚠️  Quality: Phase 5 is WORSE ({acc_diff:.1f}pp accuracy)")

    if abs(time_pct) < 5:
        print(f"➡️  Speed: SIMILAR (±{abs(time_pct):.1f}%)")
    elif time_pct < 0:
        print(f"✅ Speed: Phase 5 is FASTER ({time_pct:.1f}%)")
    else:
        print(f"⚠️  Speed: Phase 5 is SLOWER (+{time_pct:.1f}%)")

    if abs(peak_pct) < 5:
        print(f"➡️  Memory: SIMILAR (±{abs(peak_pct):.1f}%)")
    elif peak_pct < 0:
        print(f"✅ Memory: Phase 5 uses LESS ({peak_pct:.1f}%)")
    else:
        print(f"⚠️  Memory: Phase 5 uses MORE (+{peak_pct:.1f}%)")

    print("\n" + "=" * 80)


def main():
    """Run benchmark comparison."""
    print("\n" + "=" * 80)
    print("PHASE 5 vs BASE MODEL BENCHMARK")
    print("=" * 80)
    print("\nThis benchmark compares:")
    print("  • Base: Qwen2.5-Coder-7B-Instruct-4bit (no fine-tuning)")
    print("  • Phase 5: Same model + LoRA adapters (244 examples)")
    print("\nMetrics:")
    print("  • Speed: Load time + generation time per query")
    print("  • Memory: Peak memory usage during generation")
    print("  • Quality: Discrimination accuracy (tool vs direct answer)")

    # Benchmark base model
    base_summary = benchmark_model("Base Model (no adapters)", adapter_path=None)

    # Benchmark Phase 5 model
    phase5_summary = benchmark_model("Phase 5 (fine-tuned)", adapter_path="./adapters")

    # Print comparison
    print_comparison(base_summary, phase5_summary)


if __name__ == "__main__":
    main()
