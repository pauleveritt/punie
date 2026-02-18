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
    save_every: int | None = None  # Save checkpoint every N iterations (--save-every)
    val_batches: int | None = None  # Number of validation batches (--val-batches)
    test: bool = False  # Run test after training (--test)
    steps_per_report: int | None = None  # Log training stats every N steps (--steps-per-report)
    steps_per_eval: int | None = None  # Run validation every N steps (--steps-per-eval)
    grad_checkpoint: bool = False  # Use gradient checkpointing to reduce memory (--grad-checkpoint)
    config_file: Path | None = None  # YAML config file for lora_rank and other settings (--config)
    grad_accumulation_steps: int | None = None  # Accumulate gradients N steps before update (--grad-accumulation-steps)
    mask_prompt: bool = False  # Train only on completions, not on system+user turns (--mask-prompt)
    lora_scale: float | None = None  # LoRA scaling factor; None = use mlx_lm default (--lora-scale)
    weight_decay: float | None = None  # AdamW weight decay for regularization (--weight-decay)
