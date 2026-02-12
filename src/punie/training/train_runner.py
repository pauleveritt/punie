"""LoRA training runner."""

import asyncio
import subprocess
from pathlib import Path

from punie.training.lora_config import LoRAConfig


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
        "--num-layers",  # Changed from --lora-layers
        str(config.lora_layers),
    ]

    # Note: LoRA rank is set via config file or defaults
    # Can be extended later with --config flag

    return cmd


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

    return config.output_directory
