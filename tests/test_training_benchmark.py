"""Tests for training benchmark utilities and BenchmarkResult dataclass.

Consolidates:
- Benchmark utilities (create_dummy_dataset)
- BenchmarkResult dataclass
"""

from __future__ import annotations

import json
from pathlib import Path

from punie.training.benchmark import BenchmarkResult, create_dummy_dataset


# ============================================================================
# Benchmark Utilities Tests
# ============================================================================


def test_create_dummy_dataset(tmp_path: Path):
    """create_dummy_dataset writes valid JSONL files."""
    output_dir = tmp_path / "benchmark_data"
    create_dummy_dataset(output_dir, num_examples=3)

    # Check files exist
    assert (output_dir / "train.jsonl").exists()
    assert (output_dir / "valid.jsonl").exists()
    assert (output_dir / "test.jsonl").exists()

    # Check train.jsonl has valid format
    train_file = output_dir / "train.jsonl"
    lines = train_file.read_text().strip().split("\n")
    assert len(lines) == 3

    # Parse first line
    example = json.loads(lines[0])
    assert "messages" in example
    assert len(example["messages"]) == 3
    assert example["messages"][0]["role"] == "system"
    assert example["messages"][1]["role"] == "user"
    assert example["messages"][2]["role"] == "assistant"


def test_create_dummy_dataset_creates_directory(tmp_path: Path):
    """create_dummy_dataset creates parent directory if needed."""
    output_dir = tmp_path / "nested" / "benchmark_data"
    assert not output_dir.exists()

    create_dummy_dataset(output_dir, num_examples=1)

    assert output_dir.exists()
    assert (output_dir / "train.jsonl").exists()


def test_create_dummy_dataset_num_examples(tmp_path: Path):
    """create_dummy_dataset respects num_examples parameter."""
    output_dir = tmp_path / "benchmark_data"
    create_dummy_dataset(output_dir, num_examples=7)

    train_file = output_dir / "train.jsonl"
    lines = train_file.read_text().strip().split("\n")
    assert len(lines) == 7

    valid_file = output_dir / "valid.jsonl"
    lines = valid_file.read_text().strip().split("\n")
    assert len(lines) == 7

    test_file = output_dir / "test.jsonl"
    lines = test_file.read_text().strip().split("\n")
    assert len(lines) == 7


# ============================================================================
# BenchmarkResult Tests
# ============================================================================


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
