#!/usr/bin/env python3
"""Merge converted Phase 21 data with new Code Mode workflows and split into train/valid/test."""

import json
import random
from pathlib import Path


def load_jsonl(file_path):
    """Load examples from a JSONL file."""
    examples = []
    with open(file_path) as f:
        for line in f:
            examples.append(json.loads(line))
    return examples


def save_jsonl(examples, file_path):
    """Save examples to a JSONL file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")


def count_tool_vs_direct(examples):
    """Count tool-calling vs direct-answer examples."""
    tool_count = sum(1 for ex in examples if "<tool_call>" in ex["text"])
    direct_count = len(examples) - tool_count
    return tool_count, direct_count


def main():
    """Merge and split Phase 22 training data."""
    converted_dir = Path("data/phase22_code_format")
    workflows_file = Path("data/phase22_code_workflows.jsonl")
    output_dir = Path("data/phase22_merged")

    print("Merging Phase 22 training data...")
    print()

    all_examples = []

    # Load converted Phase 21 examples
    for split in ["train", "valid", "test"]:
        converted_file = converted_dir / f"{split}.jsonl"
        if converted_file.exists():
            examples = load_jsonl(converted_file)
            all_examples.extend(examples)
            print(f"✓ Loaded {len(examples)} converted examples from {split}")

    # Load new workflow examples
    if workflows_file.exists():
        workflow_examples = load_jsonl(workflows_file)
        all_examples.extend(workflow_examples)
        print(f"✓ Loaded {len(workflow_examples)} new workflow examples")

    total = len(all_examples)
    print()
    print(f"Total examples: {total}")

    # Analyze distribution
    tool_count, direct_count = count_tool_vs_direct(all_examples)
    print(f"Tool-calling: {tool_count} ({int(tool_count/total*100)}%)")
    print(f"Direct answers: {direct_count} ({int(direct_count/total*100)}%)")
    print()

    # Shuffle and split
    random.seed(42)
    random.shuffle(all_examples)

    train_size = int(total * 0.8)
    valid_size = int(total * 0.1)

    train = all_examples[:train_size]
    valid = all_examples[train_size:train_size + valid_size]
    test = all_examples[train_size + valid_size:]

    # Save
    save_jsonl(train, output_dir / "train.jsonl")
    save_jsonl(valid, output_dir / "valid.jsonl")
    save_jsonl(test, output_dir / "test.jsonl")

    print("Split into:")
    print(f"  Train: {len(train)} ({int(len(train)/total*100)}%)")
    print(f"  Valid: {len(valid)} ({int(len(valid)/total*100)}%)")
    print(f"  Test:  {len(test)} ({int(len(test)/total*100)}%)")
    print()
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
