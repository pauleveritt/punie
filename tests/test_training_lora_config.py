"""Tests for LoRA training configuration."""

from pathlib import Path

import pytest

from punie.training.lora_config import LoRAConfig
from punie.training.train_runner import build_train_command


def test_lora_config_frozen():
    """LoRAConfig instances are immutable."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
    )

    try:
        config.num_iters = 200  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_lora_config_defaults():
    """LoRAConfig has sensible defaults."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
    )

    assert config.base_model == "test-model"
    assert config.data_directory == Path("/data")
    assert config.output_directory == Path("/output")
    assert config.num_iters == 100
    assert config.batch_size == 4
    assert config.learning_rate == 1e-5
    assert config.lora_rank == 8
    assert config.lora_layers == 16


def test_lora_config_all_parameters():
    """LoRAConfig with all parameters specified."""
    config = LoRAConfig(
        base_model="mlx-community/Qwen2.5-Coder-7B",
        data_directory=Path("/data/train"),
        output_directory=Path("/adapters/v1"),
        num_iters=200,
        batch_size=8,
        learning_rate=5e-5,
        lora_rank=16,
        lora_layers=32,
    )

    assert config.base_model == "mlx-community/Qwen2.5-Coder-7B"
    assert config.num_iters == 200
    assert config.batch_size == 8
    assert config.learning_rate == 5e-5
    assert config.lora_rank == 16
    assert config.lora_layers == 32


def test_build_train_command_minimal():
    """build_train_command with default config."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
    )

    cmd = build_train_command(config)

    assert cmd == [
        "mlx_lm.lora",
        "--model",
        "test-model",
        "--data",
        "/data",
        "--adapter-path",
        "/output",
        "--iters",
        "100",
        "--batch-size",
        "4",
        "--learning-rate",
        "1e-05",
        "--lora-layers",
        "16",
    ]


def test_build_train_command_custom():
    """build_train_command with custom parameters."""
    config = LoRAConfig(
        base_model="mlx-community/Qwen2.5-Coder-7B",
        data_directory=Path("/data/train"),
        output_directory=Path("/adapters/v1"),
        num_iters=200,
        batch_size=8,
        learning_rate=5e-5,
        lora_layers=32,
    )

    cmd = build_train_command(config)

    assert "--model" in cmd
    assert "mlx-community/Qwen2.5-Coder-7B" in cmd
    assert "--iters" in cmd
    assert "200" in cmd
    assert "--batch-size" in cmd
    assert "8" in cmd
    assert "--learning-rate" in cmd
    assert str(5e-5) in cmd
    assert "--lora-layers" in cmd
    assert "32" in cmd


def test_build_train_command_paths_are_strings():
    """build_train_command converts Path objects to strings."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data/train"),
        output_directory=Path("/adapters/v1"),
    )

    cmd = build_train_command(config)

    # Check that paths are converted to strings
    assert "/data/train" in cmd
    assert "/adapters/v1" in cmd
    assert not any(isinstance(item, Path) for item in cmd)
