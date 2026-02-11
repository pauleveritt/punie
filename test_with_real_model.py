"""Test training infrastructure with a real model.

This script:
1. Downloads a small model (Qwen2.5-Coder-1.5B - very small for testing)
2. Runs training speed benchmark
3. Runs evaluation with baseline suite
4. Generates HTML reports

Run: uv run python test_with_real_model.py
"""

import asyncio
from pathlib import Path

from punie.training.benchmark import create_dummy_dataset, run_training_benchmark
from punie.training.eval_report import generate_eval_html_report
from punie.training.eval_runner import EvalRunConfig, run_evaluation
from punie.training.eval_suites import create_baseline_suite
from punie.training.server_config import ServerConfig


async def main():
    """Run full infrastructure test."""
    print("=" * 70)
    print("🧪 Testing Training Infrastructure with Real Model")
    print("=" * 70)

    # Use a very small model for testing
    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    print(f"\n📦 Model: {model_path}")
    print("   (Small 1.5B model - good for testing, ~1GB download)")

    # Step 1: Benchmark training speed
    print("\n" + "=" * 70)
    print("Step 1: Training Speed Benchmark")
    print("=" * 70)
    print("Creating dummy dataset for benchmarking...")

    data_dir = Path("data/benchmark")
    create_dummy_dataset(data_dir, num_examples=5)
    print(f"✅ Dataset created: {data_dir}")

    print(f"\n🏃 Running training benchmark (10 iterations)...")
    print("This will download the model on first run (~1GB)")
    print("Subsequent runs will be much faster...")

    try:
        result = await run_training_benchmark(
            model_path=model_path,
            num_iters=10,
            data_dir=data_dir,
        )

        print(f"\n📊 Benchmark Results:")
        print(f"   Model: {result.model_path}")
        print(f"   Seconds per iteration: {result.seconds_per_iter:.2f}s")
        print(f"   Total time: {result.total_seconds:.2f}s")
        if result.peak_memory_gb:
            print(f"   Peak memory: {result.peak_memory_gb:.2f} GB")

        # Interpret results
        if result.seconds_per_iter < 5:
            print("\n✅ EXCELLENT: Very fast training (~1-5 sec/iter)")
            print("   → 100 iterations = 2-8 minutes")
        elif result.seconds_per_iter < 30:
            print("\n⚠️  ACCEPTABLE: Moderate speed (~5-30 sec/iter)")
            print(f"   → 100 iterations = ~{result.seconds_per_iter * 100 / 60:.1f} minutes")
        else:
            print("\n❌ TOO SLOW: Training would take too long")
            print("   → Consider using smaller model or cloud training")

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        print("This might be normal if model needs to download first.")
        print("Try running again - it should work after download completes.")
        return

    # Step 2: Evaluation
    print("\n" + "=" * 70)
    print("Step 2: Model Evaluation")
    print("=" * 70)

    suite = create_baseline_suite()
    print(f"\n📋 Evaluation Suite: {suite.name}")
    print(f"   Prompts: {len(suite.prompts)}")
    for p in suite.prompts:
        print(f"   - {p.id}: {p.category}")

    print(f"\n🔄 Running evaluation (this may take a few minutes)...")
    print("The server will start automatically...")

    server_config = ServerConfig(
        model_path=model_path,
        port=8080,
    )

    config = EvalRunConfig(
        server_config=server_config,
        suite=suite,
        workspace=Path.cwd(),
        manage_server=True,  # Auto-start/stop server
    )

    try:
        report = await run_evaluation(config)

        print(f"\n📊 Evaluation Results:")
        print(f"   Overall Score: {report.overall_score:.1%}")
        print(f"   Success Rate: {report.success_rate:.1%}")
        print(f"   Total Prompts: {len(report.results)}")
        print(f"   Successful: {sum(1 for r in report.results if r.success)}")

        # Generate HTML report
        html = generate_eval_html_report(report, suite)
        report_path = Path("eval_baseline_real.html")
        report_path.write_text(html)

        print(f"\n✅ HTML report generated: {report_path}")
        print(f"   Open it: open {report_path}")

        # Show category scores
        print("\n📈 Category Breakdown:")
        category_results = {}
        for result in report.results:
            prompt = next((p for p in suite.prompts if p.id == result.prompt_id), None)
            if prompt:
                if prompt.category not in category_results:
                    category_results[prompt.category] = []
                category_results[prompt.category].append(result)

        category_scores = report.score_by_category(category_results)
        for category, score in category_scores.items():
            print(f"   {category.replace('_', ' ').title()}: {score:.1%}")

    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Summary
    print("\n" + "=" * 70)
    print("✅ Testing Complete!")
    print("=" * 70)
    print(f"""
Next Steps:
1. Review HTML report: open {report_path}
2. Check baseline scores (likely low for untrained model - that's expected!)
3. Update docs/research/training-journal.md with results
4. Decide: Continue with this model size or try larger model
5. Then: Proceed to Phase 14 (Training Data Infrastructure)

Benchmark showed training at {result.seconds_per_iter:.1f} sec/iter
Evaluation showed {report.overall_score:.1%} overall score

Ready to start training data collection and fine-tuning!
""")


if __name__ == "__main__":
    asyncio.run(main())
