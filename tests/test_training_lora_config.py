"""Tests for LoRA training configuration."""

from pathlib import Path


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
    assert config.batch_size == 2  # Reduced from 4 to control memory usage
    assert config.learning_rate == 1e-5
    assert config.lora_rank == 8
    assert config.lora_layers == 16
    assert config.save_every is None
    assert config.val_batches is None
    assert config.test is False
    assert config.steps_per_report is None
    assert config.steps_per_eval is None
    assert config.grad_checkpoint is False
    assert config.config_file is None


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
        "python",
        "-m",
        "mlx_lm",
        "lora",
        "--model",
        "test-model",
        "--train",
        "--data",
        "/data",
        "--adapter-path",
        "/output",
        "--iters",
        "100",
        "--batch-size",
        "2",  # Reduced from 4 to control memory usage
        "--learning-rate",
        "1e-05",
        "--num-layers",
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
    assert "--num-layers" in cmd
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


def test_build_train_command_with_save_every():
    """build_train_command includes --save-every flag."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
        save_every=50,
    )

    cmd = build_train_command(config)

    assert "--save-every" in cmd
    assert "50" in cmd


def test_build_train_command_with_val_batches():
    """build_train_command includes --val-batches flag."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
        val_batches=10,
    )

    cmd = build_train_command(config)

    assert "--val-batches" in cmd
    assert "10" in cmd


def test_build_train_command_with_test():
    """build_train_command includes --test flag."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
        test=True,
    )

    cmd = build_train_command(config)

    assert "--test" in cmd


def test_build_train_command_with_steps_per_report():
    """build_train_command includes --steps-per-report flag."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
        steps_per_report=10,
    )

    cmd = build_train_command(config)

    assert "--steps-per-report" in cmd
    assert "10" in cmd


def test_build_train_command_with_steps_per_eval():
    """build_train_command includes --steps-per-eval flag."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
        steps_per_eval=25,
    )

    cmd = build_train_command(config)

    assert "--steps-per-eval" in cmd
    assert "25" in cmd


def test_build_train_command_with_grad_checkpoint():
    """build_train_command includes --grad-checkpoint flag."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
        grad_checkpoint=True,
    )

    cmd = build_train_command(config)

    assert "--grad-checkpoint" in cmd


def test_build_train_command_with_config_file():
    """build_train_command includes --config flag."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
        config_file=Path("/config/lora.yaml"),
    )

    cmd = build_train_command(config)

    assert "--config" in cmd
    assert "/config/lora.yaml" in cmd


def test_build_train_command_with_all_optional_flags():
    """build_train_command with all optional flags."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
        save_every=50,
        val_batches=10,
        test=True,
        steps_per_report=10,
        steps_per_eval=25,
        grad_checkpoint=True,
        config_file=Path("/config/lora.yaml"),
    )

    cmd = build_train_command(config)

    assert "--save-every" in cmd
    assert "50" in cmd
    assert "--val-batches" in cmd
    assert "10" in cmd
    assert "--test" in cmd
    assert "--steps-per-report" in cmd
    assert "10" in cmd
    assert "--steps-per-eval" in cmd
    assert "25" in cmd
    assert "--grad-checkpoint" in cmd
    assert "--config" in cmd
    assert "/config/lora.yaml" in cmd
