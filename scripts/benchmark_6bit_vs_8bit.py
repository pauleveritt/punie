#!/usr/bin/env python3
"""Benchmark 6-bit vs 8-bit quantization for memory reduction experiment.

Research question:
  Does 6-bit (64 quantization levels) preserve LoRA signal
  while reducing memory by ~33% vs 8-bit (256 levels)?

Compares:
  - 8-bit fused model (baseline, known to work)
  - 6-bit fused model (experiment)

Measures:
  - Disk size
  - Runtime memory usage
  - Load time
  - Generation time
  - Accuracy (5-query discrimination test)
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


def get_disk_size(path: Path) -> float:
    """Get total disk size in GB."""
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / 1024**3


def benchmark_model(model_path: str, label: str) -> dict | None:
    """Benchmark a fused model."""
    print(f"\n{'='*80}")
    print(f"{label}")
    print(f"Model: {model_path}")
    print('='*80)

    path = Path(model_path)
    if not path.exists():
        print(f"❌ Model not found at {model_path}")
        return None

    # Get disk size
    disk_size = get_disk_size(path)
    print(f"Disk size: {disk_size:.2f} GB")

    # Load model
    print("Loading model...")
    start = time.time()
    model, tokenizer = load(model_path)
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
    print(f"  Disk size: {disk_size:.2f} GB")
    print(f"  Runtime memory: {memory_gb:.2f} GB")
    print(f"  Load time: {load_time:.2f}s")
    print(f"  Avg generation time: {avg_gen_time:.2f}s")
    print(f"  Accuracy: {accuracy:.1f}% ({sum(1 for r in results if r['correct'])}/{len(results)})")
    print('='*80)

    return {
        "model": model_path,
        "label": label,
        "disk_size_gb": disk_size,
        "load_time": load_time,
        "memory_gb": memory_gb,
        "avg_gen_time": avg_gen_time,
        "accuracy": accuracy,
        "results": results,
    }


def main():
    print("="*80)
    print("6-BIT vs 8-BIT QUANTIZATION BENCHMARK")
    print("="*80)
    print("\nResearch question:")
    print("  Does 6-bit (64 levels) preserve LoRA signal like 8-bit (256 levels)?")
    print("  Can we reduce memory by ~33% without losing accuracy?")
    print()

    # Benchmark 8-bit (baseline - known to work)
    results_8bit = benchmark_model(
        model_path="fused_model_qwen3_phase8_8bit",
        label="8-BIT BASELINE (256 quantization levels)",
    )

    # Benchmark 6-bit (experiment)
    results_6bit = benchmark_model(
        model_path="fused_model_qwen3_phase8_6bit",
        label="6-BIT EXPERIMENT (64 quantization levels)",
    )

    if not results_8bit or not results_6bit:
        print("\n❌ Benchmark incomplete - one or both models not found")
        return

    # Save results
    output_dir = Path("logs")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "6bit_vs_8bit_benchmark.json"

    with output_file.open("w") as f:
        json.dump({
            "8bit": results_8bit,
            "6bit": results_6bit,
            "comparison": {
                "accuracy_delta": results_6bit["accuracy"] - results_8bit["accuracy"],
                "speed_ratio": results_8bit["avg_gen_time"] / results_6bit["avg_gen_time"],
                "disk_size_reduction_gb": results_8bit["disk_size_gb"] - results_6bit["disk_size_gb"],
                "disk_size_reduction_pct": (1 - results_6bit["disk_size_gb"] / results_8bit["disk_size_gb"]) * 100,
                "memory_reduction_gb": results_8bit["memory_gb"] - results_6bit["memory_gb"],
            }
        }, f, indent=2)

    print(f"\n✅ Results saved to {output_file}")

    # Print comparison
    print("\n" + "="*80)
    print("COMPARISON:")
    print("="*80)

    # Disk size
    disk_reduction_pct = (1 - results_6bit["disk_size_gb"] / results_8bit["disk_size_gb"]) * 100
    print(f"  Disk size: 8-bit: {results_8bit['disk_size_gb']:.2f} GB, "
          f"6-bit: {results_6bit['disk_size_gb']:.2f} GB "
          f"({disk_reduction_pct:+.1f}% reduction)")

    # Memory
    memory_reduction = results_8bit["memory_gb"] - results_6bit["memory_gb"]
    print(f"  Runtime memory: 8-bit: {results_8bit['memory_gb']:.2f} GB, "
          f"6-bit: {results_6bit['memory_gb']:.2f} GB "
          f"(Δ {memory_reduction:+.2f} GB)")

    # Speed
    speed_ratio = results_8bit["avg_gen_time"] / results_6bit["avg_gen_time"]
    print(f"  Speed: 8-bit: {results_8bit['avg_gen_time']:.2f}s, "
          f"6-bit: {results_6bit['avg_gen_time']:.2f}s "
          f"({speed_ratio:.2f}x)")

    # Accuracy (most important!)
    accuracy_delta = results_6bit["accuracy"] - results_8bit["accuracy"]
    print(f"  Accuracy: 8-bit: {results_8bit['accuracy']:.1f}%, "
          f"6-bit: {results_6bit['accuracy']:.1f}% "
          f"(Δ {accuracy_delta:+.1f}%)")

    print("="*80)

    # Verdict
    print("\nVERDICT:")
    if results_6bit["accuracy"] >= 80:
        print("  ✅ 6-bit preserves quality! Memory reduction achieved.")
        print(f"     → {disk_reduction_pct:.1f}% disk size reduction")
        print(f"     → {results_6bit['accuracy']:.0f}% accuracy maintained")
    else:
        print("  ❌ 6-bit degrades quality too much")
        print(f"     → Only {results_6bit['accuracy']:.0f}% accuracy (target: 80%+)")
        print("     → Consider distillation or switching to smaller base model")
    print("="*80)


if __name__ == "__main__":
    main()
