"""LoRA training configuration."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoRAConfig:
    """Configuration for LoRA fine-tuning.

    All parameters mirror mlx_lm.lora command-line arguments.
    """

    base_model: str  # Model path (e.g., "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit")
    data_directory: Path  # Directory with train/valid/test JSONL files
    output_directory: Path  # Where to save adapter weights
    num_iters: int = 100  # Number of training iterations
    batch_size: int = 2  # Training batch size (reduced from 4 to control memory)
    learning_rate: float = 1e-5  # Learning rate
    lora_rank: int = 8  # LoRA rank (r) - adapter capacity
    lora_layers: int = 16  # Number of layers to adapt
