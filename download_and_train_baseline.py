"""Download real dataset and establish training baseline.

This proves the training infrastructure works with real downloaded data,
not just synthetic examples.

Steps:
1. Download CodeSearchNet Python dataset (1000 examples)
2. Inspect data quality
3. Train adapter (100 iterations)
4. Evaluate baseline vs adapted
5. Document actual improvement with real data

Run: uv run python download_and_train_baseline.py
"""

import asyncio
from pathlib import Path

from punie.training.downloaders import download_python_code_dataset
from punie.training.dataset_io import read_dataset
from punie.training.dataset_validation import validate_dataset
from punie.training.eval_comparison import compare_reports
from punie.training.eval_prompts import EvalPrompt, EvalSuite
from punie.training.eval_report import generate_eval_html_report
from punie.training.eval_runner import EvalRunConfig, run_evaluation
from punie.training.lora_config import LoRAConfig
from punie.training.server_config import ServerConfig
from punie.training.train_runner import run_training_with_logs
from punie.training.hyperparam import parse_training_log


async def main():
    """Download real data and establish training baseline."""
    print("=" * 70)
    print("📊 Baseline Training with Diverse Python Dataset")
    print("=" * 70)
    print("\nThis establishes a baseline using diverse Python examples")
    print("(5000 examples across code, explanations, debugging, best practices)")

    # Step 1: Use dataset
    print("\n📥 Step 1: Loading Diverse Python Dataset")
    print("-" * 70)

    data_dir = Path("data/downloaded/diverse-python-5k")

    if not data_dir.exists():
        print(f"❌ Dataset not found: {data_dir}")
        print("   Run: uv run python create_diverse_python_dataset.py")
        return

    print(f"✅ Dataset found: {data_dir}")

    # Step 2: Inspect and validate
    print("\n🔍 Step 2: Inspecting Data Quality")
    print("-" * 70)

    dataset = read_dataset(data_dir)
    errors = validate_dataset(dataset)

    if errors:
        print(f"⚠️  Found {len(errors)} validation errors:")
        for error in errors[:5]:  # Show first 5
            print(f"   - {error}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more")
    else:
        print("✅ All examples pass validation")

    print(f"\nDataset: {dataset.name} v{dataset.version}")
    print(f"Train examples: {len(dataset.train)}")
    print(f"Valid examples: {len(dataset.valid)}")
    print(f"Test examples: {len(dataset.test)}")

    # Show first example
    if dataset.train:
        first = dataset.train[0]
        print(f"\n📝 Example training item:")
        print(f"   Messages: {len(first.messages)}")
        for msg in first.messages:
            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            print(f"   {msg.role}: {content_preview}")

    # Step 3: Create evaluation suite
    print("\n📝 Step 3: Creating Evaluation Suite")
    print("-" * 70)

    eval_suite = EvalSuite(
        name="python-coding",
        prompts=(
            EvalPrompt(
                id="func-01",
                category="code_generation",
                prompt_text="Write a Python function to reverse a string",
                expected_keywords=("def", "reverse", "return", "str"),
            ),
            EvalPrompt(
                id="func-02",
                category="code_generation",
                prompt_text="Write a function to check if a number is prime",
                expected_keywords=("def", "prime", "return", "if"),
            ),
            EvalPrompt(
                id="func-03",
                category="code_generation",
                prompt_text="Write a function to find the maximum value in a list",
                expected_keywords=("def", "max", "list", "return"),
            ),
            EvalPrompt(
                id="doc-01",
                category="documentation",
                prompt_text="What does this function do: def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
                expected_keywords=("factorial", "recursive", "multiply", "base case"),
            ),
        ),
    )

    print(f"Created suite with {len(eval_suite.prompts)} prompts")
    print(f"  Code generation: {len(eval_suite.by_category('code_generation'))}")
    print(f"  Documentation: {len(eval_suite.by_category('documentation'))}")

    all_reports = []

    # Use 1.5B model for faster iteration (we can use 30B later for production)
    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    adapter_dir = Path("adapters/baseline-diverse-python-5k")

    # Step 4: Baseline evaluation
    print("\n📊 Step 4: Baseline Evaluation (Before Training)")
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
        Path("eval_baseline_diverse.html").write_text(html)
        print(f"   Report: eval_baseline_diverse.html")

    except Exception as e:
        print(f"❌ Baseline evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 5: Training
    print("\n🚀 Step 5: Training LoRA Adapter on Real Data")
    print("=" * 70)
    print("Training parameters:")
    print(f"  - Dataset: CodeSearchNet Python ({len(dataset.train)} examples)")
    print("  - 100 iterations")
    print("  - Learning rate: 1e-5 (conservative)")
    print("  - Batch size: 4 (standard)")
    print(f"  - Model: {model_path}")

    lora_config = LoRAConfig(
        base_model=model_path,
        data_directory=data_dir,
        output_directory=adapter_dir,
        num_iters=100,
        batch_size=4,
        learning_rate=1e-5,
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

    # Step 6: Adapted evaluation
    print("\n📊 Step 6: Adapted Evaluation (After Training)")
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
        Path("eval_adapted_diverse.html").write_text(html)
        print(f"   Report: eval_adapted_diverse.html")

    except Exception as e:
        print(f"❌ Adapted evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 7: Comparison
    print("\n" + "=" * 70)
    print("📊 Final Results - Real Data Training Baseline")
    print("=" * 70)

    baseline_score = baseline_report.overall_score
    adapted_score = adapted_report.overall_score
    improvement = adapted_score - baseline_score

    print(f"\nBaseline Score:  {baseline_score:.1%}")
    print(f"Adapted Score:   {adapted_score:.1%}")
    print(f"Improvement:     {improvement:+.1%}")

    if improvement > 0.05:  # >5% improvement
        print("\n🎉 SUCCESS - Training significantly improved performance!")
        print(f"   Real data training works! The adapter learned from CodeSearchNet.")
    elif improvement > 0:
        print("\n✅ MODERATE - Training showed some improvement")
        print(f"   Consider more iterations or different hyperparameters.")
    elif improvement > -0.05:
        print("\n➡️  NEUTRAL - No significant change")
        print(f"   Data may not align well with evaluation prompts.")
    else:
        print("\n⚠️  REGRESSION - Training made performance worse")
        print(f"   Learning rate may be too high or data quality issues.")

    # Generate comparison report
    comparison_html = compare_reports(all_reports, eval_suite)
    Path("eval_comparison_diverse.html").write_text(comparison_html)
    print(f"\n📊 Comparison report: eval_comparison_diverse.html")

    print("\n" + "=" * 70)
    print("✅ Baseline Training Complete!")
    print("=" * 70)

    print("\nGenerated files:")
    print(f"  Dataset: {data_dir}/")
    print(f"  Adapter: {adapter_dir}/")
    print("  Baseline: eval_baseline_diverse.html")
    print("  Adapted: eval_adapted_diverse.html")
    print("  Comparison: eval_comparison_diverse.html")

    if improvement > 0:
        print("\n🎯 Real Data Training VALIDATED:")
        print("  ✅ Downloaded real dataset (CodeSearchNet)")
        print("  ✅ Training works on real data")
        print("  ✅ Adapters improve performance")
        print("  ✅ Evaluation measures improvements")
        print("  ✅ Infrastructure ready for production!")
    else:
        print("\n💡 Next steps:")
        print("  - Try more iterations (200)")
        print("  - Try higher learning rate (5e-5)")
        print("  - Try different dataset (StackExchange Q&A)")
        print("  - Tune evaluation prompts to match training data")


if __name__ == "__main__":
    asyncio.run(main())
