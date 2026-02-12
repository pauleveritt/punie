"""Hyperparameter tuning infrastructure."""

from dataclasses import dataclass
from pathlib import Path

from punie.training.eval_results import EvalReport
from punie.training.eval_runner import EvalRunConfig, run_evaluation
from punie.training.lora_config import LoRAConfig
from punie.training.server_config import ServerConfig
from punie.training.train_runner import run_training


@dataclass(frozen=True)
class HyperparamGrid:
    """Grid of hyperparameters to search.

    Each parameter is a tuple of values to try. The grid search will
    try all combinations.
    """

    learning_rates: tuple[float, ...] = (1e-5, 5e-5, 1e-4)
    lora_ranks: tuple[int, ...] = (4, 8, 16)
    num_iters: tuple[int, ...] = (50, 100, 200)
    batch_sizes: tuple[int, ...] = (2, 4)

    @property
    def total_combinations(self) -> int:
        """Total number of hyperparameter combinations."""
        return (
            len(self.learning_rates)
            * len(self.lora_ranks)
            * len(self.num_iters)
            * len(self.batch_sizes)
        )


@dataclass(frozen=True)
class HyperparamResult:
    """Result from a single hyperparameter configuration.

    Contains the config used, the trained adapter path, and the evaluation report.
    """

    config: LoRAConfig
    adapter_path: Path
    eval_report: EvalReport


async def run_hyperparam_search(
    grid: HyperparamGrid,
    base_model: str,
    data_directory: Path,
    adapters_directory: Path,
    eval_config: EvalRunConfig,
) -> tuple[HyperparamResult, ...]:
    """Run grid search over hyperparameters.

    For each combination in the grid:
    1. Train a LoRA adapter with those parameters
    2. Evaluate the adapter using eval_config
    3. Record the results

    Args:
        grid: Hyperparameter grid to search
        base_model: Base model path
        data_directory: Training data directory
        adapters_directory: Base directory for saving adapters
        eval_config: Evaluation configuration (model_path will be overridden)

    Returns:
        Tuple of HyperparamResult sorted by score (best first)
    """
    results = []
    combination_num = 0

    for lr in grid.learning_rates:
        for rank in grid.lora_ranks:
            for iters in grid.num_iters:
                for batch_size in grid.batch_sizes:
                    combination_num += 1

                    # Create unique adapter directory
                    adapter_name = f"lr{lr}_r{rank}_i{iters}_b{batch_size}"
                    adapter_path = adapters_directory / adapter_name

                    # Create training config
                    train_config = LoRAConfig(
                        base_model=base_model,
                        data_directory=data_directory,
                        output_directory=adapter_path,
                        num_iters=iters,
                        batch_size=batch_size,
                        learning_rate=lr,
                        lora_rank=rank,
                    )

                    # Train adapter
                    print(f"\n[{combination_num}/{grid.total_combinations}] Training: {adapter_name}")
                    print(f"  LR: {lr}, Rank: {rank}, Iters: {iters}, Batch: {batch_size}")

                    try:
                        await run_training(train_config)

                        # Evaluate adapter
                        print("  Evaluating...")
                        eval_config_with_adapter = EvalRunConfig(
                            server_config=ServerConfig(
                                model_path=base_model,
                                port=eval_config.server_config.port,
                                adapter_path=str(adapter_path),
                            ),
                            suite=eval_config.suite,
                            workspace=eval_config.workspace,
                            manage_server=eval_config.manage_server,
                        )

                        eval_report = await run_evaluation(eval_config_with_adapter)
                        print(f"  Score: {eval_report.overall_score:.1%}")

                        results.append(
                            HyperparamResult(
                                config=train_config,
                                adapter_path=adapter_path,
                                eval_report=eval_report,
                            )
                        )

                    except Exception as e:
                        print(f"  ❌ Failed: {e}")
                        continue

    # Sort by score (best first)
    sorted_results = sorted(results, key=lambda r: r.eval_report.overall_score, reverse=True)
    return tuple(sorted_results)


@dataclass(frozen=True)
class TrainingLog:
    """Single entry in training log.

    Records train and validation loss at a specific iteration.
    """

    iteration: int
    train_loss: float
    val_loss: float | None = None  # Validation loss (if available)


def parse_training_log(output: str) -> tuple[TrainingLog, ...]:
    """Parse mlx_lm.lora training output to extract loss values.

    mlx_lm.lora outputs lines like:
        Iter 10: Train loss 2.345, Val loss 2.567
        Iter 20: Train loss 2.123, Val loss 2.345

    Args:
        output: Training command stdout/stderr output

    Returns:
        Tuple of TrainingLog entries, one per iteration
    """
    logs = []

    for line in output.split("\n"):
        line = line.strip()

        # Look for iteration lines
        if "Iter" not in line or "loss" not in line:
            continue

        try:
            # Parse: "Iter 10: Train loss 2.345, Val loss 2.567"
            parts = line.split(":")
            if len(parts) < 2:
                continue

            # Extract iteration number
            iter_part = parts[0].strip()
            if not iter_part.startswith("Iter"):
                continue

            iteration = int(iter_part.split()[1])

            # Extract losses
            loss_part = parts[1].strip()
            train_loss = None
            val_loss = None

            # Parse train loss
            if "Train loss" in loss_part or "train loss" in loss_part:
                train_str = loss_part.split("Train loss")[-1] if "Train loss" in loss_part else loss_part.split("train loss")[-1]
                train_str = train_str.split(",")[0].strip()
                train_loss = float(train_str)

            # Parse val loss
            if "Val loss" in loss_part or "val loss" in loss_part:
                val_str = loss_part.split("Val loss")[-1] if "Val loss" in loss_part else loss_part.split("val loss")[-1]
                val_str = val_str.split(",")[0].strip()
                val_loss = float(val_str)

            if train_loss is not None:
                logs.append(TrainingLog(iteration=iteration, train_loss=train_loss, val_loss=val_loss))

        except (ValueError, IndexError):
            # Skip malformed lines
            continue

    return tuple(logs)
