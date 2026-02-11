"""Tests for dataset JSONL I/O."""

from pathlib import Path

from punie.training.dataset import ChatMessage, TrainingDataset, TrainingExample
from punie.training.dataset_io import (
    compute_stats,
    read_dataset,
    read_jsonl,
    write_dataset,
    write_jsonl,
)


def test_write_jsonl(tmp_path: Path):
    """write_jsonl creates valid JSONL file."""
    examples = (
        TrainingExample(
            messages=(
                ChatMessage(role="user", content="Hello"),
                ChatMessage(role="assistant", content="Hi!"),
            )
        ),
        TrainingExample(
            messages=(
                ChatMessage(role="user", content="Bye"),
                ChatMessage(role="assistant", content="Goodbye!"),
            )
        ),
    )

    output_file = tmp_path / "test.jsonl"
    write_jsonl(examples, output_file)

    assert output_file.exists()

    # Verify content
    lines = output_file.read_text().strip().split("\n")
    assert len(lines) == 2


def test_read_jsonl(tmp_path: Path):
    """read_jsonl reads JSONL file correctly."""
    # Write test data
    content = """{"messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi!"}]}
{"messages": [{"role": "user", "content": "Bye"}, {"role": "assistant", "content": "Goodbye!"}]}
"""
    file_path = tmp_path / "test.jsonl"
    file_path.write_text(content)

    # Read it back
    examples = read_jsonl(file_path)

    assert len(examples) == 2
    assert examples[0].messages[0].content == "Hello"
    assert examples[1].messages[0].content == "Bye"


def test_write_read_roundtrip(tmp_path: Path):
    """Write and read produce identical data."""
    original = (
        TrainingExample(
            messages=(
                ChatMessage(role="system", content="You are helpful"),
                ChatMessage(role="user", content="What is 2+2?"),
                ChatMessage(role="assistant", content="4"),
            )
        ),
    )

    file_path = tmp_path / "roundtrip.jsonl"
    write_jsonl(original, file_path)
    restored = read_jsonl(file_path)

    assert len(restored) == len(original)
    assert restored[0].messages == original[0].messages


def test_write_dataset(tmp_path: Path):
    """write_dataset creates directory and split files."""
    example = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Test"),
            ChatMessage(role="assistant", content="Response"),
        )
    )

    dataset = TrainingDataset(
        name="test",
        version="1.0",
        train=(example,),
        valid=(example,),
        test=(),
    )

    output_dir = tmp_path / "dataset"
    write_dataset(dataset, output_dir)

    assert output_dir.exists()
    assert (output_dir / "train.jsonl").exists()
    assert (output_dir / "valid.jsonl").exists()
    assert (output_dir / "test.jsonl").exists()


def test_read_dataset(tmp_path: Path):
    """read_dataset reads all splits correctly."""
    # Create test files
    output_dir = tmp_path / "dataset"
    output_dir.mkdir()

    train_content = '{"messages": [{"role": "user", "content": "Train"}, {"role": "assistant", "content": "Response"}]}\n'
    (output_dir / "train.jsonl").write_text(train_content)

    valid_content = '{"messages": [{"role": "user", "content": "Valid"}, {"role": "assistant", "content": "Response"}]}\n'
    (output_dir / "valid.jsonl").write_text(valid_content)

    (output_dir / "test.jsonl").write_text("")  # Empty test split

    # Read dataset
    dataset = read_dataset(output_dir, name="my-dataset", version="2.0")

    assert dataset.name == "my-dataset"
    assert dataset.version == "2.0"
    assert len(dataset.train) == 1
    assert len(dataset.valid) == 1
    assert len(dataset.test) == 0
    assert dataset.train[0].messages[0].content == "Train"


def test_write_read_dataset_roundtrip(tmp_path: Path):
    """Write and read dataset produce identical data."""
    example1 = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Question 1"),
            ChatMessage(role="assistant", content="Answer 1"),
        )
    )
    example2 = TrainingExample(
        messages=(
            ChatMessage(role="user", content="Question 2"),
            ChatMessage(role="assistant", content="Answer 2"),
        )
    )

    original = TrainingDataset(
        name="test",
        version="1.0",
        train=(example1,),
        valid=(example2,),
        test=(),
    )

    output_dir = tmp_path / "roundtrip"
    write_dataset(original, output_dir)
    restored = read_dataset(output_dir, name="test", version="1.0")

    assert restored.name == original.name
    assert restored.version == original.version
    assert len(restored.train) == len(original.train)
    assert len(restored.valid) == len(original.valid)
    assert restored.train[0].messages == original.train[0].messages


def test_compute_stats():
    """compute_stats calculates correct statistics."""
    examples = [
        TrainingExample(
            messages=(
                ChatMessage(role="user", content="Q"),
                ChatMessage(role="assistant", content="A"),
            )
        ),
        TrainingExample(
            messages=(
                ChatMessage(role="system", content="S"),
                ChatMessage(role="user", content="Q"),
                ChatMessage(role="assistant", content="A"),
            )
        ),
    ]

    dataset = TrainingDataset(
        name="test",
        version="1.0",
        train=tuple(examples[:1]),
        valid=tuple(examples[1:]),
        test=(),
    )

    stats = compute_stats(dataset)

    assert stats.total_examples == 2
    assert stats.train_count == 1
    assert stats.valid_count == 1
    assert stats.test_count == 0
    assert stats.avg_messages_per_example == 2.5  # (2 + 3) / 2


def test_compute_stats_empty():
    """compute_stats handles empty dataset."""
    dataset = TrainingDataset(
        name="test",
        version="1.0",
        train=(),
        valid=(),
        test=(),
    )

    stats = compute_stats(dataset)

    assert stats.total_examples == 0
    assert stats.avg_messages_per_example == 0.0


def test_read_jsonl_empty_lines(tmp_path: Path):
    """read_jsonl skips empty lines."""
    content = """{"messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi!"}]}

{"messages": [{"role": "user", "content": "Bye"}, {"role": "assistant", "content": "Goodbye!"}]}
"""
    file_path = tmp_path / "test.jsonl"
    file_path.write_text(content)

    examples = read_jsonl(file_path)

    assert len(examples) == 2
