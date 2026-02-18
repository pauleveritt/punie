"""Tests for punie.client.timeouts — centralized timeout configuration."""

from __future__ import annotations

import pytest

from punie.client.timeouts import CLIENT_TIMEOUTS, Timeouts


def test_default_timeouts_exist():
    """CLIENT_TIMEOUTS singleton should exist with expected defaults."""
    assert CLIENT_TIMEOUTS.connect_timeout == 10.0
    assert CLIENT_TIMEOUTS.request_timeout == 30.0
    assert CLIENT_TIMEOUTS.streaming_timeout == 300.0
    assert CLIENT_TIMEOUTS.send_timeout == 5.0
    assert CLIENT_TIMEOUTS.idle_timeout == 300.0
    assert CLIENT_TIMEOUTS.grace_period == 300.0
    assert CLIENT_TIMEOUTS.cleanup_interval == 60.0
    assert CLIENT_TIMEOUTS.aggregate_timeout == 600.0


def test_timeouts_is_frozen():
    """Timeouts dataclass should be frozen (immutable)."""
    with pytest.raises((AttributeError, TypeError)):
        CLIENT_TIMEOUTS.connect_timeout = 99.0  # type: ignore[misc]


def test_custom_timeouts():
    """Should be able to create custom Timeouts instance."""
    custom = Timeouts(connect_timeout=5.0, request_timeout=15.0)
    assert custom.connect_timeout == 5.0
    assert custom.request_timeout == 15.0
    # Other values should be defaults
    assert custom.streaming_timeout == 300.0
