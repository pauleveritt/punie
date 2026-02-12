"""LoRA training runner."""

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path

from punie.training.lora_config import LoRAConfig


@dataclass(frozen=True)
class TrainingResult:
    """Result from running LoRA training.

    Contains the adapter path and training output for log parsing.
    """

    adapter_path: Path
    output: str  # Combined stdout + stderr for log parsing


def build_train_command(config: LoRAConfig) -> list[str]:
    """Build mlx_lm lora training command.

    Pure function - easily tested without running actual training.

    Args:
        config: LoRA training configuration

    Returns:
        Command as list of strings
    """
    cmd = [
        "python",
        "-m",
        "mlx_lm",
        "lora",
        "--model",
        config.base_model,
        "--train",  # Required flag to actually train
        "--data",
        str(config.data_directory),
        "--adapter-path",
        str(config.output_directory),
        "--iters",
        str(config.num_iters),
        "--batch-size",
        str(config.batch_size),
        "--learning-rate",
        str(config.learning_rate),
        "--num-layers",  # Number of layers to fine-tune
        str(config.lora_layers),
    ]

    # Note: LoRA rank must be set via config file, not command-line
    # For now, mlx-lm uses default rank (typically 8)
    # TODO: Implement config file support for custom rank

    return cmd


async def run_training_with_logs(config: LoRAConfig) -> TrainingResult:
    """Run LoRA training and return results with training logs.

    Executes mlx_lm.lora as subprocess and waits for completion.

    Args:
        config: LoRA training configuration

    Returns:
        TrainingResult with adapter path and training output

    Raises:
        subprocess.CalledProcessError: If training fails
    """
    cmd = build_train_command(config)

    # Ensure output directory exists
    config.output_directory.mkdir(parents=True, exist_ok=True)

    # Run training
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise subprocess.CalledProcessError(
            proc.returncode or 1,
            cmd,
            output=stdout,
            stderr=stderr,
        )

    # Combine stdout and stderr for log parsing
    output = stdout.decode("utf-8", errors="replace") + "\n" + stderr.decode("utf-8", errors="replace")

    return TrainingResult(adapter_path=config.output_directory, output=output)


async def run_training(config: LoRAConfig) -> Path:
    """Run LoRA training with given configuration.

    Executes mlx_lm.lora as subprocess and waits for completion.

    Args:
        config: LoRA training configuration

    Returns:
        Path to output adapter directory

    Raises:
        subprocess.CalledProcessError: If training fails
    """
    result = await run_training_with_logs(config)
    return result.adapter_path
