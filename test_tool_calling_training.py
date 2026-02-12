"""Test tool-calling adapter training workflow.

This script demonstrates:
1. Using hand-authored tool-calling examples
2. Training a tool-calling adapter
3. Evaluating tool-calling performance
4. Comparing baseline vs adapted scores

Run: uv run python test_tool_calling_training.py
"""

import asyncio
from pathlib import Path

from punie.training.eval_comparison import compare_reports
from punie.training.eval_prompts import EvalPrompt, EvalSuite
from punie.training.eval_report import generate_eval_html_report
from punie.training.eval_runner import EvalRunConfig, run_evaluation
from punie.training.lora_config import LoRAConfig
from punie.training.server_config import ServerConfig
from punie.training.train_runner import run_training


async def main():
    """Run tool-calling training test."""
    print("=" * 70)
    print("🛠️  Tool-Calling Adapter Training Test")
    print("=" * 70)

    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    data_dir = Path("data/hand-authored/tool-calling")
    adapter_dir = Path("adapters/tool-calling-v1")

    # Check if data exists
    if not data_dir.exists():
        print(f"\n⚠️  Tool-calling data not found: {data_dir}")
        print("   Run: uv run python create_hand_authored_tool_examples.py")
        return

    # Create tool-calling evaluation suite
    print("\n📊 Creating Tool-Calling Evaluation Suite")
    print("-" * 70)

    eval_suite = EvalSuite(
        name="tool-calling",
        prompts=(
            EvalPrompt(
                id="tc-01",
                category="tool_calling",
                prompt_text="Read the file src/main.py and tell me what it does",
                expected_tool_calls=("read_file",),
                expected_keywords=("read", "file", "main.py"),
            ),
            EvalPrompt(
                id="tc-02",
                category="tool_calling",
                prompt_text="Create a new file called test.txt with the content 'Hello World'",
                expected_tool_calls=("write_file",),
                expected_keywords=("create", "test.txt", "Hello"),
            ),
            EvalPrompt(
                id="tc-03",
                category="tool_calling",
                prompt_text="Run the command 'pytest tests/' and tell me the results",
                expected_tool_calls=("run_command",),
                expected_keywords=("run", "pytest", "tests"),
            ),
            EvalPrompt(
                id="tc-04",
                category="multi_tool",
                prompt_text="Read config.py and then update the PORT to 3000",
                expected_tool_calls=("read_file", "write_file"),
                expected_keywords=("read", "update", "PORT", "3000"),
            ),
        ),
    )

    print(f"Created suite with {len(eval_suite.prompts)} prompts:")
    print(f"  - Tool calling: {len(eval_suite.by_category('tool_calling'))} prompts")
    print(f"  - Multi-tool: {len(eval_suite.by_category('multi_tool'))} prompts")

    # Baseline evaluation
    print("\n📊 Baseline Evaluation (Before Training)")
    print("-" * 70)

    baseline_config = EvalRunConfig(
        server_config=ServerConfig(model_path=model_path, port=8080),
        suite=eval_suite,
        workspace=Path.cwd(),
        manage_server=True,
    )

    all_reports = []

    try:
        baseline_report = await run_evaluation(baseline_config)
        print(f"✅ Baseline Score: {baseline_report.overall_score:.1%}")
        print(f"   Success Rate: {baseline_report.success_rate:.1%}")
        all_reports.append(baseline_report)

        # Save baseline report
        html = generate_eval_html_report(baseline_report, eval_suite)
        Path("eval_tool_calling_baseline.html").write_text(html)
        print("   Report: eval_tool_calling_baseline.html")

    except Exception as e:
        print(f"⚠️  Baseline evaluation failed: {e}")
        print("   Continuing with training...")
        baseline_report = None

    # Training
    print("\n🚀 Training Tool-Calling Adapter")
    print("-" * 70)
    print("Note: Using 20 iterations for demonstration")
    print("      Real training would use 100-200 iterations")

    lora_config = LoRAConfig(
        base_model=model_path,
        data_directory=data_dir,
        output_directory=adapter_dir,
        num_iters=20,  # More than previous demos since we have fewer examples
        batch_size=2,
        learning_rate=5e-5,  # Slightly higher LR for small dataset
    )

    try:
        await run_training(lora_config)
        print("✅ Training complete!")
        print(f"   Adapter: {adapter_dir}")

    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠️  Training failed. This might be due to:")
        print("   - Too few examples (need at least 8-10)")
        print("   - Model not downloaded yet")
        print("\nSkipping evaluation.")
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
        adapted_report = await run_evaluation(adapted_config)
        print(f"✅ Adapted Score: {adapted_report.overall_score:.1%}")
        print(f"   Success Rate: {adapted_report.success_rate:.1%}")
        all_reports.append(adapted_report)

        # Save adapted report
        html = generate_eval_html_report(adapted_report, eval_suite)
        Path("eval_tool_calling_adapted.html").write_text(html)
        print("   Report: eval_tool_calling_adapted.html")

    except Exception as e:
        print(f"❌ Adapted evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        adapted_report = None

    # Comparison
    print("\n📈 Results Comparison")
    print("=" * 70)

    if len(all_reports) >= 2:
        baseline_score = all_reports[0].overall_score
        adapted_score = all_reports[1].overall_score
        improvement = adapted_score - baseline_score

        print(f"Baseline Score:  {baseline_score:.1%}")
        print(f"Adapted Score:   {adapted_score:.1%}")
        print(f"Improvement:     {improvement:+.1%}")

        if improvement > 0:
            print("\n🎉 Tool-calling adapter improved performance!")
        elif improvement < 0:
            print("\n⚠️  Score decreased (might need more iterations or data)")
        else:
            print("\n➡️  No change (dataset might be too small)")

        # Generate comparison report
        comparison_html = compare_reports(all_reports, eval_suite)
        Path("eval_tool_calling_comparison.html").write_text(comparison_html)
        print("\n📊 Comparison report: eval_tool_calling_comparison.html")

    print("\n" + "=" * 70)
    print("✅ Tool-Calling Training Test Complete!")
    print("=" * 70)

    print("\nGenerated files:")
    print(f"  Adapter: {adapter_dir}/")
    if baseline_report:
        print("  Baseline: eval_tool_calling_baseline.html")
    if adapted_report:
        print("  Adapted: eval_tool_calling_adapted.html")
    if len(all_reports) >= 2:
        print("  Comparison: eval_tool_calling_comparison.html")

    print("\n💡 Next steps:")
    print("  - Try merging with general data for better baseline")
    print("  - Increase iterations (100-200) for production training")
    print("  - Add more hand-authored examples for better coverage")
    print("  - Test with real Punie tool calls")


if __name__ == "__main__":
    asyncio.run(main())
