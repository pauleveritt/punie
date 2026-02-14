#!/usr/bin/env python3
"""Benchmark Phase 8 (Qwen3-30B-A3B) vs Phase 7 (Qwen2.5-7B) adapters.

Runs 5-query discrimination test:
- Tool-calling queries (should use tools)
- Direct-answer queries (should NOT use tools)

Measures:
- Load time
- Generation time per query
- Accuracy (discrimination)
- Peak memory usage
"""

import json
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import generate, load


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


def format_prompt(query: str) -> str:
    """Format query in Qwen chat template."""
    return (
        "<|im_start|>system\n"
        "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
        "<|im_start|>user\n"
        f"{query}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def is_tool_response(response: str) -> bool:
    """Check if response contains a tool call."""
    return "```json" in response and '"name":' in response


def benchmark_model(model_path: str, adapter_path: str | None = None) -> dict:
    """Benchmark a model+adapter combination."""
    print(f"\n{'='*80}")
    print(f"Benchmarking: {model_path}")
    if adapter_path:
        print(f"Adapter: {adapter_path}")
    print('='*80)

    # Load model
    print("Loading model...")
    start = time.time()
    model, tokenizer = load(model_path, adapter_path=adapter_path)
    load_time = time.time() - start
    print(f"✓ Loaded in {load_time:.2f}s")

    # Get memory usage
    memory_gb = mx.metal.get_active_memory() / 1024**3
    print(f"  Memory: {memory_gb:.2f} GB")

    # Run test queries
    print("\nRunning test queries...")
    results = []
    total_gen_time = 0

    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/5] {test['description']}")
        print(f"  Query: {test['query']}")

        prompt = format_prompt(test["query"])

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
            "response": response_text[:200],  # First 200 chars
        })

    # Calculate metrics
    accuracy = sum(1 for r in results if r["correct"]) / len(results) * 100
    avg_gen_time = total_gen_time / len(results)

    print(f"\n{'='*80}")
    print("RESULTS:")
    print(f"  Accuracy: {accuracy:.1f}% ({sum(1 for r in results if r['correct'])}/{len(results)})")
    print(f"  Avg generation time: {avg_gen_time:.2f}s")
    print(f"  Load time: {load_time:.2f}s")
    print(f"  Memory: {memory_gb:.2f} GB")
    print('='*80)

    return {
        "model": model_path,
        "adapter": adapter_path,
        "load_time": load_time,
        "memory_gb": memory_gb,
        "avg_gen_time": avg_gen_time,
        "accuracy": accuracy,
        "results": results,
    }


def main():
    print("="*80)
    print("PHASE 8 vs PHASE 7 BENCHMARK")
    print("="*80)
    print("\nComparing:")
    print("  Phase 7: Qwen2.5-Coder-7B-Instruct-4bit + adapter")
    print("  Phase 8: Qwen3-Coder-30B-A3B-Instruct-4bit + adapter")
    print()

    # Benchmark Phase 7 (baseline)
    phase7_results = benchmark_model(
        model_path="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        adapter_path="adapters_phase7",
    )

    # Benchmark Phase 8 (new)
    phase8_results = benchmark_model(
        model_path="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
        adapter_path="adapters_phase8",
    )

    # Save results
    output_file = Path("logs/phase8_benchmark.json")
    with output_file.open("w") as f:
        json.dump({
            "phase7": phase7_results,
            "phase8": phase8_results,
            "comparison": {
                "accuracy_delta": phase8_results["accuracy"] - phase7_results["accuracy"],
                "speed_ratio": phase7_results["avg_gen_time"] / phase8_results["avg_gen_time"],
                "memory_delta": phase8_results["memory_gb"] - phase7_results["memory_gb"],
            }
        }, f, indent=2)

    print(f"\n✅ Results saved to {output_file}")

    # Print comparison
    print("\n" + "="*80)
    print("COMPARISON:")
    print("="*80)
    print(f"  Accuracy: Phase 7: {phase7_results['accuracy']:.1f}%, "
          f"Phase 8: {phase8_results['accuracy']:.1f}% "
          f"(Δ {phase8_results['accuracy'] - phase7_results['accuracy']:+.1f}%)")
    print(f"  Speed: Phase 7: {phase7_results['avg_gen_time']:.2f}s, "
          f"Phase 8: {phase8_results['avg_gen_time']:.2f}s "
          f"({phase7_results['avg_gen_time']/phase8_results['avg_gen_time']:.2f}x)")
    print(f"  Memory: Phase 7: {phase7_results['memory_gb']:.2f} GB, "
          f"Phase 8: {phase8_results['memory_gb']:.2f} GB "
          f"(Δ {phase8_results['memory_gb'] - phase7_results['memory_gb']:+.2f} GB)")
    print("="*80)


if __name__ == "__main__":
    main()
