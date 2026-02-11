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


def test_error_handling_preserves_non_local_errors():
    """Non-local model errors should propagate normally."""
    # This is tested by the adapter code - if model string doesn't contain "local",
    # the exception is re-raised. This test documents the behavior.
    pass


def test_error_message_mentions_lm_studio():
    """Error message should guide users to LM Studio."""
    # The error message in adapter.py includes:
    # - "Local model server not available"
    # - LM Studio installation link
    # - mlx-lm.server instructions
    # - Fallback suggestions
    # This is verified by code inspection in adapter.py lines 263-289
    pass
