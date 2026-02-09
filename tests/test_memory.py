"""Tests for memory monitoring utilities."""

import pytest

from punie.models.memory import (
    MODEL_SIZES_MB,
    MemorySnapshot,
    check_memory_available,
    estimate_model_size,
    get_memory_snapshot,
)


def test_memory_snapshot_is_frozen():
    """MemorySnapshot should be a frozen dataclass."""
    from dataclasses import FrozenInstanceError

    snapshot = MemorySnapshot(
        rss_bytes=1024 * 1024,
        rss_mb=1.0,
        peak_rss_bytes=2 * 1024 * 1024,
        peak_rss_mb=2.0,
    )
    with pytest.raises(FrozenInstanceError):
        snapshot.rss_bytes = 2048  # type: ignore[misc]


def test_get_memory_snapshot_returns_positive_values():
    """get_memory_snapshot should return positive memory values."""
    snapshot = get_memory_snapshot()
    assert snapshot.rss_bytes > 0
    assert snapshot.rss_mb > 0
    assert snapshot.peak_rss_bytes > 0
    assert snapshot.peak_rss_mb > 0


def test_get_memory_snapshot_rss_mb_matches_bytes():
    """RSS in MB should match bytes / (1024*1024)."""
    snapshot = get_memory_snapshot()
    expected_mb = snapshot.rss_bytes / (1024 * 1024)
    # Allow small floating point error
    assert abs(snapshot.rss_mb - expected_mb) < 0.01


def test_check_memory_available_returns_tuple():
    """check_memory_available should return (bool, MemorySnapshot) tuple."""
    result = check_memory_available(1024.0)  # 1GB model
    assert isinstance(result, tuple)
    assert len(result) == 2
    available, snapshot = result
    assert isinstance(available, bool)
    assert isinstance(snapshot, MemorySnapshot)


def test_check_memory_available_large_model_warns():
    """Huge model size should trigger availability warning."""
    # Request absurdly large model (1TB)
    available, snapshot = check_memory_available(1024 * 1024 * 1024)
    # Should report not available (unless running on a supercomputer!)
    assert available is False
    assert snapshot.rss_mb > 0


def test_estimate_model_size_known_models():
    """estimate_model_size should recognize 3B, 7B, 14B, 30B patterns."""
    assert estimate_model_size("mlx-community/Qwen2.5-Coder-3B-Instruct-4bit") == 2048.0
    assert estimate_model_size("mlx-community/Qwen2.5-Coder-7B-Instruct-4bit") == 4096.0
    assert (
        estimate_model_size("mlx-community/Qwen2.5-Coder-14B-Instruct-4bit") == 8192.0
    )
    assert (
        estimate_model_size("mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit") == 17500.0
    )


def test_estimate_model_size_unknown_defaults():
    """Unknown model should default to 4096MB (7B)."""
    assert estimate_model_size("some-unknown-model") == 4096.0
    assert estimate_model_size("mlx-community/custom-model") == 4096.0


def test_model_sizes_dict_has_expected_entries():
    """MODEL_SIZES_MB should have entries for 3B, 7B, 14B, 30B."""
    assert "3B-4bit" in MODEL_SIZES_MB
    assert "7B-4bit" in MODEL_SIZES_MB
    assert "14B-4bit" in MODEL_SIZES_MB
    assert "30B-4bit" in MODEL_SIZES_MB
    assert len(MODEL_SIZES_MB) == 4


def test_memory_snapshot_peak_is_meaningful():
    """Peak RSS should be >= current RSS."""
    snapshot = get_memory_snapshot()
    # Peak should be at least as large as current
    # (In practice they're often equal or peak is slightly higher)
    assert snapshot.peak_rss_bytes >= snapshot.rss_bytes
