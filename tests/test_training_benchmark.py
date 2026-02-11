"""Tests for training benchmark utilities."""

import json
from pathlib import Path

from punie.training.benchmark import create_dummy_dataset


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
