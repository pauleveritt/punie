#!/usr/bin/env python3
"""Remove preambles from Phase 27 augmented training data.

This script fixes the inconsistent preamble issue where some tools (goto_definition,
find_references) have preambles before <tool_call> while others don't, causing
the model to hit EOS tokens early during inference.

Solution: Remove ALL text before <tool_call> in assistant messages.

Usage:
    python scripts/remove_preambles.py

Input:
    data/phase27_augmented/train.jsonl
    data/phase27_augmented/valid.jsonl

Output:
    data/phase27_cleaned/train.jsonl
    data/phase27_cleaned/valid.jsonl
"""

import json
import re
from pathlib import Path


def remove_preamble(content: str) -> str:
    """Remove everything before <tool_call> tag.

    Args:
        content: Assistant message content

    Returns:
        Content with preamble removed (or unchanged if no tool call)

    Examples:
        >>> remove_preamble("Let me investigate.\\n\\n<tool_call>...")
        '<tool_call>...'
        >>> remove_preamble("<tool_call>...")
        '<tool_call>...'
        >>> remove_preamble("This is a direct answer.")
        'This is a direct answer.'
    """
    if "<tool_call>" not in content:
        # No tool call, return as-is (direct answer)
        return content

    # Remove everything before <tool_call>, including newlines/whitespace
    cleaned = re.sub(r"^.*?(<tool_call>)", r"\1", content, flags=re.DOTALL)
    return cleaned.strip()


def clean_example(example: dict) -> dict:
    """Clean a single training example by removing preambles.

    Args:
        example: Training example with 'messages' list

    Returns:
        Cleaned example with preambles removed from assistant messages
    """
    for message in example["messages"]:
        if message["role"] == "assistant":
            original = message["content"]
            message["content"] = remove_preamble(original)

            # Track if we made a change
            if original != message["content"] and "<tool_call>" in message["content"]:
                removed_text = original.split("<tool_call>")[0].strip()
                if removed_text:
                    # Optional: log what was removed (for verification)
                    pass

    return example


def clean_dataset(input_path: Path, output_path: Path) -> tuple[int, int]:
    """Clean an entire dataset file.

    Args:
        input_path: Path to input JSONL file
        output_path: Path to output JSONL file

    Returns:
        Tuple of (total_examples, examples_with_preambles_removed)
    """
    total = 0
    removed_count = 0

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(input_path) as f_in, open(output_path, "w") as f_out:
        for line in f_in:
            total += 1
            example = json.loads(line)

            # Check if this example has a preamble before cleaning
            had_preamble = False
            for msg in example["messages"]:
                if msg["role"] == "assistant" and "<tool_call>" in msg["content"]:
                    before = msg["content"].split("<tool_call>")[0].strip()
                    if before:
                        had_preamble = True
                        break

            # Clean the example
            cleaned = clean_example(example)

            if had_preamble:
                removed_count += 1

            # Write cleaned example
            f_out.write(json.dumps(cleaned) + "\n")

    return total, removed_count


def main():
    """Clean Phase 27 augmented data by removing all preambles."""
    input_dir = Path("data/phase27_augmented")
    output_dir = Path("data/phase27_cleaned")

    print("=" * 70)
    print("Phase 27 Preamble Removal")
    print("=" * 70)
    print()

    # Clean train.jsonl
    train_input = input_dir / "train.jsonl"
    train_output = output_dir / "train.jsonl"

    print(f"Cleaning {train_input}...")
    train_total, train_removed = clean_dataset(train_input, train_output)
    print(f"  Total examples: {train_total}")
    print(f"  Preambles removed: {train_removed} ({train_removed/train_total*100:.1f}%)")
    print(f"  Output: {train_output}")
    print()

    # Clean valid.jsonl
    valid_input = input_dir / "valid.jsonl"
    valid_output = output_dir / "valid.jsonl"

    print(f"Cleaning {valid_input}...")
    valid_total, valid_removed = clean_dataset(valid_input, valid_output)
    print(f"  Total examples: {valid_total}")
    print(f"  Preambles removed: {valid_removed} ({valid_removed/valid_total*100:.1f}%)")
    print(f"  Output: {valid_output}")
    print()

    # Verification
    print("=" * 70)
    print("Verification")
    print("=" * 70)
    print()

    print("Checking for remaining preambles...")

    # Check train.jsonl
    with open(train_output) as f:
        has_preambles = 0
        for line in f:
            data = json.loads(line)
            for msg in data["messages"]:
                if msg["role"] == "assistant" and "<tool_call>" in msg["content"]:
                    before = msg["content"].split("<tool_call>")[0].strip()
                    if before:
                        has_preambles += 1
                        if has_preambles == 1:
                            print("  WARNING: Found preamble in train.jsonl:")
                            print(f"    {before[:100]}...")

    if has_preambles == 0:
        print("  ✅ train.jsonl: 0 preambles remaining")
    else:
        print(f"  ❌ train.jsonl: {has_preambles} preambles remaining (ERROR!)")

    # Check valid.jsonl
    with open(valid_output) as f:
        has_preambles = 0
        for line in f:
            data = json.loads(line)
            for msg in data["messages"]:
                if msg["role"] == "assistant" and "<tool_call>" in msg["content"]:
                    before = msg["content"].split("<tool_call>")[0].strip()
                    if before:
                        has_preambles += 1

    if has_preambles == 0:
        print("  ✅ valid.jsonl: 0 preambles remaining")
    else:
        print(f"  ❌ valid.jsonl: {has_preambles} preambles remaining (ERROR!)")

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"  Input:  {input_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Train:  {train_total} examples, {train_removed} cleaned")
    print(f"  Valid:  {valid_total} examples, {valid_removed} cleaned")
    print(f"  Total cleaned: {train_removed + valid_removed}/{train_total + valid_total}")
    print()
    print("✅ Data cleaning complete!")
    print()
    print("Next steps:")
    print("  1. Review cleaned data: head -5 data/phase27_cleaned/train.jsonl")
    print("  2. Train model: ./scripts/train_phase27_cleaned.sh")
    print("  3. Validate: python scripts/validate_model.py fused_model_qwen3_phase27_cleaned_5bit/")


if __name__ == "__main__":
    main()
