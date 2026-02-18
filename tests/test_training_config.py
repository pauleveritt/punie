"""Tests for training configuration: LoRA, server, hyperparameters, and tool calling.

Consolidates:
- LoRA configuration (LoRAConfig, build_train_command)
- Server configuration (ServerConfig, base_url, QWEN_STOP_SEQUENCES)
- Server process (ServerProcess, build_server_command, lifecycle)
- Hyperparameter tuning (HyperparamGrid, TrainingLog, parse_training_log)
- Inference tuning (InferenceGrid, InferenceResult)
- Tool call parsing (parse_tool_calls for JSON, XML, code fences)
- Tool calling templates (ToolCallExample, template factories)
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

from punie.training.eval_results import EvalReport, EvalResult
from punie.training.hyperparam import HyperparamGrid, TrainingLog, parse_training_log
from punie.training.inference_tuning import InferenceGrid, InferenceResult
from punie.training.lora_config import LoRAConfig
from punie.training.server import ServerProcess, build_server_command
from punie.training.server_config import QWEN_STOP_SEQUENCES, ServerConfig
from punie.training.tool_call_parser import parse_tool_calls
from punie.training.tool_calling_templates import (
    ToolCallExample,
    create_multi_tool_example,
    create_read_file_example,
    create_run_command_example,
    create_write_file_example,
)
from punie.training.train_runner import build_train_command


# ============================================================================
# LoRA Configuration Tests
# ============================================================================


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


def test_build_train_command_with_grad_accumulation_steps():
    """build_train_command includes --grad-accumulation-steps flag."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
        grad_accumulation_steps=4,
    )

    cmd = build_train_command(config)

    assert "--grad-accumulation-steps" in cmd
    assert "4" in cmd


def test_build_train_command_with_mask_prompt():
    """build_train_command includes --mask-prompt flag when True."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
        mask_prompt=True,
    )

    cmd = build_train_command(config)

    assert "--mask-prompt" in cmd


def test_build_train_command_with_lora_scale():
    """build_train_command includes --lora-scale flag."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
        lora_scale=20.0,
    )

    cmd = build_train_command(config)

    assert "--lora-scale" in cmd
    assert "20.0" in cmd


