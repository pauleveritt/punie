"""Merge all training data sources for Phase 27 augmented training."""

import json
import random
from pathlib import Path

# Set seed for reproducibility
random.seed(42)

# Data sources
# Phase 27 merged already includes: Phase 26 + LSP + git + rebalance + direct_answers
sources = {
    "train": [
        "data/phase27_merged/train.jsonl",  # 993 examples (already includes all Phase 27 data)
        "data/phase27_tool_responses/train.jsonl",  # 60 new examples with tool responses
    ],
    "valid": [
        "data/phase27_merged/valid.jsonl",  # 111 examples
        # Note: tool_responses only has train.jsonl
    ],
}

def merge_and_shuffle(source_files: list[str], output_file: Path):
    """Merge multiple JSONL files and shuffle."""
    all_examples = []

    for source in source_files:
        source_path = Path(source)
        if not source_path.exists():
            print(f"  ⚠️  Skipping {source} (not found)")
            continue

        with open(source_path) as f:
            examples = [json.loads(line) for line in f]
            all_examples.extend(examples)
            print(f"  ✓ {source}: {len(examples)} examples")

    # Shuffle
    random.shuffle(all_examples)

    # Write
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")

    return len(all_examples)

def main():
    """Merge all data sources."""
    output_dir = Path("data/phase27_augmented")

    print("Merging training data...")
    train_count = merge_and_shuffle(
        sources["train"],
        output_dir / "train.jsonl"
    )

    print(f"\n✅ Training: {train_count} examples\n")

    print("Merging validation data...")
    valid_count = merge_and_shuffle(
        sources["valid"],
        output_dir / "valid.jsonl"
    )

    print(f"\n✅ Validation: {valid_count} examples\n")

    print(f"Total: {train_count + valid_count} examples")
    print(f"Output: {output_dir}/")

if __name__ == "__main__":
    main()
