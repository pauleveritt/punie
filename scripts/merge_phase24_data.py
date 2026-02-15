"""Merge all Phase 24 training data.

Combines:
- Phase 23: 757 examples (ty + code mode + multi-turn)
- Ruff: 50 examples
- Pytest: 50 examples
- Total: 857 examples (targeting 1000+ with domain data to be added)

Splits into train/valid/test (80/10/10) and converts to Qwen chat format.
"""

import json
import random
from pathlib import Path


def load_jsonl(file_path):
    """Load examples from JSONL file."""
    examples = []
    if not file_path.exists():
        print(f"Warning: {file_path} not found, skipping")
        return examples

    with file_path.open() as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))
    return examples


def messages_to_qwen_format(messages):
    """Convert messages to Qwen chat format."""
    formatted = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            formatted.append(f"<|im_start|>user\n{content}<|im_end|>")
        elif role == "assistant":
            formatted.append(f"<|im_start|>assistant\n{content}<|im_end|>")

    return "\n".join(formatted)


def save_dataset(examples, output_dir, split_name):
    """Save examples in .jsonl format."""
    output_file = output_dir / f"{split_name}.jsonl"

    with output_file.open("w") as f:
        for example in examples:
            # Convert messages to text
            text = messages_to_qwen_format(example["messages"])
            f.write(json.dumps({"text": text}) + "\n")

    print(f"  {split_name}: {len(examples)} examples → {output_file}")


def main():
    """Merge all training data and split into train/valid/test."""
    # Load all data sources
    print("Loading data sources...")

    phase23_dir = Path("data/phase23_merged")
    ruff_dir = Path("data/ruff_training")
    pytest_dir = Path("data/pytest_training")

    # Load Phase 23 data (already in train/valid/test splits)
    phase23_train = load_jsonl(phase23_dir / "train.jsonl")
    phase23_valid = load_jsonl(phase23_dir / "valid.jsonl")
    phase23_test = load_jsonl(phase23_dir / "test.jsonl")

    # Convert Phase 23 format (text) back to messages format for merging
    # (Phase 23 is already in final format, so we'll just add new data to it)

    # Load new data
    ruff_examples = load_jsonl(ruff_dir / "ruff_examples.jsonl")
    pytest_examples = load_jsonl(pytest_dir / "pytest_examples.jsonl")

    print(f"  Phase 23 train: {len(phase23_train)}")
    print(f"  Phase 23 valid: {len(phase23_valid)}")
    print(f"  Phase 23 test: {len(phase23_test)}")
    print(f"  Ruff: {len(ruff_examples)}")
    print(f"  Pytest: {len(pytest_examples)}")

    # Combine new examples
    new_examples = ruff_examples + pytest_examples
    print(f"  New examples: {len(new_examples)}")

    # Shuffle new examples
    random.seed(42)
    random.shuffle(new_examples)

    # Split new examples (80/10/10)
    n = len(new_examples)
    train_size = int(n * 0.8)
    valid_size = int(n * 0.1)

    new_train = new_examples[:train_size]
    new_valid = new_examples[train_size:train_size + valid_size]
    new_test = new_examples[train_size + valid_size:]

    print(f"  New train: {len(new_train)}")
    print(f"  New valid: {len(new_valid)}")
    print(f"  New test: {len(new_test)}")

    # Create output directory
    output_dir = Path("data/phase24_merged")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save merged datasets
    print("\\nSaving merged datasets...")

    # For Phase 23 data, we need to load it as-is (already in Qwen format)
    # For new data, we need to convert messages to Qwen format

    # Convert new examples to Qwen format
    new_train_qwen = []
    for ex in new_train:
        text = messages_to_qwen_format(ex["messages"])
        new_train_qwen.append({"text": text})

    new_valid_qwen = []
    for ex in new_valid:
        text = messages_to_qwen_format(ex["messages"])
        new_valid_qwen.append({"text": text})

    new_test_qwen = []
    for ex in new_test:
        text = messages_to_qwen_format(ex["messages"])
        new_test_qwen.append({"text": text})

    # Combine with Phase 23 data
    # Phase 23 data is already in {"text": "..."} format
    all_train = phase23_train + new_train_qwen
    all_valid = phase23_valid + new_valid_qwen
    all_test = phase23_test + new_test_qwen

    # Save combined datasets
    for split_name, examples in [
        ("train", all_train),
        ("valid", all_valid),
        ("test", all_test)
    ]:
        output_file = output_dir / f"{split_name}.jsonl"
        with output_file.open("w") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")
        print(f"  {split_name}: {len(examples)} examples → {output_file}")

    total = len(all_train) + len(all_valid) + len(all_test)
    print(f"\\n✓ Merged {total} total examples")
    print(f"  Phase 23 contribution: {len(phase23_train) + len(phase23_valid) + len(phase23_test)}")
    print(f"  Phase 24 contribution: {len(new_train_qwen) + len(new_valid_qwen) + len(new_test_qwen)}")


if __name__ == "__main__":
    main()
