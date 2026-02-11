"""Tests for BenchmarkResult dataclass."""

from punie.training.benchmark import BenchmarkResult


def test_benchmark_result_frozen():
    """BenchmarkResult instances are immutable."""
    result = BenchmarkResult(
        model_path="test-model",
        seconds_per_iter=2.5,
        total_seconds=25.0,
        num_iters=10,
        peak_memory_gb=None,
    )

    try:
        result.model_path = "other-model"  # type: ignore[misc]
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass


def test_benchmark_result_with_memory():
    """BenchmarkResult can include memory information."""
    result = BenchmarkResult(
        model_path="mlx-community/Qwen3-Coder-30B",
        seconds_per_iter=3.2,
        total_seconds=32.0,
        num_iters=10,
        peak_memory_gb=12.5,
    )

    assert result.model_path == "mlx-community/Qwen3-Coder-30B"
    assert result.seconds_per_iter == 3.2
    assert result.total_seconds == 32.0
    assert result.num_iters == 10
    assert result.peak_memory_gb == 12.5


def test_benchmark_result_without_memory():
    """BenchmarkResult works without memory information."""
    result = BenchmarkResult(
        model_path="test-model",
        seconds_per_iter=1.5,
        total_seconds=15.0,
        num_iters=10,
        peak_memory_gb=None,
    )

    assert result.peak_memory_gb is None


def test_benchmark_result_calculation():
    """BenchmarkResult timing calculations are consistent."""
    result = BenchmarkResult(
        model_path="test-model",
        seconds_per_iter=2.5,
        total_seconds=25.0,
        num_iters=10,
        peak_memory_gb=None,
    )

    # Verify the relationship between fields
    assert result.seconds_per_iter * result.num_iters == result.total_seconds
