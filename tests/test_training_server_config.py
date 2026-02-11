"""Tests for server configuration dataclass."""

from punie.training.server_config import ServerConfig


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
    assert config.max_kv_size is None
    assert config.repetition_penalty is None


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


def test_server_config_with_kv_size():
    """ServerConfig can specify max KV cache size."""
    config = ServerConfig(
        model_path="test-model",
        max_kv_size=4096,
    )
    assert config.max_kv_size == 4096


def test_server_config_with_repetition_penalty():
    """ServerConfig can specify repetition penalty."""
    config = ServerConfig(
        model_path="test-model",
        repetition_penalty=1.1,
    )
    assert config.repetition_penalty == 1.1


def test_server_config_all_parameters():
    """ServerConfig with all parameters specified."""
    config = ServerConfig(
        model_path="mlx-community/Qwen3-Coder-30B",
        port=9000,
        host="192.168.1.1",
        adapter_path="/adapters/step-a",
        max_kv_size=8192,
        repetition_penalty=1.2,
    )
    assert config.model_path == "mlx-community/Qwen3-Coder-30B"
    assert config.port == 9000
    assert config.host == "192.168.1.1"
    assert config.adapter_path == "/adapters/step-a"
    assert config.max_kv_size == 8192
    assert config.repetition_penalty == 1.2
    assert config.base_url == "http://192.168.1.1:9000/v1"
