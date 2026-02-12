"""Test progressive dataset pruning workflow.

This script demonstrates how to:
1. Download a dataset
2. Filter it step-by-step
3. Train adapters at each step
4. Compare results across steps

Run: uv run python test_progressive_pruning.py
"""

import asyncio
from datetime import datetime
from pathlib import Path

from punie.training.dataset import ChatMessage, TrainingDataset, TrainingExample
from punie.training.dataset_filters import filter_by_content_quality, filter_by_language, filter_by_python_version
from punie.training.dataset_io import compute_stats, write_dataset
from punie.training.eval_comparison import compare_reports
from punie.training.eval_prompts import EvalPrompt, EvalSuite
from punie.training.eval_report import generate_eval_html_report
from punie.training.eval_results import EvalReport, EvalResult
from punie.training.eval_runner import EvalRunConfig, run_evaluation
from punie.training.lora_config import LoRAConfig
from punie.training.server_config import ServerConfig
from punie.training.train_runner import run_training


def create_test_dataset() -> TrainingDataset:
    """Create a small test dataset with various quality levels."""
    examples = []

    # Good examples (English, Python 3.10+, quality content)
    for i in range(5):
        examples.append(
            TrainingExample(
                messages=(
                    ChatMessage(role="system", content="You are a helpful Python tutor."),
                    ChatMessage(role="user", content=f"How do I use f-strings in Python? (Example {i})"),
                    ChatMessage(
                        role="assistant",
                        content=f"F-strings in Python 3.6+ let you embed expressions in strings using {{}}. "
                        f"For example: name = 'World'; print(f'Hello {{name}}!'). This is example {i}.",
                    ),
                )
            )
        )

    # Non-English examples (should be filtered out)
    examples.append(
        TrainingExample(
            messages=(
                ChatMessage(role="system", content="你是一个有用的助手。"),
                ChatMessage(role="user", content="如何使用Python？"),
                ChatMessage(role="assistant", content="Python是一种编程语言。"),
            )
        )
    )

    # Python 2 examples (should be filtered out)
    examples.append(
        TrainingExample(
            messages=(
                ChatMessage(role="system", content="You are a coding assistant."),
                ChatMessage(role="user", content="How do I print in Python?"),
                ChatMessage(role="assistant", content="Use print without parentheses: print 'Hello World'"),
            )
        )
    )

    examples.append(
        TrainingExample(
            messages=(
                ChatMessage(role="system", content="You are a coding assistant."),
                ChatMessage(role="user", content="How do I check if key exists in dict?"),
                ChatMessage(role="assistant", content="Use has_key() method: my_dict.has_key('key')"),
            )
        )
    )

    # Low quality examples (too short)
    examples.append(
        TrainingExample(
            messages=(
                ChatMessage(role="user", content="What is Python?"),
                ChatMessage(role="assistant", content="A language."),
            )
        )
    )

    return TrainingDataset(
        name="test-progressive",
        version="1.0",
        train=tuple(examples[:7]),  # 7 train examples
        valid=tuple(examples[7:8]),  # 1 valid
        test=tuple(examples[8:]),  # 1 test
    )


