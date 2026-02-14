"""Tests for server process lifecycle."""

import pytest

from punie.training.server import ServerProcess, build_server_command
from punie.training.server_config import ServerConfig


def test_build_server_command_minimal():
    """build_server_command with minimal config."""
    config = ServerConfig(model_path="test-model")
    cmd = build_server_command(config)

    assert cmd == [
        "python",
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
    )
    cmd = build_server_command(config)

    expected = [
        "python",
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
