"""Demonstrate successful training with measurable improvement.

This proves the training infrastructure works by:
1. Using realistic dataset (85 examples)
2. Training with proper parameters (100 iterations)
3. Evaluating baseline vs adapted
4. Showing actual improvement

Run: uv run python run_successful_training_demo.py
"""

import asyncio
from pathlib import Path

from punie.training.eval_comparison import compare_reports
from punie.training.eval_prompts import EvalPrompt, EvalSuite
from punie.training.eval_report import generate_eval_html_report
from punie.training.eval_runner import EvalRunConfig, run_evaluation
from punie.training.lora_config import LoRAConfig
from punie.training.server_config import ServerConfig
from punie.training.train_runner import run_training_with_logs
from punie.training.hyperparam import parse_training_log


async def main():
    """Run successful training demonstration."""
    print("=" * 70)
    print("🎯 Successful Training Demonstration")
    print("=" * 70)
    print("\nThis proves the training infrastructure works by showing")
    print("measurable improvement with realistic parameters.")

    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    data_dir = Path("data/realistic-training")
    adapter_dir = Path("adapters/successful-demo")

    # Check data exists
    if not data_dir.exists():
        print(f"\n❌ Dataset not found: {data_dir}")
        print("   Run: uv run python create_realistic_training_dataset.py")
        return

    print(f"\n📊 Dataset: {data_dir}")
    print(f"   Model: {model_path}")
    print(f"   Output: {adapter_dir}")

    # Create evaluation suite
    print("\n📝 Creating Evaluation Suite")
    print("-" * 70)

    eval_suite = EvalSuite(
        name="python-knowledge",
        prompts=(
            EvalPrompt(
                id="comp-01",
                category="python_basics",
                prompt_text="What is a list comprehension in Python?",
                expected_keywords=("comprehension", "list", "for", "in"),
            ),
            EvalPrompt(
                id="dec-01",
                category="python_basics",
                prompt_text="Explain Python decorators",
                expected_keywords=("decorator", "function", "@"),
            ),
            EvalPrompt(
                id="async-01",
                category="python_advanced",
                prompt_text="What is async/await in Python?",
                expected_keywords=("async", "await", "coroutine"),
            ),
            EvalPrompt(
                id="gen-01",
                category="python_advanced",
                prompt_text="Explain Python generators",
                expected_keywords=("generator", "yield", "lazy"),
            ),
            EvalPrompt(
                id="err-01",
                category="debugging",
                prompt_text="Why am I getting 'list index out of range'?",
                expected_keywords=("index", "range", "list", "length"),
            ),
            EvalPrompt(
                id="err-02",
                category="debugging",
                prompt_text="What causes KeyError in dictionary?",
                expected_keywords=("KeyError", "dictionary", "key", "exists"),
            ),
        ),
    )

    print(f"Created suite with {len(eval_suite.prompts)} prompts")
    print(f"  Python basics: {len(eval_suite.by_category('python_basics'))}")
    print(f"  Python advanced: {len(eval_suite.by_category('python_advanced'))}")
    print(f"  Debugging: {len(eval_suite.by_category('debugging'))}")

    all_reports = []

    # Baseline evaluation
    print("\n📊 Baseline Evaluation (Before Training)")
    print("-" * 70)

    baseline_config = EvalRunConfig(
        server_config=ServerConfig(model_path=model_path, port=8080),
        suite=eval_suite,
        workspace=Path.cwd(),
        manage_server=True,
    )

    try:
        print("Starting evaluation...")
        baseline_report = await run_evaluation(baseline_config)
        print(f"\n✅ Baseline Results:")
        print(f"   Overall Score: {baseline_report.overall_score:.1%}")
        print(f"   Success Rate: {baseline_report.success_rate:.1%}")
        all_reports.append(baseline_report)

        # Save report
        html = generate_eval_html_report(baseline_report, eval_suite)
        Path("eval_successful_baseline.html").write_text(html)
        print(f"   Report: eval_successful_baseline.html")

    except Exception as e:
        print(f"❌ Baseline evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Training
    print("\n🚀 Training LoRA Adapter")
    print("=" * 70)
    print("Training parameters:")
    print("  - 100 iterations (realistic)")
    print("  - 68 training examples (sufficient)")
    print("  - Learning rate: 1e-5 (conservative)")
    print("  - LoRA rank: 8 (standard)")
    print("  - Batch size: 4 (standard)")

    lora_config = LoRAConfig(
        base_model=model_path,
        data_directory=data_dir,
        output_directory=adapter_dir,
        num_iters=100,  # Realistic number
        batch_size=4,
        learning_rate=1e-5,
        lora_rank=8,
        lora_layers=16,
    )

    print(f"\nStarting training... (this may take 5-10 minutes)")
    print("-" * 70)

    try:
        result = await run_training_with_logs(lora_config)
        print(f"\n✅ Training Complete!")
        print(f"   Adapter: {result.adapter_path}")

        # Parse training logs
        logs = parse_training_log(result.output)
        if logs:
            print(f"\n📈 Training Progress:")
            print(f"   Total iterations: {len(logs)}")
            if logs[0].train_loss and logs[-1].train_loss:
                initial_loss = logs[0].train_loss
                final_loss = logs[-1].train_loss
                improvement = initial_loss - final_loss
                print(f"   Initial train loss: {initial_loss:.4f}")
                print(f"   Final train loss: {final_loss:.4f}")
                print(f"   Loss improvement: {improvement:.4f} ({improvement/initial_loss*100:.1f}%)")

    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Adapted evaluation
    print("\n📊 Adapted Evaluation (After Training)")
    print("-" * 70)

    adapted_config = EvalRunConfig(
        server_config=ServerConfig(
            model_path=model_path,
            port=8080,
            adapter_path=str(adapter_dir),
        ),
        suite=eval_suite,
        workspace=Path.cwd(),
        manage_server=True,
    )

    try:
        print("Starting evaluation with adapter...")
        adapted_report = await run_evaluation(adapted_config)
        print(f"\n✅ Adapted Results:")
        print(f"   Overall Score: {adapted_report.overall_score:.1%}")
        print(f"   Success Rate: {adapted_report.success_rate:.1%}")
        all_reports.append(adapted_report)

        # Save report
        html = generate_eval_html_report(adapted_report, eval_suite)
        Path("eval_successful_adapted.html").write_text(html)
        print(f"   Report: eval_successful_adapted.html")

    except Exception as e:
        print(f"❌ Adapted evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Comparison
    print("\n" + "=" * 70)
    print("📊 Final Results")
    print("=" * 70)

    baseline_score = baseline_report.overall_score
    adapted_score = adapted_report.overall_score
    improvement = adapted_score - baseline_score

    print(f"\nBaseline Score:  {baseline_score:.1%}")
    print(f"Adapted Score:   {adapted_score:.1%}")
    print(f"Improvement:     {improvement:+.1%}")

    if improvement > 0.05:  # >5% improvement
        print("\n🎉 SUCCESS - Training significantly improved performance!")
        print(f"   The adapter learned from the training data.")
    elif improvement > 0:
        print("\n✅ MODERATE - Training showed some improvement")
        print(f"   Consider more iterations or better data for larger gains.")
    elif improvement > -0.05:
        print("\n➡️  NEUTRAL - No significant change")
        print(f"   May need different hyperparameters or more diverse data.")
    else:
        print("\n⚠️  REGRESSION - Training made performance worse")
        print(f"   Learning rate may be too high or dataset has issues.")

    # Generate comparison report
    comparison_html = compare_reports(all_reports, eval_suite)
    Path("eval_successful_comparison.html").write_text(comparison_html)
    print(f"\n📊 Comparison report: eval_successful_comparison.html")

    print("\n" + "=" * 70)
    print("✅ Demonstration Complete!")
    print("=" * 70)

    print("\nGenerated files:")
    print(f"  Adapter: {adapter_dir}/")
    print("  Baseline: eval_successful_baseline.html")
    print("  Adapted: eval_successful_adapted.html")
    print("  Comparison: eval_successful_comparison.html")

    if improvement > 0:
        print("\n🎯 Infrastructure VALIDATED:")
        print("  ✅ Training works")
        print("  ✅ Adapters improve performance")
        print("  ✅ Evaluation measures improvements")
        print("  ✅ Ready for production use!")
    else:
        print("\n💡 Next steps:")
        print("  - Try higher learning rate (5e-5)")
        print("  - Try more iterations (200)")
        print("  - Try different LoRA rank (16)")
        print("  - Review training data quality")


if __name__ == "__main__":
    asyncio.run(main())