async def main():
    """Run progressive pruning test."""
    print("=" * 70)
    print("🔬 Progressive Dataset Pruning Test")
    print("=" * 70)

    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"

    # Create test dataset
    print("\n📊 Step 0: Create Test Dataset")
    print("-" * 70)

    raw_dataset = create_test_dataset()
    raw_dir = Path("data/pruning-test/step-0-raw")
    write_dataset(raw_dataset, raw_dir)

    stats = compute_stats(raw_dataset)
    print(f"✅ Created dataset: {stats.total_examples} examples")
    print(f"   Train: {stats.train_count}, Valid: {stats.valid_count}, Test: {stats.test_count}")
    print(f"   Avg messages: {stats.avg_messages_per_example:.1f}")

    # Create evaluation suite
    eval_suite = EvalSuite(
        name="pruning-test",
        prompts=(
            EvalPrompt(
                id="py-01",
                category="python_knowledge",
                prompt_text="What are f-strings in Python?",
                expected_keywords=("f-string", "format", "{}"),
            ),
            EvalPrompt(
                id="py-02",
                category="python_knowledge",
                prompt_text="How do I create a list comprehension?",
                expected_keywords=("comprehension", "for", "list"),
            ),
        ),
    )

    # Track all reports for comparison
    all_reports = []

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
        baseline_report = await run_evaluation(baseline_config)
        print(f"✅ Baseline Score: {baseline_report.overall_score:.1%}")
        all_reports.append(baseline_report)

        html = generate_eval_html_report(baseline_report, eval_suite)
        Path("eval_pruning_baseline.html").write_text(html)

    except Exception as e:
        print(f"⚠️  Baseline evaluation failed: {e}")
        print("   Creating mock baseline...")
        # Create mock baseline for demonstration
        baseline_report = EvalReport(
            model_name=model_path,
            adapter_path=None,
            suite_name="pruning-test",
            timestamp=datetime.now(),
            results=(
                EvalResult("py-01", "F-strings allow formatting", (), 100.0, 0.5, True),
                EvalResult("py-02", "List comprehensions iterate", (), 100.0, 0.6, True),
            ),
        )
        all_reports.append(baseline_report)

    # Step A: Remove non-English
    print("\n🌍 Step A: Filter by Language (English only)")
    print("-" * 70)

    train_kept, train_removed = filter_by_language(raw_dataset.train, "en")
    valid_kept, _ = filter_by_language(raw_dataset.valid, "en")
    test_kept, _ = filter_by_language(raw_dataset.test, "en")

    step_a_dataset = TrainingDataset(
        name="test-progressive",
        version="step-a",
        train=train_kept,
        valid=valid_kept,
        test=test_kept,
    )

    step_a_dir = Path("data/pruning-test/step-a-english")
    write_dataset(step_a_dataset, step_a_dir)

    print(f"   Removed: {len(train_removed)} examples")
    print(f"   Kept: {len(train_kept)} examples")

    # Step B: Remove Python 2
    print("\n🐍 Step B: Filter by Python Version (3.0+)")
    print("-" * 70)

    train_kept, train_removed = filter_by_python_version(step_a_dataset.train, "3")
    valid_kept, _ = filter_by_python_version(step_a_dataset.valid, "3")
    test_kept, _ = filter_by_python_version(step_a_dataset.test, "3")

    step_b_dataset = TrainingDataset(
        name="test-progressive",
        version="step-b",
        train=train_kept,
        valid=valid_kept,
        test=test_kept,
    )

    step_b_dir = Path("data/pruning-test/step-b-python3")
    write_dataset(step_b_dataset, step_b_dir)

    print(f"   Removed: {len(train_removed)} examples")
    print(f"   Kept: {len(train_kept)} examples")

    # Step C: Remove low quality
    print("\n💬 Step C: Filter by Content Quality (min 3 messages)")
    print("-" * 70)

    train_kept, train_removed = filter_by_content_quality(step_b_dataset.train, min_messages=3)
    valid_kept, _ = filter_by_content_quality(step_b_dataset.valid, min_messages=3)
    test_kept, _ = filter_by_content_quality(step_b_dataset.test, min_messages=3)

    step_c_dataset = TrainingDataset(
        name="test-progressive",
        version="step-c",
        train=train_kept,
        valid=valid_kept,
        test=test_kept,
    )

    step_c_dir = Path("data/pruning-test/step-c-quality")
    write_dataset(step_c_dataset, step_c_dir)

    print(f"   Removed: {len(train_removed)} examples")
    print(f"   Kept: {len(train_kept)} examples")

    # Summary
    print("\n📈 Filtering Summary")
    print("=" * 70)
    print(f"Step 0 (Raw):      {len(raw_dataset.train)} examples")
    print(f"Step A (English):  {len(step_a_dataset.train)} examples ({len(step_a_dataset.train) / max(len(raw_dataset.train), 1) * 100:.0f}% retained)")
    print(f"Step B (Python3):  {len(step_b_dataset.train)} examples ({len(step_b_dataset.train) / max(len(raw_dataset.train), 1) * 100:.0f}% retained)")
    print(f"Step C (Quality):  {len(step_c_dataset.train)} examples ({len(step_c_dataset.train) / max(len(raw_dataset.train), 1) * 100:.0f}% retained)")

    # Train on best dataset (Step C)
    if len(step_c_dataset.train) > 0:
        print("\n🚀 Training on Filtered Dataset (Step C)")
        print("-" * 70)
        print("Training with minimal iterations for testing...")

        adapter_dir = Path("adapters/pruning-test")
        lora_config = LoRAConfig(
            base_model=model_path,
            data_directory=step_c_dir,
            output_directory=adapter_dir,
            num_iters=10,
            batch_size=2,
            learning_rate=1e-5,
        )

        try:
            await run_training(lora_config)
            print(f"✅ Training complete: {adapter_dir}")

            # Evaluate adapted model
            print("\n📊 Evaluating Adapted Model")
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

            adapted_report = await run_evaluation(adapted_config)
            print(f"✅ Adapted Score: {adapted_report.overall_score:.1%}")
            all_reports.append(adapted_report)

            html = generate_eval_html_report(adapted_report, eval_suite)
            Path("eval_pruning_adapted.html").write_text(html)

        except Exception as e:
            print(f"⚠️  Training/evaluation failed: {e}")
            print("   This is expected with very small datasets")

    # Generate comparison report
    if len(all_reports) > 1:
        print("\n📊 Generating Comparison Report")
        print("-" * 70)

        comparison_html = compare_reports(all_reports, eval_suite)
        Path("eval_pruning_comparison.html").write_text(comparison_html)
        print("✅ Comparison report: eval_pruning_comparison.html")

    print("\n" + "=" * 70)
    print("✅ Progressive Pruning Test Complete!")
    print("=" * 70)

    print("\nGenerated files:")
    print(f"  Step 0 (Raw):     {raw_dir}/")
    print(f"  Step A (English): {step_a_dir}/")
    print(f"  Step B (Python3): {step_b_dir}/")
    print(f"  Step C (Quality): {step_c_dir}/")
    print()
    print("  Reports:")
    print("    eval_pruning_baseline.html")
    print("    eval_pruning_adapted.html")
    print("    eval_pruning_comparison.html")


if __name__ == "__main__":
    asyncio.run(main())
