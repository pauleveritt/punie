#!/usr/bin/env python3
"""Merge all training data sources for Phase 26.

Sources:
  1. Phase 22 base (707 examples from data/phase22_code_format/) — text format
  2. Phase 23 ty (50 examples from data/ty_training/) — messages format (no system)
  3. Phase 24 ruff/pytest (100 examples from data/phase24_format_a/) — messages format (with system)
  4. Phase 26 field access (120 examples from data/phase26_field_access/) — messages format (with system)

All data will be converted to messages format with system prompts, shuffled,
and split 80/10/10 for training.

Total: ~977 examples
"""

import json
import random
from pathlib import Path

from punie.training.dataset import ChatMessage, TrainingDataset, TrainingExample
from punie.training.dataset_io import write_dataset

# Input paths
PHASE22_DIR = Path("data/phase22_code_format")
TY_INPUT = Path("data/ty_training/ty_examples.jsonl")
PHASE24_DIR = Path("data/phase24_format_a")
PHASE26_DIR = Path("data/phase26_field_access")

# Output path
OUTPUT_DIR = Path("data/phase26_merged")

# Constants
SYSTEM_PROMPT = "You are Punie, an AI coding assistant that helps with Python development via PyCharm."


def convert_text_to_messages(text: str) -> list[dict]:
    """Convert text format to messages format.

    Args:
        text: Full conversation with <|im_start|> tokens

    Returns:
        List of message dicts with role/content
    """
    messages = []

    # Split by message boundaries
    parts = text.split("<|im_start|>")

    for part in parts:
        if not part.strip():
            continue

        # Split role and content
        lines = part.split("\n", 1)
        if len(lines) != 2:
            continue

        role = lines[0].strip()
        content = lines[1].replace("<|im_end|>", "").strip()

        messages.append({"role": role, "content": content})

    return messages


def convert_to_training_example(data: dict) -> TrainingExample:
    """Convert any format to TrainingExample.

    Args:
        data: Dict with either "text" or "messages" key

    Returns:
        TrainingExample with messages format
    """
    # Handle text format (Phase 22)
    if "text" in data:
        messages = convert_text_to_messages(data["text"])
    # Handle messages format (Phase 23-26)
    elif "messages" in data:
        messages = data["messages"]
    else:
        raise ValueError(f"Unknown format: {list(data.keys())}")

    # Convert to ChatMessage tuples
    chat_messages = []
    for msg in messages:
        chat_messages.append(
            ChatMessage(role=msg["role"], content=msg["content"])
        )

    return TrainingExample(messages=tuple(chat_messages))


def load_jsonl(file_path: Path) -> list[dict]:
    """Load JSONL file into list of dicts.

    Args:
        file_path: Path to JSONL file

    Returns:
        List of example dicts
    """
    examples = []
    with file_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping malformed line in {file_path}: {e}")
    return examples


def load_all_sources() -> list[TrainingExample]:
    """Load and convert all training data sources.

    Returns:
        List of TrainingExamples in unified messages format
    """
    all_examples = []

    # Source 1: Phase 22 base (707 examples, text format)
    print("Loading Phase 22 base data...")
    phase22_train = load_jsonl(PHASE22_DIR / "train.jsonl")
    phase22_valid = load_jsonl(PHASE22_DIR / "valid.jsonl")
    phase22_test = load_jsonl(PHASE22_DIR / "test.jsonl")
    phase22_all = phase22_train + phase22_valid + phase22_test
    print(f"  Phase 22: {len(phase22_all)} examples (text format)")

    for data in phase22_all:
        all_examples.append(convert_to_training_example(data))

    # Source 2: Phase 23 ty (50 examples, messages format without system)
    print("\nLoading Phase 23 ty data...")
    if TY_INPUT.exists():
        ty_data = load_jsonl(TY_INPUT)
        print(f"  ty examples: {len(ty_data)} (messages format)")

        # Add system message if missing
        for data in ty_data:
            if "messages" in data:
                msgs = data["messages"]
                # Check if first message is system
                if not msgs or msgs[0].get("role") != "system":
                    # Prepend system message
                    data["messages"] = [
                        {"role": "system", "content": SYSTEM_PROMPT}
                    ] + msgs

            all_examples.append(convert_to_training_example(data))
    else:
        print(f"  Warning: {TY_INPUT} not found, skipping")

    # Source 3: Phase 24 ruff/pytest (100 examples, Format A with system)
    print("\nLoading Phase 24 ruff/pytest data...")
    phase24_count = 0
    for file_name in ["ruff_examples.jsonl", "pytest_examples.jsonl"]:
        file_path = PHASE24_DIR / file_name
        if file_path.exists():
            data_list = load_jsonl(file_path)
            print(f"  {file_name}: {len(data_list)} examples")
            for data in data_list:
                all_examples.append(convert_to_training_example(data))
            phase24_count += len(data_list)
        else:
            print(f"  Warning: {file_path} not found")
    print(f"  Phase 24 total: {phase24_count}")

    # Source 4: Phase 26 field access (120 examples, Format A with system)
    print("\nLoading Phase 26 field access data...")
    phase26_file = PHASE26_DIR / "field_access_examples.jsonl"
    if phase26_file.exists():
        phase26_data = load_jsonl(phase26_file)
        print(f"  Field access examples: {len(phase26_data)}")
        for data in phase26_data:
            all_examples.append(convert_to_training_example(data))
    else:
        print(f"  Warning: {phase26_file} not found, skipping")

    return all_examples


def main():
    """Merge all sources and create Phase 26 training dataset."""
    print("Merging all training data for Phase 26...")
    print("="*60)
    print()

    # Load all sources
    all_examples = load_all_sources()

    print()
    print(f"Total examples loaded: {len(all_examples)}")
    print()

    # Shuffle for random split (reproducible)
    random.seed(42)
    random.shuffle(all_examples)

    # Split 80/10/10
    total = len(all_examples)
    train_size = int(total * 0.8)
    valid_size = int(total * 0.1)
    # test_size is the remainder

    train = tuple(all_examples[:train_size])
    valid = tuple(all_examples[train_size:train_size + valid_size])
    test = tuple(all_examples[train_size + valid_size:])

    print("Split (80/10/10):")
    print(f"  Train: {len(train)} examples ({len(train)/total*100:.1f}%)")
    print(f"  Valid: {len(valid)} examples ({len(valid)/total*100:.1f}%)")
    print(f"  Test: {len(test)} examples ({len(test)/total*100:.1f}%)")
    print()

    # Create TrainingDataset
    dataset = TrainingDataset(
        name="phase26",
        version="2026-02-15",
        train=train,
        valid=valid,
        test=test,
    )

    # Write to disk
    print(f"Writing to: {OUTPUT_DIR}")
    write_dataset(dataset, OUTPUT_DIR)

    print()
    print("="*60)
    print("Phase 26 training data ready!")
    print(f"  Total: {total} examples")
    print("  Format: messages (unified)")
    print(f"  Output: {OUTPUT_DIR}")
    print("="*60)


if __name__ == "__main__":
    main()
