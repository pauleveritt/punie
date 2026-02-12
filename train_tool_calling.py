"""Train on tool-calling dataset and evaluate improvement.

This trains on synthetic tool-calling examples and evaluates with
aligned prompts to demonstrate actual improvement.

Run: uv run python train_tool_calling.py
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
    """Train on tool-calling data and evaluate."""
    print("=" * 70)
    print("🔧 Tool-Calling Adapter Training")
    print("=" * 70)
    print("\nTraining on synthetic tool-calling examples to improve")
    print("Punie's ability to use tools correctly.")

    data_dir = Path("data/synthetic/tool-calling")
    adapter_dir = Path("adapters/tool-calling-synthetic")

    if not data_dir.exists():
        print(f"\n❌ Dataset not found: {data_dir}")
        print("   Run: uv run python create_tool_calling_dataset.py")
        return

    # Load and inspect dataset
    print(f"\n📊 Loading Dataset: {data_dir}")
    print("-" * 70)

    dataset = read_dataset(data_dir)
    print(f"✅ Dataset loaded")
    print(f"   Train: {len(dataset.train)} examples")
    print(f"   Valid: {len(dataset.valid)} examples")
    print(f"   Test: {len(dataset.test)} examples")

    # Create evaluation suite aligned with training data
    print("\n📝 Creating Tool-Calling Evaluation Suite")
    print("-" * 70)

    eval_suite = EvalSuite(
        name="tool-calling",
        prompts=(
            # Read file scenarios
            EvalPrompt(
                id="read-01",
                category="read_file",
                prompt_text="Read the main.py file",
                expected_keywords=("read_file", "main.py", "tool"),
            ),
            EvalPrompt(
                id="read-02",
                category="read_file",
                prompt_text="Show me the contents of config.json",
                expected_keywords=("read_file", "config.json", "tool"),
            ),
            # Write file scenarios
            EvalPrompt(
                id="write-01",
                category="write_file",
                prompt_text="Create a hello.py file with a print statement",
                expected_keywords=("write_file", "hello.py", "tool"),
            ),
            EvalPrompt(
                id="write-02",
                category="write_file",
                prompt_text="Make a README file",
                expected_keywords=("write_file", "README", "tool"),
            ),
            # Run command scenarios
            EvalPrompt(
                id="cmd-01",
                category="run_command",
                prompt_text="Run the tests",
                expected_keywords=("run_command", "pytest", "tool"),
            ),
            EvalPrompt(
                id="cmd-02",
                category="run_command",
                prompt_text="Check git status",
                expected_keywords=("run_command", "git", "tool"),
            ),
        ),
    )

    print(f"Created suite with {len(eval_suite.prompts)} prompts")
    print(f"  read_file: {len(eval_suite.by_category('read_file'))}")
    print(f"  write_file: {len(eval_suite.by_category('write_file'))}")
    print(f"  run_command: {len(eval_suite.by_category('run_command'))}")

    all_reports = []

    # Use 1.5B model for faster iteration
    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"

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

        html = generate_eval_html_report(baseline_report, eval_suite)
        Path("eval_tool_calling_baseline.html").write_text(html)
        print(f"   Report: eval_tool_calling_baseline.html")

    except Exception as e:
        print(f"❌ Baseline evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Training
    print("\n🚀 Training Tool-Calling Adapter")
    print("=" * 70)
    print("Training parameters:")
    print(f"  - Dataset: {len(dataset.train)} examples")
    print("  - 100 iterations")
    print("  - Learning rate: 1e-5")
    print("  - Batch size: 4")

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

        html = generate_eval_html_report(adapted_report, eval_suite)
        Path("eval_tool_calling_adapted.html").write_text(html)
        print(f"   Report: eval_tool_calling_adapted.html")

    except Exception as e:
        print(f"❌ Adapted evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Comparison
    print("\n" + "=" * 70)
    print("📊 Final Results - Tool-Calling Training")
    print("=" * 70)

    baseline_score = baseline_report.overall_score
    adapted_score = adapted_report.overall_score
    improvement = adapted_score - baseline_score

    print(f"\nBaseline Score:  {baseline_score:.1%}")
    print(f"Adapted Score:   {adapted_score:.1%}")
    print(f"Improvement:     {improvement:+.1%}")

    if improvement > 0.05:
        print("\n🎉 SUCCESS - Adapter significantly improved tool calling!")
        print(f"   Model learned to use tools correctly.")
    elif improvement > 0:
        print("\n✅ MODERATE - Some improvement in tool calling")
        print(f"   Consider more iterations or examples.")
    elif improvement > -0.05:
        print("\n➡️  NEUTRAL - No significant change")
        print(f"   May need better training data or evaluation.")
    else:
        print("\n⚠️  REGRESSION - Performance decreased")
        print(f"   Check hyperparameters or data quality.")

    comparison_html = compare_reports(all_reports, eval_suite)
    Path("eval_tool_calling_comparison.html").write_text(comparison_html)
    print(f"\n📊 Comparison report: eval_tool_calling_comparison.html")

    print("\n" + "=" * 70)
    print("✅ Tool-Calling Training Complete!")
    print("=" * 70)

    print("\nGenerated files:")
    print(f"  Dataset: {data_dir}/")
    print(f"  Adapter: {adapter_dir}/")
    print("  Baseline: eval_tool_calling_baseline.html")
    print("  Adapted: eval_tool_calling_adapted.html")
    print("  Comparison: eval_tool_calling_comparison.html")

    if improvement > 0:
        print("\n🎯 Tool-Calling Adapter Ready:")
        print("  ✅ Training improved tool-calling performance")
        print("  ✅ Ready to use with Punie agent")
        print("\n💡 To use this adapter with Punie:")
        print("  mlx_lm.server --model " + model_path)
        print(f"    --adapter-path {adapter_dir} --port 8080")
        print("  punie serve --model local:http://localhost:8080/v1/default")


if __name__ == "__main__":
    asyncio.run(main())