def test_build_train_command_with_weight_decay():
    """build_train_command includes --weight-decay flag."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
        weight_decay=0.01,
    )

    cmd = build_train_command(config)

    assert "--weight-decay" in cmd
    assert "0.01" in cmd


def test_build_train_command_new_fields_absent_by_default():
    """build_train_command omits new flags when using defaults."""
    config = LoRAConfig(
        base_model="test-model",
        data_directory=Path("/data"),
        output_directory=Path("/output"),
    )

    cmd = build_train_command(config)

    assert "--grad-accumulation-steps" not in cmd
    assert "--mask-prompt" not in cmd
    assert "--lora-scale" not in cmd
    assert "--weight-decay" not in cmd


# ============================================================================
# Server Configuration Tests
# ============================================================================


def test_server_config_frozen():
    """ServerConfig instances are immutable."""
    config = ServerConfig(model_path="test-model")
    try:
        config.port = 9000  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_server_config_defaults():
    """ServerConfig has sensible defaults."""
    config = ServerConfig(model_path="test-model")
    assert config.model_path == "test-model"
    assert config.port == 8080
    assert config.host == "127.0.0.1"
    assert config.adapter_path is None
    assert config.temp is None
    assert config.top_p is None
    assert config.max_tokens is None
    assert config.chat_template_args is None
    assert config.stop_sequences is None
    assert config.draft_model is None
    assert config.num_draft_tokens is None


def test_server_config_base_url():
    """base_url property constructs correct URL."""
    config = ServerConfig(model_path="test-model", port=9000, host="0.0.0.0")
    assert config.base_url == "http://0.0.0.0:9000/v1"


def test_server_config_base_url_default():
    """base_url uses default host and port."""
    config = ServerConfig(model_path="test-model")
    assert config.base_url == "http://127.0.0.1:8080/v1"


def test_server_config_with_adapter():
    """ServerConfig can specify adapter path."""
    config = ServerConfig(
        model_path="test-model",
        adapter_path="/path/to/adapter",
    )
    assert config.adapter_path == "/path/to/adapter"


def test_server_config_with_temp():
    """ServerConfig can specify temperature."""
    config = ServerConfig(
        model_path="test-model",
        temp=0.7,
    )
    assert config.temp == 0.7


def test_server_config_with_top_p():
    """ServerConfig can specify top_p."""
    config = ServerConfig(
        model_path="test-model",
        top_p=0.9,
    )
    assert config.top_p == 0.9


def test_server_config_with_max_tokens():
    """ServerConfig can specify max_tokens."""
    config = ServerConfig(
        model_path="test-model",
        max_tokens=512,
    )
    assert config.max_tokens == 512


def test_server_config_with_chat_template_args():
    """ServerConfig can specify chat_template_args."""
    config = ServerConfig(
        model_path="test-model",
        chat_template_args='{"enable_thinking":false}',
    )
    assert config.chat_template_args == '{"enable_thinking":false}'


def test_server_config_stop_sequences():
    """ServerConfig can specify stop_sequences."""
    config = ServerConfig(
        model_path="test-model",
        stop_sequences=QWEN_STOP_SEQUENCES,
    )
    assert config.stop_sequences == QWEN_STOP_SEQUENCES


def test_server_config_with_draft_model():
    """ServerConfig can specify draft_model for speculative decoding."""
    config = ServerConfig(
        model_path="test-model",
        draft_model="mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
    )
    assert config.draft_model == "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"


def test_server_config_with_num_draft_tokens():
    """ServerConfig can specify num_draft_tokens for speculative decoding."""
    config = ServerConfig(
        model_path="test-model",
        num_draft_tokens=5,
    )
    assert config.num_draft_tokens == 5


def test_server_config_all_parameters():
    """ServerConfig with all parameters specified."""
    config = ServerConfig(
        model_path="mlx-community/Qwen3-Coder-30B",
        port=9000,
        host="192.168.1.1",
        adapter_path="/adapters/step-a",
        temp=0.8,
        top_p=0.95,
        max_tokens=1024,
        chat_template_args='{"enable_thinking":false}',
        stop_sequences=QWEN_STOP_SEQUENCES,
        draft_model="mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
        num_draft_tokens=5,
    )
    assert config.model_path == "mlx-community/Qwen3-Coder-30B"
    assert config.port == 9000
    assert config.host == "192.168.1.1"
    assert config.adapter_path == "/adapters/step-a"
    assert config.temp == 0.8
    assert config.top_p == 0.95
    assert config.max_tokens == 1024
    assert config.chat_template_args == '{"enable_thinking":false}'
    assert config.stop_sequences == QWEN_STOP_SEQUENCES
    assert config.draft_model == "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    assert config.num_draft_tokens == 5
    assert config.base_url == "http://192.168.1.1:9000/v1"


# ============================================================================
# Server Process Tests
# ============================================================================


def test_build_server_command_minimal():
    """build_server_command with minimal config."""
    config = ServerConfig(model_path="test-model")
    cmd = build_server_command(config)

    assert cmd == [
        sys.executable,
        "-m",
        "mlx_lm",
        "server",
        "--model",
        "test-model",
        "--port",
        "8080",
        "--host",
        "127.0.0.1",
    ]


def test_build_server_command_with_adapter():
    """build_server_command includes adapter path."""
    config = ServerConfig(
        model_path="test-model",
        adapter_path="/path/to/adapter",
    )
    cmd = build_server_command(config)

    assert "--adapter-path" in cmd
    assert "/path/to/adapter" in cmd


def test_build_server_command_with_temp():
    """build_server_command includes temperature."""
    config = ServerConfig(
        model_path="test-model",
        temp=0.7,
    )
    cmd = build_server_command(config)

    assert "--temp" in cmd
    assert "0.7" in cmd


def test_build_server_command_with_top_p():
    """build_server_command includes top_p."""
    config = ServerConfig(
        model_path="test-model",
        top_p=0.9,
    )
    cmd = build_server_command(config)

    assert "--top-p" in cmd
    assert "0.9" in cmd


def test_build_server_command_with_max_tokens():
    """build_server_command includes max_tokens."""
    config = ServerConfig(
        model_path="test-model",
        max_tokens=512,
    )
    cmd = build_server_command(config)

    assert "--max-tokens" in cmd
    assert "512" in cmd


def test_build_server_command_with_chat_template_args():
    """build_server_command includes chat_template_args."""
    config = ServerConfig(
        model_path="test-model",
        chat_template_args='{"enable_thinking":false}',
    )
    cmd = build_server_command(config)

    assert "--chat-template-args" in cmd
    assert '{"enable_thinking":false}' in cmd


def test_build_server_command_with_draft_model():
    """build_server_command includes draft_model for speculative decoding."""
    config = ServerConfig(
        model_path="test-model",
        draft_model="mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
    )
    cmd = build_server_command(config)

    assert "--draft-model" in cmd
    assert "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit" in cmd


def test_build_server_command_with_num_draft_tokens():
    """build_server_command includes num_draft_tokens for speculative decoding."""
    config = ServerConfig(
        model_path="test-model",
        num_draft_tokens=5,
    )
    cmd = build_server_command(config)

    assert "--num-draft-tokens" in cmd
    assert "5" in cmd


def test_build_server_command_all_parameters():
    """build_server_command with all parameters."""
    config = ServerConfig(
        model_path="mlx-community/Qwen3",
        port=9000,
        host="0.0.0.0",
        adapter_path="/adapters/step-a",
        temp=0.8,
        top_p=0.95,
        max_tokens=1024,
        chat_template_args='{"enable_thinking":false}',
        draft_model="mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
        num_draft_tokens=5,
    )
    cmd = build_server_command(config)

    expected = [
        sys.executable,
        "-m",
        "mlx_lm",
        "server",
        "--model",
        "mlx-community/Qwen3",
        "--port",
        "9000",
        "--host",
        "0.0.0.0",
        "--adapter-path",
        "/adapters/step-a",
        "--temp",
        "0.8",
        "--top-p",
        "0.95",
        "--max-tokens",
        "1024",
        "--chat-template-args",
        '{"enable_thinking":false}',
        "--draft-model",
        "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
        "--num-draft-tokens",
        "5",
    ]
    assert cmd == expected


def test_server_process_initial_state():
    """ServerProcess starts in non-running state."""
    config = ServerConfig(model_path="test-model")
    server = ServerProcess(config=config)

    assert not server.is_running
    assert server.config == config


async def test_server_process_stop_idempotent():
    """ServerProcess.stop() is safe to call multiple times."""
    config = ServerConfig(model_path="test-model")
    server = ServerProcess(config=config)

    # Stop when never started - should not raise
    await server.stop()
    await server.stop()


async def test_server_process_health_check_unreachable():
    """health_check returns False for unreachable server."""
    config = ServerConfig(model_path="test-model", port=19999)  # Unlikely to be used
    server = ServerProcess(config=config)

    healthy = await server.health_check()
    assert not healthy


async def test_server_process_start_already_running():
    """Starting an already-running server raises RuntimeError."""
    config = ServerConfig(model_path="test-model")
    server = ServerProcess(config=config)

    # Simulate running state with a minimal mock process
    class MockProcess:
        def poll(self) -> None:
            return None  # Process is still running

    server._process = MockProcess()  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="already running"):
        await server.start()


def test_server_process_is_running_when_process_none():
    """is_running is False when _process is None."""
    config = ServerConfig(model_path="test-model")
    server = ServerProcess(config=config)

    assert server._process is None
    assert not server.is_running


def test_server_process_is_running_when_process_terminated():
    """is_running is False when process has terminated."""
    config = ServerConfig(model_path="test-model")
    server = ServerProcess(config=config)

    # Simulate terminated process
    class MockProcess:
        def poll(self) -> int:
            return 0  # Process has exited

    server._process = MockProcess()  # type: ignore[assignment]

    assert not server.is_running


def test_server_process_is_running_when_process_active():
    """is_running is True when process is active."""
    config = ServerConfig(model_path="test-model")
    server = ServerProcess(config=config)

    # Simulate active process
    class MockProcess:
        def poll(self) -> None:
            return None  # Process is still running

    server._process = MockProcess()  # type: ignore[assignment]

    assert server.is_running


# ============================================================================
# Hyperparameter Tuning Tests
# ============================================================================


def test_hyperparam_grid_frozen():
    """HyperparamGrid is immutable."""
    grid = HyperparamGrid()

    try:
        grid.learning_rates = (1e-4,)  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_hyperparam_grid_defaults():
    """HyperparamGrid has sensible defaults."""
    grid = HyperparamGrid()

    assert grid.learning_rates == (1e-5, 5e-5, 1e-4)
    assert grid.lora_ranks == (4, 8, 16)
    assert grid.num_iters == (50, 100, 200)
    assert grid.batch_sizes == (2, 4)


def test_hyperparam_grid_total_combinations():
    """HyperparamGrid calculates total combinations correctly."""
    grid = HyperparamGrid(
        learning_rates=(1e-5, 5e-5),
        lora_ranks=(4, 8),
        num_iters=(50,),
        batch_sizes=(2,),
    )

    # 2 * 2 * 1 * 1 = 4
    assert grid.total_combinations == 4


def test_hyperparam_grid_custom():
    """HyperparamGrid with custom values."""
    grid = HyperparamGrid(
        learning_rates=(1e-4,),
        lora_ranks=(16,),
        num_iters=(100, 200),
        batch_sizes=(4, 8),
    )

    assert len(grid.learning_rates) == 1
    assert len(grid.lora_ranks) == 1
    assert len(grid.num_iters) == 2
    assert len(grid.batch_sizes) == 2
    assert grid.total_combinations == 4  # 1 * 1 * 2 * 2


def test_training_log_frozen():
    """TrainingLog is immutable."""
    log = TrainingLog(iteration=10, train_loss=2.5)

    try:
        log.iteration = 20  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_training_log_with_val_loss():
    """TrainingLog with validation loss."""
    log = TrainingLog(iteration=10, train_loss=2.5, val_loss=2.8)

    assert log.iteration == 10
    assert log.train_loss == 2.5
    assert log.val_loss == 2.8


def test_training_log_without_val_loss():
    """TrainingLog without validation loss."""
    log = TrainingLog(iteration=10, train_loss=2.5)

    assert log.iteration == 10
    assert log.train_loss == 2.5
    assert log.val_loss is None


def test_parse_training_log_empty():
    """parse_training_log with empty output."""
    logs = parse_training_log("")
    assert logs == ()


def test_parse_training_log_single_iter():
    """parse_training_log with single iteration."""
    output = "Iter 10: Train loss 2.345, Val loss 2.567"
    logs = parse_training_log(output)

    assert len(logs) == 1
    assert logs[0].iteration == 10
    assert logs[0].train_loss == 2.345
    assert logs[0].val_loss == 2.567


def test_parse_training_log_multiple_iters():
    """parse_training_log with multiple iterations."""
    output = """
    Iter 10: Train loss 2.345, Val loss 2.567
    Iter 20: Train loss 2.123, Val loss 2.345
    Iter 30: Train loss 1.987, Val loss 2.234
    """
    logs = parse_training_log(output)

    assert len(logs) == 3
    assert logs[0].iteration == 10
    assert logs[0].train_loss == 2.345
    assert logs[1].iteration == 20
    assert logs[1].train_loss == 2.123
    assert logs[2].iteration == 30
    assert logs[2].train_loss == 1.987


def test_parse_training_log_train_only():
    """parse_training_log with only train loss."""
    output = "Iter 10: Train loss 2.345"
    logs = parse_training_log(output)

    assert len(logs) == 1
    assert logs[0].iteration == 10
    assert logs[0].train_loss == 2.345
    assert logs[0].val_loss is None


def test_parse_training_log_mixed_content():
    """parse_training_log with mixed content."""
    output = """
    Loading model...
    Iter 10: Train loss 2.345, Val loss 2.567
    Some random output
    Iter 20: Train loss 2.123
    More output
    Iter 30: Train loss 1.987, Val loss 2.100
    Done!
    """
    logs = parse_training_log(output)

    assert len(logs) == 3
    assert logs[0].iteration == 10
    assert logs[1].iteration == 20
    assert logs[1].val_loss is None
    assert logs[2].iteration == 30


def test_parse_training_log_malformed_lines():
    """parse_training_log skips malformed lines."""
    output = """
    Iter: Train loss 2.345
    Iter 10 Train loss 2.345
    Iter 20: Train loss invalid
    Iter 30: Train loss 1.987, Val loss 2.100
    """
    logs = parse_training_log(output)

    # Only the last line should parse correctly
    assert len(logs) == 1
    assert logs[0].iteration == 30


# ============================================================================
# Inference Tuning Tests
# ============================================================================


def test_inference_grid_frozen():
    """InferenceGrid is immutable."""
    grid = InferenceGrid()

    try:
        grid.temperatures = (0.5,)  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_inference_grid_defaults():
    """InferenceGrid has sensible defaults."""
    grid = InferenceGrid()

    assert grid.temperatures == (0.0, 0.1, 0.3, 0.7)
    assert grid.top_ps == (0.9, 0.95, 1.0)


def test_inference_grid_total_combinations():
    """InferenceGrid calculates total combinations correctly."""
    grid = InferenceGrid(
        temperatures=(0.0, 0.5),
        top_ps=(0.9, 1.0),
    )

    # 2 * 2 = 4
    assert grid.total_combinations == 4


def test_inference_grid_custom():
    """InferenceGrid with custom values."""
    grid = InferenceGrid(
        temperatures=(0.0,),
        top_ps=(1.0,),
    )

    assert len(grid.temperatures) == 1
    assert len(grid.top_ps) == 1
    assert grid.total_combinations == 1  # 1 * 1


def test_inference_result_frozen():
    """InferenceResult is immutable."""
    config = ServerConfig(model_path="test")
    report = EvalReport(
        model_name="test",
        adapter_path=None,
        suite_name="test",
        timestamp=datetime.now(),
        results=(),
    )

    result = InferenceResult(
        server_config=config,
        eval_report=report,
        temperature=0.0,
        top_p=0.9,
    )

    try:
        result.temperature = 0.5  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_inference_result_basic():
    """InferenceResult stores all parameters."""
    config = ServerConfig(
        model_path="test-model",
        port=8080,
        temp=0.3,
        top_p=0.95,
    )

    report = EvalReport(
        model_name="test-model",
        adapter_path=None,
        suite_name="test",
        timestamp=datetime.now(),
        results=(
            EvalResult("p1", "response", (), 100.0, 0.8, True),
        ),
    )

    result = InferenceResult(
        server_config=config,
        eval_report=report,
        temperature=0.3,
        top_p=0.95,
    )

    assert result.server_config.model_path == "test-model"
    assert result.server_config.temp == 0.3
    assert result.server_config.top_p == 0.95
    assert result.eval_report.overall_score == 0.8
    assert result.temperature == 0.3
    assert result.top_p == 0.95


# ============================================================================
# Tool Call Parser Tests
# ============================================================================


def test_parse_single_json_tool_call():
    """Parse a single JSON-format tool call from model output."""
    text = 'Some text<tool_call>{"name": "read_file", "arguments": {"path": "foo.py"}}</tool_call>'
    content, calls = parse_tool_calls(text)

    assert content == "Some text"
    assert len(calls) == 1
    assert calls[0]["name"] == "read_file"
    assert calls[0]["arguments"] == {"path": "foo.py"}


def test_parse_multiple_json_tool_calls():
    """Parse multiple JSON-format tool calls from model output."""
    text = (
        'Let me help<tool_call>{"name": "read_file", "arguments": {"path": "a.py"}}</tool_call>'
        ' and <tool_call>{"name": "write_file", "arguments": {"path": "b.py", "content": "x"}}</tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert content == "Let me help and"
    assert len(calls) == 2
    assert calls[0]["name"] == "read_file"
    assert calls[1]["name"] == "write_file"


def test_parse_xml_tool_call():
    """Parse XML-format tool call with parameters."""
    text = (
        'Let me list files<tool_call>'
        '<function=list_files>'
        '<parameter=path>.</parameter>'
        '<parameter=pattern>*.py</parameter>'
        '</function>'
        '</tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert content == "Let me list files"
    assert len(calls) == 1
    assert calls[0]["name"] == "list_files"
    assert calls[0]["arguments"] == {"path": ".", "pattern": "*.py"}


def test_parse_xml_tool_call_single_parameter():
    """Parse XML-format tool call with single parameter."""
    text = (
        'Reading<tool_call>'
        '<function=read_file>'
        '<parameter=path>/path/to/file.py</parameter>'
        '</function>'
        '</tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert content == "Reading"
    assert len(calls) == 1
    assert calls[0]["name"] == "read_file"
    assert calls[0]["arguments"] == {"path": "/path/to/file.py"}


def test_parse_broken_xml_missing_opening_tag():
    """Parse broken XML format missing opening <tool_call> tag."""
    text = (
        'Let me search'
        '<function=search_code>'
        '<parameter=query>def main</parameter>'
        '<parameter=file_pattern>*.py</parameter>'
        '</function></tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert content == "Let me search"
    assert len(calls) == 1
    assert calls[0]["name"] == "search_code"
    assert calls[0]["arguments"] == {"query": "def main", "file_pattern": "*.py"}


def test_parse_no_tool_calls():
    """Parse text with no tool calls returns empty list."""
    text = "Just plain text with no tool calls."
    content, calls = parse_tool_calls(text)

    assert content == "Just plain text with no tool calls."
    assert calls == []


def test_parse_invalid_json_tool_call():
    """Invalid JSON in tool call is stripped but not added to calls."""
    text = 'Text<tool_call>{"name": "read", invalid json}</tool_call> more text'
    content, calls = parse_tool_calls(text)

    # Invalid JSON should be stripped but not added to calls
    assert "invalid json" not in content
    assert "<tool_call>" not in content
    assert content == "Text more text"
    assert calls == []


def test_parse_json_tool_call_missing_name():
    """Tool call without 'name' field is skipped."""
    text = 'Text<tool_call>{"arguments": {"path": "foo.py"}}</tool_call>'
    content, calls = parse_tool_calls(text)

    # Missing name means invalid tool call - should be stripped
    assert calls == []
    assert "<tool_call>" not in content


def test_parse_xml_tool_call_missing_function_tag():
    """XML tool call without function tag is skipped."""
    text = 'Text<tool_call><parameter=path>.</parameter></tool_call>'
    content, calls = parse_tool_calls(text)

    # Missing function tag means invalid - should be stripped
    assert calls == []
    assert "<tool_call>" not in content


def test_parse_mixed_text_and_tool_calls():
    """Parse text with interleaved content and multiple tool calls."""
    text = (
        'First, I will read the file '
        '<tool_call>{"name": "read_file", "arguments": {"path": "main.py"}}</tool_call> '
        'and then I will search for the function '
        '<tool_call>{"name": "search_code", "arguments": {"query": "def process"}}</tool_call> '
        'to understand the logic.'
    )
    content, calls = parse_tool_calls(text)

    assert "First, I will read the file" in content
    assert "and then I will search for the function" in content
    assert "to understand the logic." in content
    assert len(calls) == 2
    assert calls[0]["name"] == "read_file"
    assert calls[1]["name"] == "search_code"


def test_parse_tool_call_preserves_whitespace():
    """Tool call parsing preserves meaningful whitespace in remaining text."""
    text = (
        'Line 1\n'
        '<tool_call>{"name": "test", "arguments": {}}</tool_call>\n'
        'Line 2'
    )
    content, calls = parse_tool_calls(text)

    # Should preserve the newline structure (but strip() at end removes trailing/leading)
    assert "Line 1" in content
    assert "Line 2" in content
    assert len(calls) == 1


def test_parse_xml_with_multiline_parameter_values():
    """Parse XML tool call with multiline parameter values."""
    text = (
        '<tool_call>'
        '<function=write_file>'
        '<parameter=path>test.py</parameter>'
        '<parameter=content>line 1\nline 2\nline 3</parameter>'
        '</function>'
        '</tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert len(calls) == 1
    assert calls[0]["name"] == "write_file"
    assert calls[0]["arguments"]["content"] == "line 1\nline 2\nline 3"


def test_parse_empty_string():
    """Parse empty string returns empty results."""
    content, calls = parse_tool_calls("")

    assert content == ""
    assert calls == []


def test_parse_tool_call_with_nested_json():
    """Parse tool call with nested JSON in arguments."""
    text = (
        '<tool_call>'
        '{"name": "update_config", "arguments": {"config": {"key1": "value1", "key2": {"nested": true}}}}'
        '</tool_call>'
    )
    content, calls = parse_tool_calls(text)

    assert content == ""
    assert len(calls) == 1
    assert calls[0]["name"] == "update_config"
    assert calls[0]["arguments"]["config"]["key2"]["nested"] is True


def test_parse_json_code_fence():
    """Parse JSON tool call in code fence (used by smaller models like 1.5B)."""
    text = '''Let me read that file.

```json
{
  "name": "read_file",
  "arguments": {
    "path": "src/main.py"
  }
}
```'''
    content, calls = parse_tool_calls(text)

    assert "Let me read that file." in content
    assert len(calls) == 1
    assert calls[0]["name"] == "read_file"
    assert calls[0]["arguments"]["path"] == "src/main.py"


def test_parse_multiple_code_fences():
    """Parse multiple JSON code fences."""
    text = '''First, read the file:

```json
{
  "name": "read_file",
  "arguments": {"path": "test.py"}
}
```

Then run the tests:

```json
{
  "name": "run_command",
  "arguments": {"command": "pytest"}
}
```'''
    content, calls = parse_tool_calls(text)

    assert len(calls) == 2
    assert calls[0]["name"] == "read_file"
    assert calls[1]["name"] == "run_command"


def test_parse_mixed_formats():
    """Parse both <tool_call> tags and code fences in same text."""
    text = '''Using tags: <tool_call>{"name": "read_file", "arguments": {"path": "a.py"}}</tool_call>

And code fence:

```json
{
  "name": "write_file",
  "arguments": {"path": "b.py", "content": "test"}
}
```'''
    content, calls = parse_tool_calls(text)

    assert len(calls) == 2
    assert calls[0]["name"] == "read_file"
    assert calls[1]["name"] == "write_file"


# ============================================================================
# Tool Calling Templates Tests
# ============================================================================


def test_tool_call_example_frozen():
    """ToolCallExample is immutable."""
    example = ToolCallExample(
        system_message="system",
        user_request="request",
        tool_name="read_file",
        tool_arguments='{"path": "test.py"}',
        tool_result="content",
        assistant_response="response",
    )

    try:
        example.tool_name = "write_file"  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_tool_call_example_to_training_example():
    """ToolCallExample converts to correct message sequence."""
    example = ToolCallExample(
        system_message="You are a helpful assistant.",
        user_request="Read the file test.py",
        tool_name="read_file",
        tool_arguments='{"path": "test.py"}',
        tool_result="print('hello')",
        assistant_response="The file contains a simple print statement.",
    )

    training_example = example.to_training_example()

    # Should have 5 messages: system, user, assistant (tool call), user (result), assistant (final)
    assert len(training_example.messages) == 5

    assert training_example.messages[0].role == "system"
    assert training_example.messages[0].content == "You are a helpful assistant."

    assert training_example.messages[1].role == "user"
    assert training_example.messages[1].content == "Read the file test.py"

    assert training_example.messages[2].role == "assistant"
    assert "<tool_call>" in training_example.messages[2].content
    assert '"name": "read_file"' in training_example.messages[2].content
    assert '"path": "test.py"' in training_example.messages[2].content

    assert training_example.messages[3].role == "user"
    assert "Tool result:" in training_example.messages[3].content
    assert "print('hello')" in training_example.messages[3].content

    assert training_example.messages[4].role == "assistant"
    assert training_example.messages[4].content == "The file contains a simple print statement."


def test_create_read_file_example():
    """create_read_file_example produces valid training example."""
    example = create_read_file_example(
        file_path="src/main.py",
        file_content="def main():\n    pass",
        user_question="What does main.py do?",
        assistant_answer="The file defines an empty main function.",
    )

    assert len(example.messages) == 5
    assert example.messages[1].content == "What does main.py do?"
    assert "<tool_call>" in example.messages[2].content
    assert '"name": "read_file"' in example.messages[2].content
    assert "src/main.py" in example.messages[2].content
    assert "def main()" in example.messages[3].content
    assert "empty main function" in example.messages[4].content


def test_create_write_file_example():
    """create_write_file_example produces valid training example."""
    example = create_write_file_example(
        file_path="test.txt",
        new_content="Hello, World!",
        user_request="Create a test file with hello world",
        confirmation_message="I've created test.txt with the message.",
    )

    assert len(example.messages) == 5
    assert example.messages[1].content == "Create a test file with hello world"
    assert "<tool_call>" in example.messages[2].content
    assert '"name": "write_file"' in example.messages[2].content
    assert "test.txt" in example.messages[2].content
    assert "File written successfully" in example.messages[3].content
    assert "created test.txt" in example.messages[4].content


def test_create_run_command_example():
    """create_run_command_example produces valid training example."""
    example = create_run_command_example(
        command="pytest tests/",
        output="5 passed in 0.1s",
        user_request="Run the tests",
        assistant_interpretation="All 5 tests passed successfully!",
    )

    assert len(example.messages) == 5
    assert example.messages[1].content == "Run the tests"
    assert "<tool_call>" in example.messages[2].content
    assert '"name": "run_command"' in example.messages[2].content
    assert "pytest tests/" in example.messages[2].content
    assert "5 passed" in example.messages[3].content
    assert "All 5 tests passed" in example.messages[4].content


def test_create_multi_tool_example():
    """create_multi_tool_example handles multiple tool calls."""
    example = create_multi_tool_example(
        system_message="You are Punie.",
        user_request="Read main.py and run the tests",
        tool_sequence=[
            ("read_file", '{"path": "main.py"}', "def main(): pass"),
            ("run_command", '{"command": "pytest"}', "3 passed"),
        ],
        final_response="I read main.py and ran the tests. All 3 tests passed.",
    )

    # System + user + (assistant + user) * 2 tools + final assistant = 7 messages
    assert len(example.messages) == 7

    assert example.messages[0].role == "system"
    assert example.messages[1].role == "user"

    # First tool call
    assert example.messages[2].role == "assistant"
    assert "<tool_call>" in example.messages[2].content
    assert '"name": "read_file"' in example.messages[2].content
    assert example.messages[3].role == "user"
    assert "def main()" in example.messages[3].content

    # Second tool call
    assert example.messages[4].role == "assistant"
    assert "<tool_call>" in example.messages[4].content
    assert '"name": "run_command"' in example.messages[4].content
    assert example.messages[5].role == "user"
    assert "3 passed" in example.messages[5].content

    # Final response
    assert example.messages[6].role == "assistant"
    assert "All 3 tests passed" in example.messages[6].content


def test_create_multi_tool_example_single_tool():
    """create_multi_tool_example works with single tool."""
    example = create_multi_tool_example(
        system_message="System",
        user_request="Read file",
        tool_sequence=[
            ("read_file", '{"path": "test.py"}', "content"),
        ],
        final_response="Done",
    )

    # System + user + assistant + user + assistant = 5 messages
    assert len(example.messages) == 5
