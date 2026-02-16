"""Merge Phase 27 augmented + Phase 27.5 new data, deduplicate, split."""

import json
import random
from pathlib import Path

random.seed(47)


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file into list of examples."""
    examples = []
    with open(path) as f:
        for line in f:
            examples.append(json.loads(line))
    return examples


def deduplicate_examples(examples: list[dict]) -> list[dict]:
    """Remove exact duplicates based on full message content."""
    seen = set()
    unique = []

    for ex in examples:
        # Create hashable key from messages
        key = json.dumps(ex["messages"], sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(ex)

    return unique


def main():
    """Merge and deduplicate Phase 27.5 data."""
    print("Merging Phase 27.5 data...")
    print("=" * 60)

    # Load sources
    print("\n1. Loading data sources...")
    phase27_aug = load_jsonl(Path("data/phase27_augmented/train.jsonl"))
    print(f"   Phase 27 augmented: {len(phase27_aug)} examples")

    phase275_new = load_jsonl(Path("data/phase275_new/train.jsonl"))
    print(f"   Phase 27.5 new: {len(phase275_new)} examples")

    # Combine
    all_examples = phase27_aug + phase275_new
    print(f"\n2. Combined: {len(all_examples)} examples")

    # Deduplicate
    unique_examples = deduplicate_examples(all_examples)
    duplicates_removed = len(all_examples) - len(unique_examples)
    print(f"\n3. Deduplicated: {len(unique_examples)} examples")
    print(f"   Removed {duplicates_removed} duplicates")

    # Shuffle
    random.shuffle(unique_examples)
    print(f"\n4. Shuffled examples")

    # Split 90/10
    split_idx = int(len(unique_examples) * 0.9)
    train_examples = unique_examples[:split_idx]
    valid_examples = unique_examples[split_idx:]

    print(f"\n5. Split into train/valid:")
    print(f"   Train: {len(train_examples)} examples")
    print(f"   Valid: {len(valid_examples)} examples")

    # Write
    output_dir = Path("data/phase275_merged")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "train.jsonl", "w") as f:
        for ex in train_examples:
            f.write(json.dumps(ex) + "\n")

    with open(output_dir / "valid.jsonl", "w") as f:
        for ex in valid_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\n{'=' * 60}")
    print(f"✅ Merged data saved to {output_dir}/")
    print(f"   Train: {len(train_examples)} examples")
    print(f"   Valid: {len(valid_examples)} examples")
    print(f"   Total: {len(unique_examples)} examples")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
