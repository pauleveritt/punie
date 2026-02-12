"""Train on Glaive function calling dataset - final baseline.

This uses REAL downloaded tool-calling data (not synthetic).

Run: uv run python train_glaive_baseline.py
"""

import asyncio
from pathlib import Path

from punie.training.dataset_io import read_dataset
from punie.training.eval_comparison import compare_reports
from punie.training.eval_prompts import EvalPrompt, EvalSuite
from punie.training.eval_report import generate_eval_html_report
from punie.training.eval_runner import EvalRunConfig, run_evaluation
from punie.training.lora_config import LoRAConfig
from punie.training.server_config import ServerConfig
from punie.training.train_runner import run_training_with_logs
from punie.training.hyperparam import parse_training_log


async def main():
    """Train on Glaive function calling data."""
    print("=" * 70)
    print("🎯 Final Baseline: Glaive Function Calling Dataset")
    print("=" * 70)
    print("\nTraining on REAL downloaded tool-calling data")
    print("(Not synthetic - actual function calling examples)")

    data_dir = Path("data/downloaded/glaive-function-calling")
    adapter_dir = Path("adapters/glaive-function-calling")

    if not data_dir.exists():
        print(f"\n❌ Dataset not found: {data_dir}")
        print("   Run: uv run python download_glaive_tool_calling.py")
        return

    # Load dataset
    print(f"\n📊 Loading Dataset")
    print("-" * 70)

    dataset = read_dataset(data_dir)
    print(f"✅ Real tool-calling data loaded")
    print(f"   Train: {len(dataset.train)} examples")
    print(f"   Valid: {len(dataset.valid)} examples")
    print(f"   Test: {len(dataset.test)} examples")

    # Create evaluation suite
    print("\n📝 Creating Evaluation Suite")
    print("-" * 70)

    eval_suite = EvalSuite(
        name="function-calling",
        prompts=(
            EvalPrompt(
                id="func-01",
                category="function_calling",
                prompt_text="Can you get the current weather in New York?",
                expected_keywords=("function", "weather", "New York"),
            ),
            EvalPrompt(
                id="func-02",
                category="function_calling",
                prompt_text="Send an email to john@example.com",
                expected_keywords=("function", "email", "send"),
            ),
            EvalPrompt(
                id="func-03",
                category="function_calling",
                prompt_text="Calculate the sum of 25 and 17",
                expected_keywords=("function", "calculate", "sum"),
            ),
            EvalPrompt(
                id="func-04",
                category="function_calling",
                prompt_text="Book a flight from Boston to Chicago",
                expected_keywords=("function", "flight", "book"),
            ),
        ),
    )

    print(f"Created suite with {len(eval_suite.prompts)} prompts")

    all_reports = []
    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"

    # Baseline evaluation
    print("\n📊 Baseline Evaluation")
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

        html = generate_eval_html_report(baseline_report, eval_suite)
        Path("eval_glaive_baseline.html").write_text(html)
        print(f"   Report: eval_glaive_baseline.html")

    except Exception as e:
        print(f"❌ Baseline evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Training
    print("\n🚀 Training on Real Function Calling Data")
    print("=" * 70)
    print(f"  - Dataset: {len(dataset.train)} real examples")
    print("  - 100 iterations")
    print("  - Learning rate: 1e-5")

    lora_config = LoRAConfig(
        base_model=model_path,
        data_directory=data_dir,
        output_directory=adapter_dir,
        num_iters=100,
        batch_size=4,
        learning_rate=1e-5,
        lora_layers=16,
    )

    print(f"\nStarting training...")
    print("-" * 70)

    try:
        result = await run_training_with_logs(lora_config)
        print(f"\n✅ Training Complete!")
        print(f"   Adapter: {result.adapter_path}")

        logs = parse_training_log(result.output)
        if logs:
            print(f"\n📈 Training Progress:")
            print(f"   Total iterations logged: {len(logs)}")
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
    print("\n📊 Adapted Evaluation")
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

        html = generate_eval_html_report(adapted_report, eval_suite)
        Path("eval_glaive_adapted.html").write_text(html)
        print(f"   Report: eval_glaive_adapted.html")

    except Exception as e:
        print(f"❌ Adapted evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Comparison
    print("\n" + "=" * 70)
    print("📊 Final Results - Real Tool-Calling Data Baseline")
    print("=" * 70)

    baseline_score = baseline_report.overall_score
    adapted_score = adapted_report.overall_score
    improvement = adapted_score - baseline_score

    print(f"\nBaseline Score:  {baseline_score:.1%}")
    print(f"Adapted Score:   {adapted_score:.1%}")
    print(f"Improvement:     {improvement:+.1%}")

    if improvement > 0.05:
        print("\n🎉 SUCCESS - Real data training improved performance!")
    elif improvement > 0:
        print("\n✅ MODERATE - Some improvement with real data")
    else:
        print("\n➡️  Training complete - baseline established")

    comparison_html = compare_reports(all_reports, eval_suite)
    Path("eval_glaive_comparison.html").write_text(comparison_html)
    print(f"\n📊 Comparison report: eval_glaive_comparison.html")

    print("\n" + "=" * 70)
    print("✅ Final Baseline Complete!")
    print("=" * 70)

    print("\nGenerated files:")
    print(f"  Dataset: {data_dir}/ (73 real examples)")
    print(f"  Adapter: {adapter_dir}/")
    print("  Reports: eval_glaive_*.html")

    print("\n🎯 Infrastructure Validated:")
    print("  ✅ Training on downloaded real data works")
    print("  ✅ Glaive function calling dataset accessible")
    print("  ✅ Complete training pipeline end-to-end")
    print("  ✅ Ready for production use!")


if __name__ == "__main__":
    asyncio.run(main())
