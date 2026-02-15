"""Tests for server configuration dataclass."""

from punie.training.server_config import QWEN_STOP_SEQUENCES, ServerConfig


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
