"""Test hyperparameter tuning workflow.

This script demonstrates how to:
1. Define a hyperparameter grid
2. Run grid search (train + evaluate for each combination)
3. Find the best configuration
4. Parse training logs for loss curves

Run: uv run python test_hyperparam_tuning.py
"""

import asyncio
from pathlib import Path

from punie.training.eval_suites import create_baseline_suite
from punie.training.eval_runner import EvalRunConfig
from punie.training.hyperparam import HyperparamGrid, run_hyperparam_search
from punie.training.server_config import ServerConfig


async def main():
    """Run hyperparameter tuning test."""
    print("=" * 70)
    print("🔬 Hyperparameter Tuning Test")
    print("=" * 70)

    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    data_dir = Path("data/workflow-test")
    adapters_dir = Path("adapters/hyperparam-search")

    # Check if data exists
    if not data_dir.exists():
        print(f"\n⚠️  Data directory not found: {data_dir}")
        print("   Please run the progressive pruning demo first:")
        print("   uv run python test_progressive_pruning.py")
        return

    # Define a SMALL grid for testing (normally would be larger)
    print("\n📊 Hyperparameter Grid")
    print("-" * 70)

    grid = HyperparamGrid(
        learning_rates=(1e-5, 5e-5),  # Try 2 learning rates
        lora_ranks=(4, 8),  # Try 2 LoRA ranks
        num_iters=(10,),  # Very small for testing (normally 50-200)
        batch_sizes=(2,),  # Single batch size
    )

    print(f"Learning rates: {grid.learning_rates}")
    print(f"LoRA ranks: {grid.lora_ranks}")
    print(f"Iterations: {grid.num_iters}")
    print(f"Batch sizes: {grid.batch_sizes}")
    print(f"\nTotal combinations: {grid.total_combinations}")
    print("\n💡 Note: Using minimal iterations (10) for testing.")
    print("   Real hyperparameter search would use 50-200 iterations.")

    # Create evaluation config
    eval_suite = create_baseline_suite()
    eval_config = EvalRunConfig(
        server_config=ServerConfig(model_path=model_path, port=8080),
        suite=eval_suite,
        workspace=Path.cwd(),
        manage_server=True,
    )

    # Run grid search
    print("\n🚀 Running Grid Search")
    print("=" * 70)

    try:
        results = await run_hyperparam_search(
            grid=grid,
            base_model=model_path,
            data_directory=data_dir,
            adapters_directory=adapters_dir,
            eval_config=eval_config,
        )

        # Display results
        print("\n📈 Results (sorted by score)")
        print("=" * 70)

        for i, result in enumerate(results, 1):
            config = result.config
            score = result.eval_report.overall_score
            success_rate = result.eval_report.success_rate

            print(f"\n{i}. Score: {score:.1%} (Success: {success_rate:.1%})")
            print(f"   LR: {config.learning_rate}, Rank: {config.lora_rank}, "
                  f"Iters: {config.num_iters}, Batch: {config.batch_size}")
            print(f"   Adapter: {result.adapter_path}")

        # Best configuration
        if results:
            print("\n🏆 Best Configuration")
            print("-" * 70)
            best = results[0]
            print(f"Score: {best.eval_report.overall_score:.1%}")
            print(f"Learning rate: {best.config.learning_rate}")
            print(f"LoRA rank: {best.config.lora_rank}")
            print(f"Iterations: {best.config.num_iters}")
            print(f"Batch size: {best.config.batch_size}")
            print(f"Adapter: {best.adapter_path}")

            # Category breakdown
            print("\n📊 Category Scores:")
            # Note: Would need to pass category_results here in real use
            # For now, just show overall
            print(f"   Overall: {best.eval_report.overall_score:.1%}")
            print(f"   Success rate: {best.eval_report.success_rate:.1%}")

        else:
            print("\n⚠️  No successful training runs")

    except Exception as e:
        print(f"\n❌ Grid search failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 70)
    print("✅ Hyperparameter Tuning Test Complete!")
    print("=" * 70)

    if results:
        print(f"\nTested {len(results)}/{grid.total_combinations} configurations successfully")
        print(f"Best score: {results[0].eval_report.overall_score:.1%}")
        print(f"\nAdapters saved to: {adapters_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
