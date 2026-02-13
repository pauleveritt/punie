"""Tests for local server connection error handling.

Verifies graceful fallback to test model when local server (LM Studio,
mlx-lm.server) is not available.
"""


def test_local_spec_parsing():
    """Verify local model spec parsing works correctly."""
    from punie.agent.factory import _parse_local_spec

    # Empty spec uses defaults
    spec = _parse_local_spec("")
    assert spec.base_url == "http://localhost:1234/v1"
    assert spec.model_name == "default"

    # Model name only
    spec = _parse_local_spec("my-model")
    assert spec.base_url == "http://localhost:1234/v1"
    assert spec.model_name == "my-model"

    # Full URL
    spec = _parse_local_spec("http://localhost:8080/v1/custom")
    assert spec.base_url == "http://localhost:8080/v1"
    assert spec.model_name == "custom"
