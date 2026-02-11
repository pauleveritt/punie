"""Tests for local model specification parsing.

Tests _parse_local_spec() function that parses three formats:
1. "" (empty) → default URL + default model
2. "model-name" → default URL + given model
3. "http://host:port/v1/model" → custom URL + model
"""

from punie.agent.factory import (
    DEFAULT_LOCAL_BASE_URL,
    DEFAULT_LOCAL_MODEL,
    _parse_local_spec,
)


def test_parse_empty_string():
    """Empty string returns defaults."""
    result = _parse_local_spec("")
    assert result.base_url == DEFAULT_LOCAL_BASE_URL
    assert result.model_name == DEFAULT_LOCAL_MODEL


def test_parse_model_name_only():
    """Model name only uses default URL."""
    result = _parse_local_spec("my-custom-model")
    assert result.base_url == DEFAULT_LOCAL_BASE_URL
    assert result.model_name == "my-custom-model"


def test_parse_full_url():
    """Full URL with model extracts both."""
    result = _parse_local_spec("http://localhost:8080/v1/qwen-model")
    assert result.base_url == "http://localhost:8080/v1"
    assert result.model_name == "qwen-model"


def test_parse_https_url():
    """HTTPS URLs are supported."""
    result = _parse_local_spec("https://api.example.com/v1/model-name")
    assert result.base_url == "https://api.example.com/v1"
    assert result.model_name == "model-name"


def test_parse_url_with_127_0_0_1():
    """127.0.0.1 is supported."""
    result = _parse_local_spec("http://127.0.0.1:1234/v1/test-model")
    assert result.base_url == "http://127.0.0.1:1234/v1"
    assert result.model_name == "test-model"


def test_parse_url_without_port():
    """URLs without explicit port work."""
    result = _parse_local_spec("http://localhost/v1/model")
    assert result.base_url == "http://localhost/v1"
    assert result.model_name == "model"


def test_parse_url_with_path():
    """URLs with /v1 path are normalized correctly."""
    result = _parse_local_spec("http://api.local:9000/v1/llama-3")
    assert result.base_url == "http://api.local:9000/v1"
    assert result.model_name == "llama-3"
