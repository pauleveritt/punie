"""JSONL I/O for training datasets."""

import json
from pathlib import Path

from punie.training.dataset import ChatMessage, DatasetStats, TrainingDataset, TrainingExample


def write_jsonl(examples: tuple[TrainingExample, ...], file_path: Path) -> None:
    """Write examples to JSONL file.

    Args:
        examples: Training examples to write
        file_path: Output file path
    """
    with file_path.open("w") as f:
        for example in examples:
            json_dict = example.to_jsonl_dict()
            f.write(json.dumps(json_dict) + "\n")


def read_jsonl(file_path: Path) -> tuple[TrainingExample, ...]:
    """Read examples from JSONL file.

    Args:
        file_path: Input file path

    Returns:
        Tuple of training examples
    """
    examples = []

    with file_path.open("r") as f:
        for line in f:
            if not line.strip():
                continue

            data = json.loads(line)
            messages = tuple(
                ChatMessage(role=msg["role"], content=msg["content"])
                for msg in data["messages"]
            )
            examples.append(TrainingExample(messages=messages))

    return tuple(examples)


def write_dataset(dataset: TrainingDataset, directory: Path) -> None:
    """Write dataset to directory with train/valid/test splits.

    Creates directory if it doesn't exist.
    Writes train.jsonl, valid.jsonl, test.jsonl files.

    Args:
        dataset: Dataset to write
        directory: Output directory
    """
    directory.mkdir(parents=True, exist_ok=True)

    write_jsonl(dataset.train, directory / "train.jsonl")
    write_jsonl(dataset.valid, directory / "valid.jsonl")
    write_jsonl(dataset.test, directory / "test.jsonl")


def read_dataset(directory: Path, name: str = "dataset", version: str = "1.0") -> TrainingDataset:
    """Read dataset from directory with train/valid/test splits.

    Args:
        directory: Directory containing train.jsonl, valid.jsonl, test.jsonl
        name: Dataset name (default: "dataset")
        version: Dataset version (default: "1.0")

    Returns:
        TrainingDataset with loaded examples
    """
    train = read_jsonl(directory / "train.jsonl") if (directory / "train.jsonl").exists() else ()
    valid = read_jsonl(directory / "valid.jsonl") if (directory / "valid.jsonl").exists() else ()
    test = read_jsonl(directory / "test.jsonl") if (directory / "test.jsonl").exists() else ()

    return TrainingDataset(
        name=name,
        version=version,
        train=train,
        valid=valid,
        test=test,
    )


def compute_stats(dataset: TrainingDataset) -> DatasetStats:
    """Compute statistics for a dataset.

    Args:
        dataset: Dataset to analyze

    Returns:
        DatasetStats with computed metrics
    """
    total = len(dataset.train) + len(dataset.valid) + len(dataset.test)

    # Compute average messages per example
    all_examples = dataset.train + dataset.valid + dataset.test
    if all_examples:
        total_messages = sum(len(ex.messages) for ex in all_examples)
        avg_messages = total_messages / len(all_examples)
    else:
        avg_messages = 0.0

    return DatasetStats(
        total_examples=total,
        train_count=len(dataset.train),
        valid_count=len(dataset.valid),
        test_count=len(dataset.test),
        avg_messages_per_example=avg_messages,
    )
