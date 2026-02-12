"""Test complete training pipeline end-to-end.

This script demonstrates the full workflow:
1. Generate sample dataset
2. Validate it
3. Train LoRA adapter (small number of iterations for testing)
4. Evaluate both base model and adapted model
5. Compare results

Run: uv run python test_full_training_pipeline.py
"""

import asyncio
from datetime import datetime
from pathlib import Path

from punie.training.dataset_io import read_dataset
from punie.training.dataset_validation import validate_dataset
from punie.training.downloaders import download_sample_dataset
from punie.training.eval_prompts import EvalPrompt, EvalSuite
from punie.training.eval_report import generate_eval_html_report
from punie.training.eval_runner import EvalRunConfig, run_evaluation
from punie.training.lora_config import LoRAConfig
from punie.training.server_config import ServerConfig
from punie.training.train_runner import run_training


async def main():
    """Run complete training pipeline test."""
    print("=" * 70)
    print("🧪 Complete Training Pipeline Test")
    print("=" * 70)

    # Configuration
    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    data_dir = Path("data/pipeline-test")
    adapter_dir = Path("adapters/pipeline-test")

    # Step 1: Generate sample dataset
    print("\n📥 Step 1: Generate Sample Dataset")
    print("-" * 70)

    if data_dir.exists():
        print(f"Dataset already exists at {data_dir}, skipping generation")
    else:
        stats = download_sample_dataset(data_dir, max_examples=50)
        print(f"✅ Generated {stats.total_examples} examples")
        print(f"   Train: {stats.train_count}, Valid: {stats.valid_count}, Test: {stats.test_count}")

    # Step 2: Validate dataset
    print("\n✅ Step 2: Validate Dataset")
    print("-" * 70)

    dataset = read_dataset(data_dir)
    errors = validate_dataset(dataset)

    if errors:
        print(f"❌ Validation found {len(errors)} errors:")
        for error in errors[:5]:
            print(f"   • {error}")
        return

    print(f"✅ Dataset is valid!")
    print(f"   {len(dataset.train)} train, {len(dataset.valid)} valid, {len(dataset.test)} test")

    # Step 3: Baseline evaluation (before training)
    print("\n📊 Step 3: Baseline Evaluation (Before Training)")
    print("-" * 70)

    # Create simple eval suite
    eval_suite = EvalSuite(
        name="pipeline-test",
        prompts=(
            EvalPrompt(
                id="python-01",
                category="python_knowledge",
                prompt_text="What is a Python function?",
                expected_keywords=("def", "function", "return"),
            ),
            EvalPrompt(
                id="python-02",
                category="python_knowledge",
                prompt_text="How do I create a list in Python?",
                expected_keywords=("list", "[]", "brackets"),
            ),
        ),
    )

    print(f"Running evaluation with {len(eval_suite.prompts)} prompts...")

    baseline_config = EvalRunConfig(
        server_config=ServerConfig(model_path=model_path, port=8080),
        suite=eval_suite,
        workspace=Path.cwd(),
        manage_server=True,
    )

    try:
        baseline_report = await run_evaluation(baseline_config)
        print(f"✅ Baseline Score: {baseline_report.overall_score:.1%}")
        print(f"   Success Rate: {baseline_report.success_rate:.1%}")

        # Save baseline report
        html = generate_eval_html_report(baseline_report, eval_suite)
        Path("eval_baseline_pipeline.html").write_text(html)
        print(f"   Report: eval_baseline_pipeline.html")

    except Exception as e:
        print(f"⚠️  Baseline evaluation failed: {e}")
        print("   Continuing with training...")
        baseline_report = None

    # Step 4: Train LoRA adapter
    print("\n🚀 Step 4: Train LoRA Adapter")
    print("-" * 70)
    print("Training with VERY small number of iterations (10) for quick testing")
    print("Real training would use 100-1000+ iterations")

    lora_config = LoRAConfig(
        base_model=model_path,
        data_directory=data_dir,
        output_directory=adapter_dir,
        num_iters=10,  # Very small for testing
        batch_size=2,  # Small batch for testing
        learning_rate=1e-5,
    )

    try:
        adapter_path = await run_training(lora_config)
        print(f"✅ Training complete!")
        print(f"   Adapter: {adapter_path}")

    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠️  Training failed. This might be due to:")
        print("   - Model not downloaded yet (first run takes longer)")
        print("   - mlx_lm.lora command needs different arguments")
        print("   - Dataset format issue")
        print("\nSkipping remaining steps.")
        return

    # Step 5: Evaluation with adapter
    print("\n📊 Step 5: Evaluation with Adapter (After Training)")
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

        # Save adapted report
        html = generate_eval_html_report(adapted_report, eval_suite)
        Path("eval_adapted_pipeline.html").write_text(html)
        print(f"   Report: eval_adapted_pipeline.html")

    except Exception as e:
        print(f"❌ Adapted evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        adapted_report = None

    # Step 6: Compare results
    print("\n📈 Step 6: Compare Results")
    print("=" * 70)

    if baseline_report and adapted_report:
        baseline_score = baseline_report.overall_score
        adapted_score = adapted_report.overall_score
        improvement = adapted_score - baseline_score

        print(f"Baseline Score:  {baseline_score:.1%}")
        print(f"Adapted Score:   {adapted_score:.1%}")
        print(f"Improvement:     {improvement:+.1%}")

        if improvement > 0:
            print(f"\n🎉 Training improved the model!")
        elif improvement < 0:
            print(f"\n⚠️  Score decreased (might need more training iterations)")
        else:
            print(f"\n➡️  No change (dataset might be too small or too few iterations)")

        print(f"\n💡 Notes:")
        print(f"   - This used only {lora_config.num_iters} training iterations (very few!)")
        print(f"   - Dataset has only {len(dataset.train)} training examples")
        print(f"   - Real training typically uses 100-1000+ iterations")
        print(f"   - Real datasets have 1000s-10000s of examples")

    else:
        print("⚠️  Could not compare - one or both evaluations failed")

    print("\n" + "=" * 70)
    print("✅ Pipeline Test Complete!")
    print("=" * 70)

    print("\nGenerated files:")
    print(f"  Data:     {data_dir}/")
    print(f"  Adapter:  {adapter_dir}/")
    if baseline_report:
        print(f"  Baseline: eval_baseline_pipeline.html")
    if adapted_report:
        print(f"  Adapted:  eval_adapted_pipeline.html")


if __name__ == "__main__":
    asyncio.run(main())
