"""Merge Phase 22 training data with ty examples for Phase 23.

Takes Phase 22's 707 examples (code format) and adds 50 ty examples,
then splits 80/10/10 for training.
"""

import json
import random
from pathlib import Path

# Input paths
PHASE22_DIR = Path("data/phase22_merged")
TY_DIR = Path("data/ty_training")

# Output path
OUTPUT_DIR = Path("data/phase23_merged")


def load_jsonl(file_path: Path) -> list[dict]:
    """Load JSONL file into list of dicts."""
    examples = []
    with file_path.open() as f:
        for line in f:
            examples.append(json.loads(line))
    return examples


def save_jsonl(examples: list[dict], file_path: Path) -> None:
    """Save list of dicts to JSONL file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")


def convert_messages_to_text(example: dict) -> dict:
    """Convert messages format to text format for mlx_lm.

    Args:
        example: Dict with either "messages" or "text" key

    Returns:
        Dict with "text" key in Qwen chat format
    """
    # Already in text format
    if "text" in example:
        return example

    # Convert from messages format
    if "messages" not in example:
        raise ValueError(f"Example has neither 'text' nor 'messages': {example.keys()}")

    # Build chat format text
    system_msg = "You are Punie, an AI coding assistant that helps with Python development via PyCharm."
    text_parts = [f"<|im_start|>system\n{system_msg}<|im_end|>"]

    for msg in example["messages"]:
        role = msg["role"]
        content = msg["content"]
        text_parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")

    return {"text": "\n".join(text_parts)}


def main():
    """Merge Phase 22 + ty examples and split for Phase 23 training."""
    print("Loading Phase 22 data...")
    phase22_train = load_jsonl(PHASE22_DIR / "train.jsonl")
    phase22_valid = load_jsonl(PHASE22_DIR / "valid.jsonl")
    phase22_test = load_jsonl(PHASE22_DIR / "test.jsonl")
    phase22_total = phase22_train + phase22_valid + phase22_test
    print(f"  Phase 22: {len(phase22_total)} examples (train={len(phase22_train)}, valid={len(phase22_valid)}, test={len(phase22_test)})")

    print("\nLoading ty training data...")
    ty_examples_raw = load_jsonl(TY_DIR / "ty_examples.jsonl")
    print(f"  ty examples: {len(ty_examples_raw)}")

    # Convert ty examples from messages to text format
    print("Converting ty examples to text format...")
    ty_examples = [convert_messages_to_text(ex) for ex in ty_examples_raw]

    # Merge all examples
    all_examples = phase22_total + ty_examples
    print(f"\nTotal examples: {len(all_examples)}")

    # Shuffle for random split
    random.seed(42)  # Reproducible
    random.shuffle(all_examples)

    # Split 80/10/10
    total = len(all_examples)
    train_size = int(total * 0.8)
    valid_size = int(total * 0.1)
    # test_size is the remainder

    train = all_examples[:train_size]
    valid = all_examples[train_size:train_size + valid_size]
    test = all_examples[train_size + valid_size:]

    print(f"\nSplit:")
    print(f"  Train: {len(train)} ({len(train)/total*100:.1f}%)")
    print(f"  Valid: {len(valid)} ({len(valid)/total*100:.1f}%)")
    print(f"  Test: {len(test)} ({len(test)/total*100:.1f}%)")

    # Save splits
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_jsonl(train, OUTPUT_DIR / "train.jsonl")
    save_jsonl(valid, OUTPUT_DIR / "valid.jsonl")
    save_jsonl(test, OUTPUT_DIR / "test.jsonl")

    print(f"\nSaved to: {OUTPUT_DIR}/")
    print("Ready for Phase 23 training!")


if __name__ == "__main__":
    main()
