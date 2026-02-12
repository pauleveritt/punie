"""Benchmark Qwen3-Coder-30B-A3B-Instruct-4bit training speed.

This validates whether the target model (30B with ~3B active parameters)
is trainable on M1 32GB RAM.

Decision criteria:
- ~1-5 sec/iter: ✅ Excellent (100 iters = 2-8 min)
- ~10-30 sec/iter: ✅ Acceptable (100 iters = 15-50 min)
- >60 sec/iter: ❌ Too slow, pivot to 7B model

Run: uv run python benchmark_30b_model.py
"""

import asyncio
from pathlib import Path

from punie.training.benchmark import create_dummy_dataset, run_training_benchmark


async def main():
    """Run 30B model training benchmark."""
    print("=" * 70)
    print("🔬 Qwen3-Coder-30B-A3B-Instruct-4bit Training Benchmark")
    print("=" * 70)

    model_path = "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"

    print(f"\nModel: {model_path}")
    print("Size: ~15GB (30B total parameters, ~3B active per forward pass)")
    print("Architecture: Mixture of Experts")
    print("\nBenchmark config:")
    print("  - 10 iterations")
    print("  - 5 training examples")
    print("  - Default batch size and learning rate")

    # Create dummy dataset
    data_dir = Path("data/benchmark-30b")
    if not data_dir.exists():
        print(f"\n📝 Creating dummy dataset in {data_dir}")
        create_dummy_dataset(data_dir, num_examples=5)
        print("✅ Dataset created")
    else:
        print(f"\n📁 Using existing dataset in {data_dir}")

    # Run benchmark
    print("\n🚀 Starting benchmark...")
    print("Note: First run will download model (~15GB), please be patient")
    print("-" * 70)

    try:
        result = await run_training_benchmark(
            model_path=model_path,
            num_iters=10,
        )

        print("\n" + "=" * 70)
        print("📊 Benchmark Results")
        print("=" * 70)

        print(f"\nModel: {result.model_path}")
        print(f"Iterations: {result.num_iters}")
        print(f"Total time: {result.total_seconds:.1f} seconds")
        print(f"Time per iteration: {result.seconds_per_iter:.2f} seconds")

        if result.peak_memory_gb:
            print(f"Peak memory: {result.peak_memory_gb:.2f} GB")

        # Decision
        print("\n" + "=" * 70)
        print("🎯 Decision")
        print("=" * 70)

        if result.seconds_per_iter < 5:
            print("\n✅ EXCELLENT - Model is very fast to train")
            print(f"   100 iterations would take ~{result.seconds_per_iter * 100 / 60:.1f} minutes")
            print("   👍 Proceed with 30B model")
        elif result.seconds_per_iter < 30:
            print("\n✅ ACCEPTABLE - Model is trainable")
            print(f"   100 iterations would take ~{result.seconds_per_iter * 100 / 60:.1f} minutes")
            print("   👍 Proceed with 30B model")
        elif result.seconds_per_iter < 60:
            print("\n⚠️  SLOW - Model is trainable but slow")
            print(f"   100 iterations would take ~{result.seconds_per_iter * 100 / 60:.1f} minutes")
            print("   🤔 Consider 7B model for faster iteration")
        else:
            print("\n❌ TOO SLOW - Model is not practical to train")
            print(f"   100 iterations would take ~{result.seconds_per_iter * 100 / 60:.1f} minutes")
            print("   ❌ Pivot to 7B model instead")

        print("\n" + "=" * 70)

        # Save results
        results_file = Path("benchmark_30b_results.txt")
        with open(results_file, "w") as f:
            f.write(f"Model: {result.model_path}\n")
            f.write(f"Iterations: {result.num_iters}\n")
            f.write(f"Total time: {result.total_seconds:.1f}s\n")
            f.write(f"Time per iteration: {result.seconds_per_iter:.2f}s\n")
            if result.peak_memory_gb:
                f.write(f"Peak memory: {result.peak_memory_gb:.2f} GB\n")

        print(f"\n📄 Results saved to: {results_file}")

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()

        print("\n" + "=" * 70)
        print("💡 Common Issues")
        print("=" * 70)
        print("1. Model not available - check model path")
        print("2. Insufficient memory - try smaller model")
        print("3. mlx_lm not installed - run: uv add --dev mlx-lm")
        return


if __name__ == "__main__":
    asyncio.run(main())
